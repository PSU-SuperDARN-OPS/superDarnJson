from pydarn.sdio import beamData, scanData
import logging
from twisted.internet import reactor, protocol, threads
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import LineReceiver
from pydarn.sdio import beamData, scanData
import json
from Queue import Queue 
import threading
import os, errno
import subprocess
from rtiJS import plotRti
from geoJS import plotFan
from fgpJS import plotFgpJson
import matplotlib.pyplot as plot
import sys 
sys.path.append('~/davitpy')
import datetime,pytz
import numpy as np
import pydarn
import utils
from pydarn.proc.music import getDataSet

'''
ProcessData(self)
clears figure, calls graphing method, saves figure

'''
class geoThread(threading.Thread):
	
	def __init__(self, parent,data):
		super(geoThread, self).__init__()
		self.parent = parent
		self.data = data
		self.stoprequest = threading.Event()

	def run(self):
	
		while not self.data.empty():
			myScan = self.data.get(True, 1)
			#print 'myScan=',myScan
			for mb in myScan:
				myBeam = beamData()
				myBeam = mb
				break
		while not self.stoprequest.isSet():
			timeNow = datetime.datetime.utcnow()
			myBeam.time = myBeam.time.replace(tzinfo=None)
			while not self.data.empty():
				myBeam = beamData()
				myBeam = self.data.get()
				#print 'myBeam=',myBeam
				myScan.pop(myBeam.bmnum)
				myScan.insert(myBeam.bmnum,myBeam)
			
		
			try:
				self.parent.geo['figure'] = plotFan(myScan,[self.parent.rad],
					fovs = self.parent.fovs,
					params=self.parent.geo['param'],
					gsct=self.parent.geo['gsct'], 
					maxbeams = int(self.parent.maxbeam[0]),
					maxgates=int(self.parent.nrangs[0]),	
					scales=self.parent.geo['sc'],
					drawEdge = self.parent.geo['drawEdge'], 
					myFigs = self.parent.geo['figure'],
					bmnum = myBeam.bmnum,
					site = self.parent.site,
					tfreq = myBeam.prm.tfreq,
					noise = myBeam.prm.noisesearch,
					rTime=myBeam.time,
					title = self.parent.names[0],
					dist = self.parent.dist,
					llcrnrlon = self.parent.llcrnrlon,
					llcrnrlat = self.parent.llcrnrlat,
					urcrnrlon = self.parent.urcrnrlon,
					urcrnrlat = self.parent.urcrnrlat,
					lon_0 = self.parent.lon_0,
					lat_0 = self.parent.lat_0,
					merGrid = self.parent.geo['merGrid'],
					merColor = self.parent.geo['merColor'],
					continentBorder = self.parent.geo['continentBorder'],
					waterColor = self.parent.geo['waterColor'],
					continentColor = self.parent.geo['continentColor'],
					backgColor = self.parent.geo['backgColor'],
					gridColor = self.parent.geo['gridColor'],
					filepath = self.parent.filepath[0])
			except:
				logging.error('geographic plot missing info')
				logging.error('Geo Figure: %s'%(sys.exc_info()[0]))
			logging.info('Updated Geographic Plot')
			for i in range(len(self.parent.fan['figure'])):
				try:
					self.parent.fan['figure'][i].clf()
					self.parent.fan['figure'][i]=plotFgpJson(myScan,self.parent.rad,
						params=[self.parent.fan['param'][i]],
						gsct=self.parent.fan['gsct'],
						scales=[self.parent.fan['sc'][i]],
						bmnum = myBeam.bmnum,
						figure = self.parent.fan['figure'][i],
						tfreq = myBeam.prm.tfreq,
						noise = myBeam.prm.noisesearch,
						rTime=myBeam.time,
						title = self.parent.names[0])
					self.parent.fan['figure'][i].savefig("%sfan_%s" % (self.parent.filepath[0],self.parent.fan['param'][i]))
				except:
					logging.error('fan plot missing info')
					logging.error('Fan Figure: %s'%(sys.exc_info()[0]))
				logging.info('Updated Fan Plot')
				
	def join(self, timeout=None):
		self.stoprequest.set()
		logging.info("Closing geoThread")
		super(geoThread, self).join(timeout)

