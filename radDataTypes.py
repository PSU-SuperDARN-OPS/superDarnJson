# Copyright (C) 2012  VT SuperDARN Lab
# Full license can be found in LICENSE.txt
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
.. module:: radDataTypes
   :synopsis: the classes needed for reading, writing, and storing fundamental
              radar data (iq,raw,fit)
.. moduleauthor:: AJ, 20130108

pydarn.sdio.radDataTypes
-------------------------

Classes
--------
radDataPtr
radBaseData
scanData
beamData
prmData
fitData
rawData
iqData
"""


import davitpy
import logging

from davitpy.utils import twoWayDict
alpha = ['a','b','c','d','e','f','g','h','i','j','k','l','m', \
          'n','o','p','q','r','s','t','u','v','w','x','y','z']


class radDataPtr():
    """A class which contains a pipeline to a data source

    Public Attributes
    ------------------
    sTime : (datetime)
        start time of the request
    eTime : (datetime)
        end time of the request
    stid : (int)
        station id of the request
    channel : (str/NoneType)
        The 1-letter code to specify the UAF channel (not stereo),
        e.g. 'a','b',... If 'all', ALL channels were obtained. 
        (default=None, meaning don't check for UAF named data files)
    bmnum : (int)
        beam number of the request
    cp : (int)
        control prog id of the request
    fType : (str)
        the file type, 'fitacf', 'rawacf', 'iqdat', 'fitex', 'lmfit'
    fBeam : (pydarn.sdio.radDataTypes.beamData)
        the first beam of the next scan, useful for when reading into scan
        objects
    recordIndex : (dict)
        look up dictionary for file offsets for all records 
    scanStartIndex : (dict)
        look up dictionary for file offsets for scan start records

    Private Attributes
    --------------------
    ptr : (file or mongodb query object)
        the data pointer (different depending on mongodo or dmap)
    fd : (int)
        the file descriptor 
    filtered : (bool)
        use Filtered datafile 
    nocache : (bool)
        do not use cached files, regenerate tmp files 
    src : (str)
        local or sftp 

    Methods
    ----------
    open
    close
        Close file pointer
    createIndex
        Index the offsets for all records and scan boundaries
    offsetSeek
        Seek file to requested byte offset, checking to make sure it in the
        record index
    offsetTell
        Current byte offset
    rewind
        rewind file back to the beginning 
    readRec
        read record at current file offset
    readScan
        read scan associated with current record
    readAll
        read all records
    
    Written by AJ 20130108
    """
    
    def __init__(self, sTime=None, radcode=None, eTime=None, stid=None,
                 channel=None, bmnum=None, cp=None, fileType=None,
                 filtered=False, src=None, fileName=None, noCache=False,
                 local_dirfmt=None, local_fnamefmt=None, local_dict=None,
                 remote_dirfmt=None, remote_fnamefmt=None, remote_dict=None,
                 remote_site=None, username=None, port=None, password=None,
                 tmpdir=None):
        import datetime as dt
        import os,glob,string
        from davitpy.pydarn.radar import network
        from davitpy import utils
        from davitpy.pydarn.sdio import fetchUtils as futils

        self.sTime = sTime
        self.eTime = eTime
        self.stid = stid
        self.channel = channel
        self.bmnum = bmnum
        self.cp = cp
        self.fType = fileType
        self.dType = None
        self.fBeam = None
        self.recordIndex = None
        self.scanStartIndex = None
        self.__filename = fileName 
        self.__filtered = filtered
        self.__nocache = noCache
        self.__src = src
        self.__fd = None
        self.__ptr =  None

        # check inputs
        estr = "fileType must be one of: rawacf, fitacf, fitex, lmfit, iqdat"
        assert isinstance(self.sTime,dt.datetime), \
            logging.error('sTime must be datetime object')
        assert self.eTime == None or isinstance(self.eTime, dt.datetime), \
            logging.error('eTime must be datetime object or None')
        assert(self.channel == None or self.channel == 'all' or
               (isinstance(self.channel,str) and len(self.channel) == 1)), \
            logging.error('channel must be None or a 1-letter string')
        assert bmnum == None or isinstance(bmnum,int), \
            logging.error('bmnum must be an int or None')
        assert cp == None or isinstance(cp, int), \
            logging.error('cp must be an int or None')
        assert(fileType == 'rawacf' or fileType == 'fitacf' or
               fileType == 'fitex' or fileType == 'lmfit' or
               fileType == 'iqdat'), logging.error(estr)
        assert fileName == None or isinstance(fileName,str), \
            logging.error('fileName must be None or a string')
        assert isinstance(filtered, bool), \
            logging.error('filtered must be True of False')
        assert src == None or src == 'local' or src == 'sftp', \
            logging.error('src must be one of: None, local, sftp')

        # If channel is all, then make the channel a wildcard, then it will pull
        # in all UAF channels
        if self.channel=='all':
            channel = '.'

        if(self.eTime == None):
            self.eTime = self.sTime + dt.timedelta(days=1)

        filelist = []
        if fileType == 'fitex':
            arr = ['fitex', 'fitacf', 'lmfit']
        elif fileType == 'fitacf':
            arr = ['fitacf', 'fitex', 'lmfit']
        elif fileType == 'lmfit':
            arr = ['lmfit', 'fitex', 'fitacf']
        else:
            arr = [fileType]

        # a temporary directory to store a temporary file
        if tmpdir is None:
            try:
                tmpDir = davitpy.rcParams['DAVIT_TMPDIR']
            except:
                tmpDir = '/tmp/sd/'
        d = os.path.dirname(tmpDir)
        if not os.path.exists(d):
            os.makedirs(d)

        cached = False
        
        # FIRST, check if a specific filename was given
        if fileName != None:
            try:
                if(not os.path.isfile(fileName)):
                    estr = 'problem reading {:s} :file does '.format(fileName)
                    logging.error("{:s}not exist".format(estr))
                    return None
                outname = tmpDir + \
                          str(int(utils.datetimeToEpoch(dt.datetime.now())))
                if(string.find(fileName,'.bz2') != -1):
                    outname = string.replace(fileName,'.bz2','')
                    logging.debug('bunzip2 -c '+fileName+' > '+outname+'\n')
                    os.system('bunzip2 -c '+fileName+' > '+outname)
                elif(string.find(fileName,'.gz') != -1):
                    outname = string.replace(fileName,'.gz','')
                    logging.debug('gunzip -c '+fileName+' > '+outname+'\n')
                    os.system('gunzip -c '+fileName+' > '+outname)
                else:
                    os.system('cp '+fileName+' '+outname)
                    logging.debug('cp '+fileName+' '+outname)
                filelist.append(outname)
                self.dType = 'dmap'
            except Exception, e:
                logging.exception(e)
                logging.exception('problem reading file', fileName)
                return None
        # Next, check for a cached file
        if fileName == None and not noCache:
            try:
                if self.channel is None:
                    gl = glob.glob("%s????????.??????.????????.??????.%s.%s" %
                                   (tmpDir, radcode, fileType))
                    for f in gl:
                        try:
                            ff = string.replace(f, tmpDir, '')
                            # check time span of file
                            t1 = dt.datetime(int(ff[0:4]), int(ff[4:6]),
                                             int(ff[6:8]), int(ff[9:11]),
                                             int(ff[11:13]), int(ff[13:15]))
                            t2 = dt.datetime(int(ff[16:20]), int(ff[20:22]),
                                             int(ff[22:24]), int(ff[25:27]),
                                             int(ff[27:29]), int(ff[29:31]))
                            if t1 <= self.sTime and t2 >= self.eTime:
                                cached = True
                                filelist.append(f)
                                break
                        except Exception,e:
                            logging.exception(e)
                else:
                    gl = glob.glob("%s????????.??????.????????.??????.%s.%s.%s"
                                   % (tmpDir, radcode, self.channel, fileType))
                    for f in gl:
                        try:
                            ff = string.replace(f,tmpDir,'')
                            # check time span of file
                            t1 = dt.datetime(int(ff[0:4]), int(ff[4:6]),
                                             int(ff[6:8]), self.sTime.hour,
                                             self.sTime.minute, self.sTime.second)
                            t2 = dt.datetime(int(ff[16:20]), int(ff[20:22]),
                                             int(ff[22:24]), self.eTime.hour,
                                             self.eTime.minute, self.eTime.second)
                            # check if file covers our timespan
                            if t1 <= self.sTime and t2 >= self.eTime and t1.day == self.sTime.day:
                                cached = True
                                filelist.append(f)
                                break
                        except Exception, e:
                            logging.exception(e)
            except Exception,e:
                logging.exception(e)
        
        # Next, LOOK LOCALLY FOR FILES
        if not cached and (src == None or src == 'local') and fileName == None:
            try:
                for ftype in arr:
                    estr = "\nLooking locally for {:} files with".format(ftype)
                    estr = "{:} radcode: {:} channel: {:}".format(estr, radcode,
                                                               self.channel)
                    logging.info(estr)

                    # If the following aren't already, in the near future they
                    # will be assigned by a configuration dictionary much like
                    # matplotlib's rcsetup.py (matplotlibrc)
                    if local_dirfmt is None:
                        try:
                            local_dirfmt = \
                                    davitpy.rcParams['DAVIT_LOCAL_DIRFORMAT']
                        except:
                            local_dirfmt = '/mnt/nfs/home/SuperDARN/data/fitacf/'
                            estr = 'Config entry DAVIT_LOCAL_DIRFORMAT not set,'
                            estr = '{:s} using default: '.format(estr)
                            logging.exception("{:s}{:}".format(estr,
                                                               local_dirfmt))
                    local_dirfmt = '/mnt/nfs/home/SuperDARN/data/fitacf/{year}/{month}.{day}/'

                    if local_dict is None:
                        local_dict = {'radar':radcode, 'ftype':ftype,
                                      'channel':channel}
                    if 'ftype' in local_dict.keys():
                        local_dict['ftype'] = ftype

                    if local_fnamefmt is None:
                        try:
                            local_fnamefmt = \
                            davitpy.rcParams['DAVIT_LOCAL_FNAMEFMT'].split(',')
                        except:
                            local_fnamefmt = \
                              ['{date}.{hour}......{radar}.{ftype}',
                               '{date}.{hour}......{radar}.{channel}.{ftype}']
                            estr = 'Config entry DAVIT_LOCAL_FNAMEFMT not set, '
                            estr = '{:s} using default: '.format(estr)
                            logging.exception("{:s}{:}".format(estr,
                                                               local_fnamefmt))

                    outdir = tmpDir

                    # check to see if channel was specified and only use
                    # fnamefmts with channel in them
                    for f,fname in enumerate(local_fnamefmt):

                        if channel is not None and 'channel' not in fname:
                            local_fnamefmt.pop(f)
                    if len(local_fnamefmt) == 0:
                        estr = 'No file name formats containing channel exists!'
                        logging.error(estr)
                        break

                    # fetch the local files

                    temp = futils.fetch_local_files(self.sTime, self.eTime,
                                                    local_dirfmt, local_dict,
                                                    outdir, local_fnamefmt)

                    # check to see if the files actually have data between stime
                    # and etime
                    valid = self.__validate_fetched(temp, self.sTime,
                                                    self.eTime)
                    filelist = [x[0] for x in zip(temp,valid) if x[1]]
                    invalid_files = [x[0] for x in zip(temp,valid) if not x[1]]

                    if len(invalid_files) > 0:
                        for f in invalid_files:
                            logging.debug('removing invalid file: ' + f)
                            os.system('rm ' + f)

                    # If we have valid files then continue
                    if len(filelist) > 0:
                        self.fType = ftype
                        self.dType = 'dmap'
                        fileType = ftype
                        break
                    else:
                        estr = "couldn't find local [{}] data".format(ftype)
                        logging.info(estr)
            except Exception, e:
                logging.exception(e)
                estr = "Unable to read local data, possible problem with "
                estr = "{:s}local_dirfmt input or rcParameter ".format(estr)
                estr = "{:s}DAVIT_LOCAL_DIRFORMAT\nWill attempt to".format(estr)
                estr = "{:s} fetch data from remote.".format(estr)
                logging.exception(estr)
                src = None

        # Finally, check the SFTP server if we have not yet found files
        if((src == None or src == 'sftp') and self.__ptr == None and
           len(filelist) == 0 and fileName == None):
            for ftype in arr:
                estr = 'Looking on the SFTP server for {:} files'.format(ftype)
                logging.info(estr)
                try:
                    # If the following aren't already, in the near future
                    # they will be assigned by a configuration dictionary 
                    # much like matplotlib's rcsetup.py (matplotlibrc)
                    if remote_site is None:
                        try:
                            remote_site = davitpy.rcParams['DB']
                        except:
                            remote_site = 'sd-data.ece.vt.edu'
                            estr = 'Config entry DB not set, using default: '
                            logging.warning("{:s}{:}".format(estr, remote_site))
                    if username is None:
                        try:
                            username = davitpy.rcParams['DBREADUSER']
                        except:
                            username = 'sd_dbread'
                            estr = 'Config entry DBREADUSER not set, using '
                            estr = '{:s}default: {:s}'.format(estr, username)
                            logging.warning(estr)
                    if password is None:
                        try:
                            password = davitpy.rcParams['DBREADPASS']
                        except:
                            password = '5d'
                            estr = 'Config entry DBREADPASS not set, using '
                            estr = 'default: {:}'.format(estr, password)
                            logging.warning(estr)
                    if remote_dirfmt is None:
                        try:
                            remote_dirfmt = \
                                davitpy.rcParams['DAVIT_REMOTE_DIRFORMAT']
                        except:
                            remote_dirfmt = 'data/{year}/{ftype}/{radar}/'
                            estr = 'Config entry DAVIT_REMOTE_DIRFORMAT not '
                            estr = '{:s}set, using default: '.format(estr)
                            logging.warning('{:s}{:}'.format(estr,
                                                             remote_dirfmt))
                    if remote_dict is None:
                        remote_dict = {'ftype':ftype, 'channel':channel,
                                       'radar':radcode}
                    if 'ftype' in remote_dict.keys():
                        remote_dict['ftype'] = ftype
                    if remote_fnamefmt is None:
                        try:
                            remote_fnamefmt = \
                            davitpy.rcParams['DAVIT_REMOTE_FNAMEFMT'].split(',')
                        except:
                            remote_fnamefmt = \
                                ['{date}.{hour}......{radar}.{ftype}',
                                 '{date}.{hour}......{radar}.{channel}.{ftype}']
                            estr = 'Config entry DAVIT_REMOTE_FNAMEFMT not '
                            estr = '{:s}set, using default: '.format(estr)
                            estr = '{:s}{:}'.format(estr, remote_fnamefmt)
                            logging.warning(estr)
                    if port is None:
                        try:
                            port = davitpy.rcParams['DB_PORT']
                        except:
                            port = '22'
                            estr = 'Config entry DB_PORT not set, using '
                            estr = 'default: {:s}'.format(estr, str(port))
                            logging.warning(estr)

                    outdir = tmpDir

                    # check to see if channel was specified and only use
                    # fnamefmts with channel in them
                    for f,fname in enumerate(remote_fnamefmt):
                        if channel is not None and 'channel' not in fname:
                            remote_fnamefmt.pop(f)
                    if len(remote_fnamefmt) == 0:
                        estr = "no filename formats containing channel"
                        logging.error(estr)
                        break

                    # Now fetch the files
                    temp = futils.fetch_remote_files(self.sTime, self.eTime,
                                                     'sftp', remote_site,
                                                     remote_dirfmt, remote_dict,
                                                     outdir, remote_fnamefmt,
                                                     username=username,
                                                     password=password,
                                                     port=port)

                    # check to see if the files actually have data between
                    # stime and etime
                    valid = self.__validate_fetched(temp, self.sTime,
                                                    self.eTime)
                    filelist = [x[0] for x in zip(temp,valid) if x[1]]
                    invalid_files = [x[0] for x in zip(temp, valid) if not x[1]]

                    if len(invalid_files) > 0:
                        for f in invalid_files:
                            logging.debug('removing invalid file: ' + f)
                            os.system('rm ' + f)

                    # If we have valid files then continue
                    if len(filelist) > 0 :
                        estr = 'found {} data on sftp server'.format(ftype)
                        logging.info(estr)
                        self.fType = ftype
                        self.dType = 'dmap'
                        fileType = ftype
                        break
                    else:
                        estr = "couldn't find remote [{}]".format(ftype)
                        logging.info("{:s} data on".format(estr))
                except Exception, e:
                    logging.exception(e)
                    logging.exception('problem reading from sftp server')

        # check if we have found files
        if len(filelist) != 0:
            # concatenate the files into a single file
            if not cached:
                logging.info('Concatenating all the files in to one')
                # choose a temp file name with time span info for cacheing
                if (self.channel is None):
                    tmpName = '%s%s.%s.%s.%s.%s.%s' % \
                              (tmpDir, self.sTime.strftime("%Y%m%d"),
                               self.sTime.strftime("%H%M%S"),
                               self.eTime.strftime("%Y%m%d"),
                               self.eTime.strftime("%H%M%S"), radcode, fileType)
                else:
                    tmpName = '%s%s.%s.%s.%s.%s.%s.%s' % \
                              (tmpDir, self.sTime.strftime("%Y%m%d"),
                               self.sTime.strftime("%H%M%S"),
                               self.eTime.strftime("%Y%m%d"),
                               self.eTime.strftime("%H%M%S"),
                               radcode, self.channel, fileType)
                logging.debug('cat ' + string.join(filelist) + ' > ' + tmpName)
                os.system('cat ' + string.join(filelist) + ' > ' + tmpName)
                for filename in filelist:
                    logging.debug('rm ' + filename)
                    os.system('rm ' + filename)
            else:
                tmpName = filelist[0]
                self.fType = fileType
                self.dType = 'dmap'

            # filter(if desired) and open the file
            if not filtered:
                self.__filename=tmpName
                self.open()
            else:
                if not fileType+'f' in tmpName:
                    try:
                        fTmpName = tmpName + 'f'
                        command = 'fitexfilter ' + tmpName + ' > ' + fTmpName
                        logging.debug("performing: {:s}".format(command))
                        os.system(command)
                    except Exception, e:
                        estr = 'problem filtering file, using unfiltered'
                        logging.warning(estr)
                        fTmpName = tmpName
                else:
                    fTmpName = tmpName
                try:
                    self.__filename=fTmpName
                    self.open()
                except Exception, e:
                    logging.exception('problem opening file')
                    logging.exception(e)

        if(self.__ptr != None):
            if(self.dType == None): self.dType = 'dmap'
        else:
            logging.error('Sorry, we could not find any data for you :(')

    def __repr__(self):
        myStr = 'radDataPtr: \n'
        for key,var in self.__dict__.iteritems():
            if(isinstance(var, radBaseData) or isinstance(var, radDataPtr) or
               isinstance(var, type({}))):
                myStr += '%s = %s \n' % (key,'object')
            else:
                myStr += '%s = %s \n' % (key,var)
        return myStr

    def __del__(self):
        self.close() 

    def __iter__(self):
        return self

    def next(self):
        beam = self.readRec()
        if beam is None:
            raise StopIteration
        else:
            return beam

    def open(self):
        """open the associated dmap filename."""
        import os
        self.__fd = os.open(self.__filename,os.O_RDONLY)
        self.__ptr = os.fdopen(self.__fd)

    def createIndex(self):
        import datetime as dt
        from davitpy.pydarn.dmapio import getDmapOffset, readDmapRec
        from davitpy.pydarn.dmapio import setDmapOffset

        recordDict = {}
        scanStartDict = {}
        starting_offset = self.offsetTell()

        # rewind back to start of file
        self.rewind()
        while(1):
            # read the next record from the dmap file
            offset= getDmapOffset(self.__fd)
            dfile = readDmapRec(self.__fd)
            if(dfile is None):
                #if we dont have valid data, clean up, get out
                logging.info('reached end of data')
                break
            else:
                if(dt.datetime.utcfromtimestamp(dfile['time']) >= self.sTime and
                   dt.datetime.utcfromtimestamp(dfile['time']) <= self.eTime):
                    rectime = dt.datetime.utcfromtimestamp(dfile['time'])
                    recordDict[rectime] = offset
                    if dfile['scan'] == 1: scanStartDict[rectime] = offset
        # reset back to before building the index 
        self.recordIndex = recordDict
        self.offsetSeek(starting_offset)
        self.scanStartIndex = scanStartDict
        return recordDict, scanStartDict

    def offsetSeek(self,offset,force=False):
        """jump to dmap record at supplied byte offset.
        Require offset to be in record index list unless forced. 
        """
        from davitpy.pydarn.dmapio import setDmapOffset, getDmapOffset
        if force:
            return setDmapOffset(self.__fd, offset)
        else:
            if self.recordIndex is None:        
                self.createIndex()
            if offset in self.recordIndex.values():
                return setDmapOffset(self.__fd,offset)
            else:
                return getDmapOffset(self.__fd)

    def offsetTell(self):
        """jump to dmap record at supplied byte offset. 
        """
        from davitpy.pydarn.dmapio import getDmapOffset
        return getDmapOffset(self.__fd)

    def rewind(self):
        """jump to beginning of dmap file."""
        from davitpy.pydarn.dmapio import setDmapOffset 
        return setDmapOffset(self.__fd,0)

    def readScan(self, firstBeam=None, useEvery=None, warnNonStandard=True,
                 showBeams=False):
        """A function to read a full scan of data from a
        :class:`pydarn.sdio.radDataTypes.radDataPtr` object. 
        This function is capable of reading standard scans and extracting
        standard scans from patterned or interleaved scans (see Notes).

        Parameters
        ----------
        firstBeam : (int/NoneType)
            If manually specifying a scan pattern, will start picking beams at
            this index in the scan. Requires useEvery to also be specified.
            (default=None)
        useEvery : (int/NoneType)
            If manually specifying a scan pattern, will pick every `useEvery`
            beam. Requires firstBeam to also be specified. (default=None)
        warnNonStandard : (bool)
            If True, display a warning when auto-detecting a non-standard scan
            pattern (``firstBeam != 0`` or ``useEvery != 1``). (default=True)
        showBeams : (bool)
            `showBeams` will print the collected scan numbers. Useful for
            debugging or if you manually want to find the correct combination
            of `firstBeam` and `useEvery`. (default=False)

        Returns
        -------
        myScan : :class:`~pydarn.sdio.radDataTypes.scanData` or None
            A sequence of beams (``None`` when no more data are available)

        Notes
        -----
        For patterned scans (e.g. if beam numbers are [5, 0, 5, 1, 5, 2, ...])
        the function will try to find  a subset of the beams where beam numbers
        are increasing/decreasing by 1 throughout the scan.  Alternatively you
        can specify the pattern manually by using `firstBeam` and `useEvery`.
        You will then get the subset of the beams starting at `firstBeam`
        (which is the beam's index in the list of beams in the scan, not the
        beam number) and only including every `useEvery` beam.

        This will ignore any bmnum request in
        :func:`~pydarn.sdio.radDataRead.radDataOpen`.
        Also, if no channel was specified, it will only read channel 'a'.
        """
        from davitpy.pydarn.sdio import scanData
        from davitpy import pydarn

        if None in [firstBeam, useEvery] and firstBeam is not useEvery:
            estr = 'firstBeam and useEvery must both either be None or '
            raise ValueError('{:s}specified'.format(estr))

        # Save the radDataPtr's bmnum setting temporarily and set it to None
        orig_beam = self.bmnum
        self.bmnum = None

        if self.__ptr is None:
            estr = 'Self.__ptr is None.  There is probably no data available '
            logging.error('{:s}for your selected time.'.format(estr))
            self.bmnum = orig_beam
            return None

        if self.__ptr.closed:
            logging.error('Your file pointer is closed')
            self.bmnum = orig_beam
            return None

        myScan = scanData()

        # get first beam in the scan
        myBeam = self.readRec()
        if myBeam is None:  # no more data
            self.bmnum = orig_beam
            return None
        while not myBeam.prm.scan:
            # continue to read until we encounter a set scan flag
            myBeam = self.readRec()
            if myBeam is None:
                # no more data
                self.bmnum = orig_beam
                return None

        # myBeam is now the first beam we encountered where scan flag is set
        myScan.append(myBeam)
        firstBeamNum = myBeam.bmnum

        # get the rest of the beams in the scan
        while True:
            # get current offset (in case we have to revert) and next beam
            offset = pydarn.dmapio.getDmapOffset(self.__fd)
            myBeam = self.readRec()
            if myBeam is None:
                # no more data
                break

            # Scan detection algorithm: We have a new scan if scan flag
            # is set AND beam number is the same as the first beam number
            # in the previous scan.
            # The latter condition is important since we can encounter
            # patterned scans with
            #   scan flags:    [1, 1, 0, 0, 0, 0, ...]
            #   beam numbers:  [5, 0, 5, 1, 5, 2, ...]
            # and we don't want to break out on the 2nd beam in this case.
            if myBeam.prm.scan and myBeam.bmnum == firstBeamNum:
                # if start of (next) scan revert offset to start of scan and
                # break out of loop
                pydarn.dmapio.setDmapOffset(self.__fd, offset)
                break
            else:
                # append beam to current scan
                myScan.append(myBeam)

        self.bmnum = orig_beam

        # use scan pattern from parameters if given
        if None not in [firstBeam, useEvery]:
            if showBeams:
                estr = 'Beam numbers in scan pattern for firstBeam='
                estr = '{:s}{}, useEvery={}: '.format(estr, firstBeam, useEvery)
                estr = '{:s}{}'.format(estr, [beam.bmnum for beam in myScan])
                logging.info(estr)
            # return None if scan is empty
            return myScan[firstBeam::useEvery] or None

        # try to find the scan pattern automatically
        import itertools
        import numpy as np
        for firstBeam, useEvery in itertools.product(range(24), range(1, 24)):
            scan = myScan[firstBeam::useEvery]
            bmnums = [beam.bmnum for beam in scan]
            # assume correct pattern if beam numbers are increasing/decreasing
            # by one throughout the scan
            if np.all(np.diff(bmnums) == 1) or np.all(np.diff(bmnums) == -1):
                if showBeams or (warnNonStandard and (firstBeam != 0 or
                                                      useEvery != 1)):
                    estr = 'Auto-detected scan pattern with firstBeam='
                    estr = '{:s}{}, useEvery='.format(estr, firstBeam)
                    estr = '{:s}{} beam numbers are '.format(estr, useEvery)
                    estr = '{:s}{}'.format(estr, [beam.bmnum for beam in scan])
                    logging.info(estr)
                # return None if scan is empty
                return scan or None
        # the only reason for not having returned yet is that the automatic
        # detection failed
        estr = 'Auto-detection of scan pattern failed, set pattern manually '
        estr = '{:s}using the firstBeam and useEvery parameters'.format(estr)
        raise ValueError(estr)

    def readRec(self):
        """A function to read a single record of radar data from a
        :class:`pydarn.sdio.radDataTypes.radDataPtr` object

        Returns
        ---------
        myBeam : (:class:`pydarn.sdio.radDataTypes.beamData`/NoneType)
        an object filled with the data we are after.  Will return None when
        finished reading.
        """
        from davitpy.pydarn.sdio.radDataTypes import radDataPtr, beamData, \
            fitData, prmData, rawData, iqData, alpha
        from davitpy import pydarn
        import datetime as dt

        # check input
        if(self.__ptr == None):
            logging.error('Your pointer does not point to any data')
            return None
        if self.__ptr.closed:
            logging.error('Your file pointer is closed')
            return None
        myBeam = beamData()
        # do this until we reach the requested start time
        # and have a parameter match
        while(1):
            offset=pydarn.dmapio.getDmapOffset(self.__fd)
            dfile = pydarn.dmapio.readDmapRec(self.__fd)
            # check for valid data
            if(dfile == None or
               dt.datetime.utcfromtimestamp(dfile['time']) > self.eTime):
                # if we dont have valid data, clean up, get out
                logging.info('reached end of data')
                #self.close()
                return None
            # check that we're in the time window, and that we have a 
            # match for the desired params
            # if dfile['channel'] < 2: channel = 'a'  THIS CHECK IS BAD.
            # 'channel' in a dmap file specifies STEREO operation or not.
            #else: channel = alpha[dfile['channel']-1]
            if(dt.datetime.utcfromtimestamp(dfile['time']) >= self.sTime and
               dt.datetime.utcfromtimestamp(dfile['time']) <= self.eTime and
               (self.stid == None or self.stid == dfile['stid']) and
               #(self.channel == None or self.channel == channel) and
               # ASR removed because of bad check as above.
               (self.bmnum == None or self.bmnum == dfile['bmnum']) and
               (self.cp == None or self.cp == dfile['cp'])):
                # fill the beamdata object
                myBeam.updateValsFromDict(dfile)
                myBeam.recordDict = dfile
                myBeam.fType = self.fType
                myBeam.fPtr = self
                myBeam.offset = offset
                # file prm object
                myBeam.prm.updateValsFromDict(dfile)
                if myBeam.fType == "rawacf":
                    myBeam.rawacf.updateValsFromDict(dfile)
                if myBeam.fType == "iqdat":
                    myBeam.iqdat.updateValsFromDict(dfile)
                if(myBeam.fType == 'fitacf' or myBeam.fType == 'fitex' or
                   myBeam.fType == 'lmfit'):
                    myBeam.fit.updateValsFromDict(dfile)
                if myBeam.fit.slist == None:
                    myBeam.fit.slist = []
                return myBeam

    def close(self):
        """close associated dmap file."""
        import os

        if self.__ptr is not None:
            self.__ptr.close()
            self.__fd = None

    def __validate_fetched(self,filelist,stime,etime):
        """ This function checks if the files in filelist contain data
        for the start and end times (stime,etime) requested by a user.

        Parameters
        -------------
        filelist : (list)
            List of filenames 
        stime : (datetime.datetime)
            Starting time for list of filenames
        etime : (datetime.datetime)
            Ending time for list of filenames

        Returns:
        List of booleans. True if a file contains data in the time
        range (stime, etime)
        """
        # This method will need some modification for it to work with
        # file formats that are NOT DMAP (i.e. HDF5). Namely, the dmapio
        # specific code will need to be modified (readDmapRec).
        import os
        import datetime as dt
        import numpy as np
        from davitpy.pydarn.dmapio import readDmapRec

        valid = []

        for f in filelist:
            logging.debug('Checking file: ' + f)
            stimes = []
            etimes = []

            # Open the file and create a file pointer
            self.__filename = f
            self.open()

            # Iterate through the file and grab the start time for beam
            # integration and calculate the end time from intt.sc and intt.us
            while(1):
                # read the next record from the dmap file
                dfile = readDmapRec(self.__fd)
                if(dfile is None):
                    break
                else:
                    temp = dt.datetime.utcfromtimestamp(dfile['time'])
                    stimes.append(temp)
                    sec = dfile['intt.sc'] + dfile['intt.us'] / (10. ** 6)
                    etimes.append(temp + dt.timedelta(seconds=sec))
            # Close the file and clean up
            self.close()
            self.__ptr = None

            inds = np.where((np.array(stimes) >= stime) &
                            (np.array(stimes) <= etime))
            inde = np.where((np.array(etimes) >= stime) &
                            (np.array(etimes) <= etime))
            if (np.size(inds) > 0) or (np.size(inde) > 0):
                valid.append(True)
            else:
                valid.append(False)

        return valid



class radBaseData():
    """a base class for the radar data types.  This allows for single
    definition of common routines

    Parameters
    -----------
    None

    Methods
    --------
    copyData : (func)
        Recursively copy contents into a new object
    updateValsFromDict : (func)
        converts a dict from a dmap file to radBaseData
    
    Written by AJ 20130108
    """
  
    def copyData(self,obj):
        """This method is used to recursively copy all of the contents from
        input object to self

        Parameters
        -----------
        obj : (:class:`pydarn.sdio.radDataTypes.radBaseData`)
            the object to be copied

        Returns
        --------
        Void

        Example
        ::

        myradBaseData.copyData(radBaseDataObj)
      
        Note
        -----
        In general, users will not need to use this.

        written by AJ, 20130402
        """
        for key, val in obj.__dict__.iteritems():
            if isinstance(val, radBaseData):
                try:
                    getattr(self, key).copyData(val)
                except:
                    pass
            else:
                setattr(self, key, val)

    def updateValsFromDict(self, aDict):
        """A function to to fill a radar params structure with the data in a
        dictionary that is returned from the reading of a dmap file
	
        		Parameters
        ------------
        aDict : (dict)
        	The dictionary containing the radar data
	
        Returns
        --------
        Void
	
        Note
        ------
        In general, users will not need to us this.
        
        Written by AJ 20121130
        """
        import datetime as dt
        for attr, value in self.__dict__.iteritems():
        	if(attr == 'channel'):
        		if aDict.has_key('channel'):
        			self.channel = aDict['channel']
        		continue
        	elif(attr == 'inttus'):
        		if aDict.has_key('intt.us'): 
        			self.inttus = aDict['intt.us']
        		continue
        	elif(attr == 'inttsc'):
        		if aDict.has_key('intt.sc'): 
        			self.inttsc = aDict['intt.sc']
        		elif('sc' in aDict.get('intt',{})):
        			self.inttsc = aDict['intt']['sc']
        		continue
        	elif(attr == 'statlopwr'):
        		if aDict.has_key('stat.lopwr'): 
        			self.statlopwr = aDict['stat.lopwr']
        		elif('lopwr' in aDict.get('stat',{})):
        			self.statlopwr = aDict['stat']['lopwr']
        		continue
        	elif(attr == 'statagc'):
        		if aDict.has_key('stat.agc'): 
        			self.statagc = aDict['stat.agc']
        		elif('agc' in aDict.get('stat',{})):
        			self.statagc = aDict['stat']['agc']
        		continue
        	elif(attr == 'noisesky'):
        		if aDict.has_key('noise.sky'): 
        			self.noisesky = aDict['noise.sky']
        		elif('sky' in aDict.get('noise',{})):
        			self.noisesky = aDict['noise']['sky']
        		continue
        	elif(attr == 'noisesearch'):
        		if aDict.has_key('noise.search'): 
        			self.noisesearch = aDict['noise.search']
        		elif('search' in aDict.get('noise',{})):
        			self.noisesearch = aDict['noise']['search']
        		continue
        	elif(attr == 'noisemean'):
        		if aDict.has_key('noise.mean'): 
        			self.noisemean = aDict['noise.mean']
        		elif('mean' in aDict.get('noise',{})):
        			self.noisemean = aDict['noise']['mean']
        		continue
        	elif(attr == 'acfd' or attr == 'xcfd'):
        		if(attr in aDict): 
        			setattr(self,attr,[])
        			for i in range(self.parent.prm.nrang):
        				rec = []
        				for j in range(self.parent.prm.mplgs):
        					samp = []
        					for k in range(2):
        						samp.append(aDict[attr][(i*self.parent.prm.mplgs+j)*2+k])
        					rec.append(samp)
        				getattr(self, attr).append(rec)
        		else: setattr(self,attr,[])
        		continue
        	elif(attr == 'mainData'):
        		if('data' in aDict): 
        			if(len(aDict['data']) == aDict['smpnum']*aDict['seqnum']*2*2): fac = 2
        			else: fac = 1
        			setattr(self,attr,[])
        			for i in range(aDict['seqnum']):
        				rec = []
        				for j in range(aDict['smpnum']):
        					samp = []
        					for k in range(2):
        						samp.append(aDict['data'][(i*fac*aDict['smpnum']+j)*2+k])
        				rec.append(samp)
        			getattr(self, attr).append(rec)
        		else: setattr(self,attr,[])
        		continue
        	elif(attr == 'intData'):
        		if aDict.has_key('data'): 
        			if(len(aDict['data']) ==
        				aDict['smpnum'] * aDict['seqnum'] * 2 * 2):
        				fac = 2
        			else:
        				continue
        			setattr(self, attr, [])
        			for i in range(aDict['seqnum']):
        				rec = []
        				for j in range(aDict['smpnum']):
        					samp = []
        					for k in range(2):
        						aa = ((i * fac + 1) * aDict['smpnum']
        						+ j) * 2 + k
        						samp.append(aDict['data'][aa])
         					rec.append(samp)
        				getattr(self, attr).append(rec)
        		else:
        			setattr(self, attr, [])
        		continue
        	try:
        		setattr(self, attr, aDict[attr])
        	except:
        		#put in a default value if not another object
        		if(not isinstance(getattr(self, attr), radBaseData)):
        			setattr(self, attr, None)
          

    
class scanData(list):
    """a class to contain a radar scan.  Extends list.
    Just a list of :class:`pydarn.sdio.radDataTypes.beamData` objects
  
    Attributes
    ----------
    None

    Example
    --------
    ::

    myBeam = pydarn.sdio.scanData()

    Written by AJ 20121130
    """

    def __init__(self):
        pass
  
class beamData(radBaseData):
	"""a class to contain the data from a radar beam sounding,
	extends class :class:`pydarn.sdio.radDataTypes.radBaseData`
	
	Attributes
	-----------
	cp : (int)
	radar control program id number
	stid : (int)
	radar station id number
	time : (datetime)
	timestamp of beam sounding
	channel (int)
	radar operating channel defined by STEREO operations, eg 0, 1, 2.
	Zero is for non-stereo operations and 1 & 2 are for STEREO operations
	of A & B channels
	bmnum : (int)
	beam number
	prm : (pydarn.sdio.radDataTypes.prmData)
	operating params
	fit : (pydarn.sdio.radDataTypes.fitData)
	fitted params
	rawacf : (pydarn.sdio.radDataTypes.rawData)
	rawacf data
	iqdat : (pydarn.sdio.radDataTypes.iqData)
	iqdat data_f
	fType : (str)
	the file type, 'fitacf', 'rawacf', 'iqdat', 'fitex', 'lmfit'
	
	Example
	--------
	::
	
	myBeam = pydarn.sdio.radBeam()
	
	Written by AJ 20121130
	"""
	def __init__(self, beamDict=None, myBeam=None, proctype=None):
		#initialize the attr values
		self.cp = None
		self.stid = None
		self.time = None
		self.bmnum = None
		self.channel = None
		self.exflg = None
		self.lmflg = None
		self.acflg = None
		self.rawflg = None
		self.iqflg = None
		self.fitex = None
		self.fitacf = None
		self.lmfit= None
		self.fit = fitData()
		self.rawacf = rawData(parent=self)
		self.prm = prmData()
		self.iqdat = iqData()
		self.recordDict = None 
		self.fType = None
		self.offset = None
		self.fPtr = None 
		#if we are intializing from an object, do that
		if(beamDict != None):
			self.updateValsFromDict(beamDict)
	
	def __repr__(self):
		import datetime as dt
		myStr = 'Beam record FROM: ' + str(self.time) + '\n'
		for key,var in self.__dict__.iteritems():
			if(isinstance(var, radBaseData) or isinstance(var, radDataPtr) or
			   isinstance(var, type({}))):
				myStr += '%s  = %s \n' % (key, 'object')
			else:
				myStr += '%s  = %s \n' % (key, var)
		return myStr
	
class prmData(radBaseData):
	"""A class to represent radar operating parameters, extends :class:`pydarn.sdio.radDataTypes.radBaseData`
	
	**Attrs**:
	* **nave**  (int): number of averages
	* **combf**	(int): comment
	* **lagfr**  (int): lag to first range in us
	* **smsep**  (int): sample separation in us
	* **ercod**  (int): Error indicator
	* **bmazm**  (float): beam azimuth
	* **scan**  (int): new scan flag
	* **rxrise**  (int): receiver rise time
	* **inttsc**  (int): integeration time (sec)
	* **inttus**  (int): integration time (us)
	* **mpinc**  (int): multi pulse increment (tau, basic lag time) in us
	* **mppul**  (int): number of pulses
	* **mplgs**  (int): number of lags
	* **mplgexs**  (int): number of lags (tauscan)
	* **nrang**  (int): number of range gates
	* **frang**  (int): first range gate (km)
	* **rsep**  (int): range gate separation in km
	* **xcf**  (int): xcf flag
	* **tfreq**  (int): transmit freq in kHz
	* **ifmode**  (int): if mode flag
	* **ptab**  (mppul length list): pulse table
	* **ltab**  (mplgs x 2 length list): lag table
	* **noisemean**  (float): mean noise level
	* **noisesky**  (float): sky noise level
	* **noisesearch**  (float): freq search noise level
	* **statlopwr**
	* **statagc**
	* **atten**
	
	Written by AJ 20121130
	"""
	
	#initialize the struct
	def __init__(self, prmDict=None, myPrm=None):
		#set default values
		self.nave = None        #number of averages
		self.combf = None		#comments
		self.lagfr = None       #lag to first range in us
		self.smsep = None       #sample separation in us
		self.ercod = None		#error indicator
		self.bmazm = None       #beam azimuth
		self.scan = None        #new scan flag
		self.rxrise = None      #receiver rise time
		self.inttsc = None      #integeration time (sec)
		self.inttus = None      #integration time (us)
		self.mpinc = None       #multi pulse increment (tau, basic lag time) in us
		self.mppul = None       #number of pulses
		self.mplgs = None       #number of lags
		self.mplgexs = None     #number of lags (tauscan)
		self.nrang = None       #number of range gates
		self.frang = None       #first range gate (km)
		self.rsep = 0        #range gate separation in km
		self.xcf = None         #xcf flag
		self.tfreq = 0       #transmit freq in kHz
		self.ifmode = None      #if mode flag
		self.ptab = None        #pulse table
		self.ltab = None        #lag table
		self.noisemean = None   #mean noise level
		self.noisesky = None    #sky noise level
		self.noisesearch = None #freq search noise level
		self.statlopwr = None
		self.statagc = None
		self.atten = None
		
		#if we are copying a structure, do that
		if(prmDict != None):
			self.updateValsFromDict(prmDict)
	
	def __repr__(self):
		import datetime as dt
		myStr = 'Prm data: \n'
		for key,var in self.__dict__.iteritems():
			myStr += '%s  = %s \n' % (key, var)
		return myStr
	
class fitData(radBaseData):
	"""a class to contain the fitted params of a radar beam sounding, extends :class:`pydarn.sdio.radDataTypes.radBaseData`
	
	**Attrs**:
	* **pwr0**  (prm.nrang length list): lag 0 power
	* **slist**  (npnts length list): list of range gates with backscatter
	* **npnts** (int): number of range gates with scatter
	* **nlag**  (npnts length list): number of good lags
	* **qflg**  (npnts length list): quality flag
	* **gflg**  (npnts length list): ground scatter flag
	* **p_l**  (npnts length list): lambda power
	* **p_l_e**  (npnts length list): lambda power error
	* **p_s**  (npnts length list): sigma power
	* **p_s_e**  (npnts length list): sigma power error
	* **v**  (npnts length list): velocity
	* **v_e**  (npnts length list): velocity error
	* **w_l**  (npnts length list): lambda spectral width
	* **w_l_e**  (npnts length list): lambda width error
	* **w_s**  (npnts length list): sigma spectral width
	* **w_s_e**  (npnts length list): sigma width error
	* **phi0**  (npnts length list): phi 0
	* **phi0_e**  (npnts length list): phi 0 error
	* **elv**  (npnts length list): elevation angle
	
	**Example**: 
	::
	
	myFit = pydarn.sdio.fitData()
	
	Written by AJ 20121130
	"""
	
	#initialize the struct
	def __init__(self, fitDict=None, myFit=None):
		self.pwr0 = None      #lag 0 power
		self.slist = None     # list of range gates with backscatter
		self.npnts = None     #number of range gates with scatter
		self.nlag = None      #number of good lags
		self.qflg = None      #quality flag
		self.gflg = None      #ground scatter flag
		self.p_l = None       #lambda power
		self.p_l_e = None     #lambda power error
		self.p_s = None       #sigma power
		self.p_s_e = None     #sigma power error
		self.v = None         #velocity
		self.v_e = None       #velocity error
		self.w_l = None       #lambda spectral width
		self.w_l_e = None     #lambda width error
		self.w_s = None       #sigma spectral width
		self.w_s_e = None     #sigma width error
		self.phi0 = None      #phi 0
		self.phi0_e = None    #phi 0 error
		self.elv = None       #elevation angle
		
		if(fitDict != None): self.updateValsFromDict(fitDict)
	
	def __repr__(self):
		import datetime as dt
		myStr = 'Fit data: \n'
		for key,var in self.__dict__.iteritems():
		  myStr += key+' = '+str(var)+'\n'
		return myStr
	
class rawData(radBaseData):
	"""a class to contain the rawacf data from a radar beam sounding, extends :class:`pydarn.sdio.radDataTypes.radBaseData`
	
	**Attrs**:
	* **acfd** (nrang x mplgs x 2 length list): acf data
	* **xcfd** (nrang x mplgs x 2 length list): xcf data
	
	**Example**: 
	::
	
	myRaw = pydarn.sdio.rawData()
	
	Written by AJ 20130125
	"""
	
	#initialize the struct
	def __init__(self, rawDict=None, parent=None):
		self.pwr0 = []       #acf data
		self.acfd = []      #acf data
		self.xcfd = []      #xcf data
		self.parent = parent #reference to parent beam
		
		if(rawDict != None): self.updateValsFromDict(rawDict)
	
	def __repr__(self):
		import datetime as dt
		myStr = 'Raw data: \n'
		for key,var in self.__dict__.iteritems():
		  myStr += key+' = '+str(var)+'\n'
		return myStr
	
class iqData(radBaseData):
	""" a class to contain the iq data from a radar beam sounding, extends :class:`pydarn.sdio.radDataTypes.radBaseData`
	
	.. warning::
	I'm not sure what all of the attributes mean.  if somebody knows what these are, please help!
	
	**Attrs**:
	* **chnnum** (int): number of channels?
	* **smpnum** (int): number of samples per pulse sequence
	* **skpnum** (int): number of samples to skip at the beginning of a pulse sequence?
	* **seqnum** (int): number of pulse sequences
	* **tbadtr** (? length list): time of bad tr samples?
	* **tval** (? length list): ?
	* **atten** (? length list): ?
	* **noise** (? length list): ?
	* **offset** (? length list): ?
	* **size** (? length list): ?
	* **badtr** (? length list): bad tr samples?
	* **mainData** (seqnum x smpnum x 2 length list): the actual iq samples (main array)
	* **intData** (seqnum x smpnum x 2 length list): the actual iq samples (interferometer)
	
	**Example**: 
	::
	
	myIq = pydarn.sdio.iqData()
	
	Written by AJ 20130116
	"""
	
	#initialize the struct
	def __init__(self, iqDict=None, parent=None):
		self.seqnum = None
		self.chnnum = None
		self.smpnum = None
		self.skpnum = None
		self.btnum = None
		self.tsc = None
		self.tus = None
		self.tatten = None
		self.tnoise = None
		self.toff = None
		self.tsze = None
		self.tbadtr = None
		self.badtr = None
		self.mainData = []
		self.intData = []
		
		if(iqDict != None): self.updateValsFromDict(iqDict)
	
	def __repr__(self):
		import datetime as dt
		myStr = 'IQ data: \n'
		for key,var in self.__dict__.iteritems():
		  myStr += key+' = '+str(var)+'\n'
		return myStr
	