class timeThread(threading.Thread):
	
	def __init__(self, parent, data):
		super(timeThread, self).__init__()
		self.parent = parent
		self.data = data
		self.stoprequest = threading.Event()
	
	def run(self):
		myBeamList = scanData()
		while not self.stoprequest.isSet():

			while not self.data.empty():
				myBeam = beamData()
				myBeam = self.data.get(True, 10)
				timeNow = datetime.datetime.utcnow()
				myBeam.time = myBeam.time.replace(tzinfo=None)
				myBeamList.append(myBeam)
				if len(myBeamList)>2:
					try:
						self.parent.time['figure'].clf()
						self.parent.time['figure']=plotRti(myBeamList,
								self.parent.rad,
								params=self.parent.time['param'],
								scales=self.parent.time['sc'],
								gsct=self.parent.time['gsct'],
								bmnum = int(self.parent.beams[0]),
								figure = self.parent.time['figure'],
								rTime = myBeam.time,
								title = self.parent.names[0])
						self.parent.time['figure'].savefig("%stime" % (self.parent.filepath[0]))
					except:
						logging.error('time plot missing info')
						logging.error('Time Figure: %s' %(sys.exc_info()[0]))
					logging.info('Updated Time Plot')
	def join(self, timeout=None):
		self.stoprequest.set()
		logging.info("Closing timeThread")
		super(timeThread, self).join(timeout)
					


def processMsg(self):
    #logging.info('Msg: %s' % str(self.data))
    #json loads the data
    #import pdb 
    #pdb.set_trace()
    try:
        dic = json.loads(self.data)
    except ValueError:
        # errors out if we got multiple packets (race condition)
        # If we get more than one dictionary, just skip the whole thing
        # this shouldn't happen very often
        logging.info("Error decoding dictionary, skipping packet")
        return
    
    #prm data update
    self.parent.myBeam = beamData()
    self.parent.myBeam.updateValsFromDict(dic)
    self.parent.myBeam.prm.updateValsFromDict(dic)
    '''
    if self.parent.myBeam.prm.rsep != self.parent.site.rsep:
        logging.info('Difference in rsep: %s' % str(self.parent.site.rsep),' : ',str(self.parent.myBeam.prm.rsep))
        self.parent.site.rsep = self.parent.myBeam.prm.rsep
        createData(self)
    '''
    self.endP = False

    #fit data update and param noisesky
    self.parent.myBeam.fit.updateValsFromDict(dic)
    self.parent.myBeam.prm.noisesky = dic['noise.sky']



    #updates time to a datetime string
    #time = self.parent.myBeam.time
    #self.parent.myBeam.time = datetime.datetime(time['yr'],time['mo'],\
    #time['dy'],time['hr'],time['mt'],time['sc'])
    self.parent.myBeam.time = datetime.datetime(dic['time.yr'],dic['time.mo'],\
    	dic['time.dy'],dic['time.hr'],dic['time.mt'],dic['time.sc']) 

    logging.info("Proccessing Beam: %s Time: %s" % (str(self.parent.myBeam.bmnum),str(self.parent.myBeam.time)))
    #inserts removes and inserts new beam data
    self.gque.put(self.parent.myBeam)
    if self.parent.myBeam.bmnum == int(self.parent.beams[0]):
        self.tque.put(self.parent.myBeam)
    logging.info("Proccessing packet: %s" % (str(self.parent.i)))
    self.parent.i = self.parent.i+1
    self.endP = True


def incommingData(self,data):	
    #As soon as any data is received, write it back.
    #print 'Self.data: ',self.data
    #logging.info('Start self.Data: %s' % str(self.data))

    self.find = str.find
    start_count = self.data.count('["{')
    if start_count != 0:
        start_count -= 1
    #logging.info('Start Count: %s' % str(start_count))
    i = 0
    #logging.info('Data: %s' % str(data))
    self.data = data

    while i <= start_count:
        #logging.info('Looping self.Data: %s' % str(self.data))
        indS = self.find(self.data,'{"')
        indF = self.find(self.data,']}')
        #print "Self data has data"
        #print "indS: ",indS," indF: ",indF
        self.parseS = True
        if indS == -1 or indF == -1:
            if indS != -1:
                self.parseP = True
                #logging.info("Self data complete data")
                indF = self.find(data,'}]')
            else:
                #logging.info("Self data doesn't have data")
                indS = self.find(data,'{"')
                indF = self.find(data,'}]')

            #print "indS: ",indS," indF: ",indF
            self.parseS = False
        if indF < indS:
            indF = -1;
        #logging.info("indS: %s indF: %s" % (str(indS),str(indF)))
        #logging.info("parseS: %s parseP: %s" % (str(self.parseS),str(self.parseP)))
        if indS != -1 and indF != -1:
            if self.parseS:
                if i == start_count:
                    self.data2 = self.data[indF+2:]+data
                else:
                    self.data2 = self.data[indF+2:]
                self.data = self.data[indS:indF+2]
            elif self.parseP:
                self.data = self.data[indS:] + data[:indF+2]
                data = data[indF+2:]
                self.parseP = False
            else:
                self.data = data[indS:indF+2]
                data = data[indF+2:]
            #logging.info('In 1')
            self.comp = True
        elif indF != -1:
            self.data = self.data + data[:indF+2]
            data = data[indF+2:]
            #logging.info('In 2')
            self.comp = True
        elif indS != -1:
            if self.parseP:
                self.data = self.data + data
                self.parseP = False
            else:
                self.data = data[indS:]
        else:
            self.data = self.data + data
            #logging.info('In else')
        if self.comp:
            #print 'Process Msg Full data: ',self.data
            #try:
            processMsg(self)
            '''
            except:
                logging.info('Incomming Data %s' % str(sys.exc_info()[0]))
                logging.info('Data %s' % str(self.data))
                self.errorCount = self.errorCount + 1
                logging.error('Error in Data: '+str(self.errorCount))
                '''
            if self.parseS:
                data = self.data[indF+2:]+data
                self.parseS = False
                #print 'Data in if: ',data
            indS = self.find(data,'{"')
            if indS != -1:
                self.data = data[indS:]
            else:
                self.data = data
            self.comp = False

        if self.data2 != None:
            self.data = self.data2
            self.data2 = None
        i +=1

class EchoClient(protocol.Protocol):
    def connectionMade(self):
        self.parent = self.factory.parent
        self.gque = self.factory.gque
        self.tque = self.factory.tque
        logging.info('Connected')
        self.data = ''
        self.data2 = None
        self.parent.i = 1
        self.errorCount = 0
        self.comp = False
        self.endP = False
        self.parseP = False
        self.parseS = False
        logging.info('Connection Open')
        self.transport.registerProducer(self.transport, streaming=True)

    '''    
    Built in Twisted method overwritten:
    Recieves data parses apart each packet and updates Scan data
    '''
    def dataReceived(self, data):
        incommingData(self,data)
    def connectionLost(self, reason):
        logging.info("Connection Lost")

'''
Handles lost server connections
Will exponentially try to reconnect to the server
Also removes and replaces saved figure with a lost connection identifier
creates new data array for everything except time data

'''
class EchoFactory(protocol.ClientFactory):
    protocol = EchoClient
    def __init__(self,parent):
        self.parent = parent


    def clientConnectionFailed(self, connector, reason):
        logging.debug("Connection failed - goodbye!")
        logging.debug('Closed Connection')
        reactor.stop()
        self.gt.join()
        self.tt.join()
        for pr in self.parent.fan['param']:
            silentRemove(self,"fan_%s.png" % (pr))
            silentRemove(self,"geo_%s.png" % (pr))
        silentRemove(self,'time.png')


    def clientConnectionLost(self, connector, reason):
        logging.debug("Connection lost - goodbye!")
        logging.debug('Closed Connection')
        reactor.stop()
        self.gt.join()
        self.tt.join()
        for pr in self.parent.fan['param']:
            silentRemove(self,"fan_%s.png" % (pr))
            silentRemove(self,"geo_%s.png" % (pr))
        silentRemove(self,'time.png')


#connects server
def serverCon(self):
    t_date = datetime.date.today()
    logging.basicConfig(filename="errlog/err_%s_%s"\
            % (self.rad,t_date.strftime('%Y%m%d')), level=logging.DEBUG, \
            format='%(asctime)s %(message)s')
    f = EchoFactory(self)
    f.parent = self
    f.gque = Queue()
    f.gque.put(self.myScan)
    f.tque = Queue()
    f.gt = geoThread(self,f.gque)
    f.tt = timeThread(self,f.tque)
    f.gt.start()
    f.tt.start()
    reactor.connectTCP(self.hosts[0], int(self.ports[0]), f)
    reactor.run(installSignalHandlers=0)

#disconnects from the server currently never called
def disconnect(self):
    logging.info('Closed Connection')
    parent.i=1
    reactor.stop()


#Clears figure and replaces with text indicating lost connection
def silentRemove(self,filename):
    for fanFig in self.parent.fan['figure']:
        fanFig.clf()
        fanFig.text(0.5,0.5,'Lost Connection',backgroundcolor='r',
                size='x-large',style='oblique',ha='center',va='center')
        fanFig.savefig("%s%s" % (self.parent.filepath[0],filename))

#creates a new data set
def createData(self):
    self.myScan = scanData()
    #only called near midnight contains time plot data
    for i in range(0, int(self.parent.maxbeam[0])):
        myBeam = beamData()
        today = datetime.datetime.utcnow()
        today = today.replace(tzinfo=pytz.utc)	
        myBeam.time= today
        myBeam.bmnum = i
        myBeam.prm.nrang = int(self.parent.nrangs[0])
        if i == 0:
            self.myBeam = myBeam
        self.myScan.append(myBeam)
    self.parent.site.tval = datetime.datetime.utcnow()
    self.parent.llcrnrlon,self.parent.llcrnrlat,self.parent.urcrnrlon,self.parent.urcrnrlat,self.parent.lon_0, \
    self.parent.lat_0, self.parent.fovs,self.parent.dist = utils.plotUtils.geoLoc(self.parent.site,
            int(self.parent.nrangs[0]),self.parent.site.rsep,
            int(self.parent.maxbeam[0]))


