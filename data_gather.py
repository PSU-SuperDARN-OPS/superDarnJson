import math,matplotlib,calendar,datetime,pylab,time,sys
import numpy as np
import davitpy.gme
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.ticker import MultipleLocator
import matplotlib.pyplot as plt
import matplotlib.lines as lines
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from davitpy.pydarn.sdio import *
import davitpy.pydarn 
from numpy import ndarray, array, arange, zeros, nan
from davitpy.utils import Re, geoPack

class myBeamData(radBaseData):
	def __init__(self, beamDict=None, myBeam=None, proctype=None):
		#initialize the attr values
		self.slist = None
		self.vel = None
		self.pow = None
		self.wid = None
		self.gsflg = None
		self.qflg = None

	def __repr__(self):
		import datetime as dt
		#myStr = 'Beam record FROM: ' + str(self.time) + '\n'

		for key,var in self.__dict__.iteritems():
			if(isinstance(var, radBaseData) or isinstance(var, radDataPtr) or
			   isinstance(var, type({}))):
				myStr += '%s  = %s \n' % (key, 'object')
			else:
				myStr += '%s  = %s \n' % (key, var)
		return myStr




def getSouthGPS(year,mon,day):
	
	S4 = []
	xlim=None
	xticks=None
	sigmaPhi = []
	date = []
	lat = []
	lon = []
	kp = []
	f10 = []
	tmp =[]
	tmp_sigmaPhi = []
	tmp_lat = []
	tmp_lon = []
	tmp_kp = []
	tmp_f10 = []
	tmp
	tmp_date = []
	tmp_S4 = []
	if int(day) < 10:
		day = ' '+`day`
	if int(mon) < 10:
		mon = ' '+`mon`
	filename = '/home/mrsimon/Desktop/Data/south/%s/iono_%s_%s_%s'%(year,mon,day,year)
	print "Opening %s"%(filename)
	with open(filename, 'rb') as f:
		for line in f:
			tmpRow = line.strip().split("   ")
			i = 1
			row = []
			for trow in tmpRow:
				if trow != '':
					row.append(trow)
			try:
				tmp_date.append(datetime.datetime(int(year),int(mon),int(day),int(row[3]),int(row[4]),int(row[5])))
				tmp_lat.append(float(row[6]))
				tmp_lon.append(float(row[7]))
				tmp_kp.append(float(row[8]))
				tmp_f10.append(float(row[9]))
				tmp_S4.append(abs(float(row[10])))
				tmp_sigmaPhi.append(abs(float(row[11])))
			except:
				print 'Saw some weird data'
	tmp.append(tmp_date)
	tmp.append(tmp_lat)
	tmp.append(tmp_lon)
	tmp.append(tmp_kp)
	tmp.append(tmp_f10)
	tmp.append(tmp_S4)
	tmp.append(tmp_sigmaPhi)
	middate = tmp_date[len(tmp_date)/2]
	idx = np.argsort(tmp[0])
	minSize = min(len(tmp_S4),len(tmp_date),len(tmp_sigmaPhi))
	for i in range(0,minSize):
		if idx[i] < minSize:
			if tmp[0][idx[i]] <= middate+datetime.timedelta(days=1) and \
				tmp[0][idx[i]] >= middate-datetime.timedelta(days=1):
				date.append(tmp[0][idx[i]])
				lat.append(tmp[1][idx[i]])
				lon.append(tmp[2][idx[i]])
				kp.append(tmp[3][idx[i]])
				f10.append(tmp[4][idx[i]])
				S4.append(tmp[5][idx[i]])
				sigmaPhi.append(tmp[6][idx[i]])
	return (date, lat, lon, kp, f10, S4, sigmaPhi)

def getTECData(year,yearNum):
	
	secsInWeek = 604800 
	secsInDay = 86400
	leapSecs = 14
	gpsEpoch = (1980, 1, 6, -1, 0, 0)
	SEC = []
	xlim=None
	xticks=None
	date = []
	av_date = []
	av_SEC = []
	tmp =[]
	tmp_date = []
	tmp_SEC = []
	filename = '/home/mrsimon/Desktop/Data/%s/ionio_%s.txt'%(year,yearNum)
	epochTuple = gpsEpoch + (-1,-1,0)
	t0 = time.mktime(epochTuple) - time.timezone
	
	with open(filename, 'rb') as f:
		for line in f:
			tmpRow = line.strip().split(" ")
			i = 1
			row = []
			for trow in tmpRow:
				if trow != '':
					row.append(trow)
			try:
				tdiff = (int(row[0]) * secsInWeek)+int(row[1])-leapSecs
				t = t0 + tdiff
				(year, month, day, hh, mm, ss, dayOfWeek, julianDay, daylightsaving) = time.gmtime(t) 
				tmp_date.append(datetime.datetime(year,month,day,hh,mm,ss))
				tmp_SEC.append(abs(float(row[4])))
			except:
				print 'Saw some weird data'
	tmp.append(tmp_date)
	tmp.append(tmp_SEC)
	middate = tmp_date[len(tmp_date)/2]
	idx = np.argsort(tmp[0])
	minSize = min(len(tmp_S4),len(tmp_date),len(tmp_sigmaPhi))
	for i in range(0,minSize):
		if idx[i] < minSize:
			if tmp[0][idx[i]] <= middate+datetime.timedelta(days=1) and \
				tmp[0][idx[i]] >= middate-datetime.timedelta(days=1):
				SEC.append(tmp[1][idx[i]])
				date.append(tmp[0][idx[i]])
	av_SEC = SEC
	av_date = date
	return (av_date, av_SEC)

def getGPSData(g_year,yearNum):
        
        secsInWeek = 604800 
        secsInDay = 86400
        leapSecs = 14
        gpsEpoch = (1980, 1, 6, -1, 0, 0)
        S4 = []
        xlim=None
        xticks=None
        sigmaPhi = []
        date = []
        av_date = []
        av_sigmaPhi = []
        av_S4 = []
        tmp =[]
        tmp_sigmaPhi = []
        tmp_date = []
        tmp_S4 = []
        tmp_date_tx = []
        tmp_lat = []
        tmp_lon = []
        tmp_txid_tx =[]
        tmp_txid = []
        tmp_tx = []
        lat = 65.124
        lon = -147.5
        g_lat = []
        g_lon = []
        g_data = {}
        loc_data = {}
        tmp_lat = []
        tmp_long= []
        filename = '/home/mrsimon/Desktop/Data/%s/scint_%s.txt'%(g_year,yearNum)
        tx_filename = '/home/mrsimon/Desktop/Data/%s/tx_%s.txt'%(g_year,yearNum)
        try:
                with open(tx_filename, 'rb') as f:
                        for line in f:
                                tmpRow = line.strip().split(" ")
                                i = 1
                                row = []
                                for trow in tmpRow:
                                         if trow != '':
                                                row.append(trow)
                                t = (datetime.datetime(1980,1,6) - datetime.datetime(1970,1,1)).total_seconds()
                                tsec = t+ (int(row[0]) * secsInWeek)+int(row[1])-leapSecs
                                (year, month, day, hh, mm, ss, dayOfWeek, julianDay, daylightsaving) = time.gmtime(tsec)
                                if year == g_year:
                                        tme =(datetime.datetime(year,month,day,hh,mm,ss)-datetime.datetime(1970,1,1)).total_seconds()
                                        t_date_tx=tme
                                        el =math.radians(float(row[4]))
                                        az = math.radians(float(row[3]))
                                        
                                        phi = (0.0137/(el+0.11))-0.022
                                        if phi > 0.416:
                                                phi = 0.416
                                        elif phi < -0.416:
                                                phi = -0.416
                                        t_lat = lat+math.degrees(phi*math.cos(az))
                                        
                                        top =phi*math.sin(az)
                                        rt_lat = math.radians(t_lat)
                                        bottom = math.cos(rt_lat)
                                        t_lon = lon+math.degrees(top/bottom)
                                        t_txid_tx = int(row[7])
                                        #tmp_lat.append(t_lat)
                                        #tmp_lon.append(t_lon)
                                        loc_data[tme+t_txid_tx]=[tme,t_lat,t_lon]
        except:
                print 'No file'
        try:    
                with open(filename, 'rb') as f:
                        for line in f:
                                tmpRow = line.strip().split(" ")
                                i = 1
                                row = []
                                for trow in tmpRow:
                                        if trow != '':
                                                row.append(trow)
                                try:       
                                        t = (datetime.datetime(1980,1,6) - datetime.datetime(1970,1,1)).total_seconds()
                                        
                                        tsec = t+ (int(row[0]) * secsInWeek)+int(row[1])-leapSecs
                                        (year, month, day, hh, mm, ss, dayOfWeek, julianDay, daylightsaving) = time.gmtime(tsec)
                                        if year == g_year:
                                                tme =(datetime.datetime(year,month,day,hh,mm,ss)-datetime.datetime(1970,1,1)).total_seconds()
                                                t_date= tme
                                                t_S4=abs(float(row[4]))
                                                t_sigmaPhi=abs(float(row[7]))
                                                t_txid=int(row[14])
                                                g_data[tme+t_txid]=[tme,t_S4,t_sigmaPhi]
                                except:
                                        print 'Saw some weird data'
        except:
                print 'No file'
        data_arr = []
        for key in g_data.keys():
                if key in loc_data.keys():
                        (year, month, day, hh, mm, ss, dayOfWeek, julianDay, daylightsaving) = time.gmtime(g_data[key][0]) 
                        myTecTime = datetime.datetime(year,month,day,hh,mm,ss)
                        data_arr.append([myTecTime,g_data[key][1],g_data[key][2],
                        loc_data[key][1],loc_data[key][2]])
        or_data_arr = sorted(data_arr,key=lambda x:(x[0]))
        for i in range(len(or_data_arr)):
			date.append(or_data_arr[i][0])
			S4.append(or_data_arr[i][1])
			sigmaPhi.append(or_data_arr[i][2])
			g_lat.append(or_data_arr[i][3])
			g_lon.append(or_data_arr[i][4])
        return (date, S4, sigmaPhi,g_lat,g_lon)

def getAeData(datemin,datemax,size=100):
	gmeData = gme.ind.ae.readAe(sTime = datemin, eTime=datemax,res =1)
	ae = []
	au = []
	al = []
	ao = []
	aDate = []
	av_ae = []
	av_adate =[]
	datet = datemin
	for x in gmeData:
		ae.append(x.ae)
		au.append(x.au)
		al.append(x.al)
		ao.append(x.ao)
		datet += datetime.timedelta(minutes =1)
		aDate.append(datet)
	if size == 0:
		av_ae = ae
		av_adate = aDate
	else:
		step = int(np.floor(float(len(ae))/size))
		for i in range(0,size):
			if i == size-1:
				av_ae.append(np.mean(ae[((i)*step):len(ae)]))
				av_adate.append(aDate[len(aDate)-1])
			else:
				av_ae.append(np.mean(ae[((i)*step):((i+1)*step)]))
				av_adate.append(aDate[(step/2)+step*i+1])
	return (av_adate,av_ae,au,al)
	


def getMyBeam(sTime,rad,eTime,channel='d',fileType='fitacf',filtered=False,fileName = None):
	bmnum = 0
	myArray = []
	
	print 'We have returned'
	tbands = []
	tbands.append([8000,20000])
	while(bmnum <16):
		myFile = radDataOpen(sTime,rad,eTime,channel=channel,bmnum=bmnum,fileType=fileType,filtered=filtered,fileName=fileName)
		print myFile
		#Finally we can start reading the data file
		myBeam = radDataReadRec(myFile)
		if not myBeam:
			print 'error, no data available for the requested time/radar/filetype combination'
			return None
		#initialize empty lists
		vel,pow,wid,elev,phi0,times,freq,cpid,nave,nsky,nsch,slist,mode,rsep,nrang,frang,gsflg,qsflg = \
			[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]
			
		#read the parameters of interest
		oneBeam = myBeamData()
		while(myBeam != None):
			#if(myBeam.time > eTime): break
			if(myBeam.bmnum == bmnum and (sTime <= myBeam.time)):
				for i in range(0,len(tbands)):
					if myBeam.prm.tfreq >= tbands[i][0] and myBeam.prm.tfreq <= tbands[i][1]:
						times.append(myBeam.time)
						cpid.append(myBeam.cp)
						nave.append(myBeam.prm.nave)
						nsky.append(myBeam.prm.noisesky)
						rsep.append(myBeam.prm.rsep)
						nrang.append(myBeam.prm.nrang)
						frang.append(myBeam.prm.frang)
						nsch.append(myBeam.prm.noisesearch)
						freq.append(myBeam.prm.tfreq/1e3)
						slist.append(myBeam.fit.slist)
						mode.append(myBeam.prm.ifmode)
						vel.append(myBeam.fit.v)
						pow.append(myBeam.fit.p_l)
						wid.append(myBeam.fit.w_l)
						elev.append(myBeam.fit.elv)
						phi0.append(myBeam.fit.phi0)
						gsflg.append(myBeam.fit.gflg)
						qsflg.append(myBeam.fit.qflg)
			myBeam = radDataReadRec(myFile)
		oneBeam.slist = slist
		oneBeam.vel = vel
		oneBeam.pow = pow
		oneBeam.wid = wid
		oneBeam.gsflg = gsflg
		oneBeam.qflg = qsflg
		myArray.append(oneBeam)
		bmnum+=1
	return (times,nrang,rsep,frang, myArray)
	  
def getGeo(rad,times,nrang,rsep,frang,elevation = None):
	altitude=300
	site = davitpy.pydarn.radar.network().getRadarByCode(rad).getSiteByDate(times)
                
		
	# Then assign variables from the site object if necessary
	if site:
		nbeams = site.maxbeam
		ngates = nrang+1
		bmsep = site.bmsep
		recrise = site.recrise
		siteLat = site.geolat
		siteLon = site.geolon
		siteAlt = site.alt
		siteBore = site.boresite
		siteYear = site.tval.year
		
	# Some type checking. Look out for arrays
	# If frang, rsep or recrise are arrays, then they should be of shape (nbeams,)
	# Set a flag if any of frang, rsep or recrise is an array
	isParamArray = False
	if isinstance(frang, ndarray):
		isParamArray = True
		if len(frang) != nbeams: 
			print 'getFov: frang must be of a scalar or ndarray(nbeams). Using first element: {}'.format(frang[0])
			frang = frang[0] * ones(nbeams+1)
		# Array is adjusted to add on extra beam edge by copying the last element
		else: frang = np.append(frang, frang[-1])
	else: frang = array([frang])
	if isinstance(rsep, ndarray):
		isParamArray = True
		if len(rsep) != nbeams: 
			print 'getFov: rsep must be of a scalar or ndarray(nbeams). Using first element: {}'.format(rsep[0])
			rsep = rsep[0] * ones(nbeams+1)
		# Array is adjusted to add on extra beam edge by copying the last element
		else: rsep = np.append(rsep, rsep[-1])
	else: rsep = array([rsep])
	if isinstance(recrise, ndarray):
		isParamArray = True
		if len(recrise) != nbeams: 
			print 'getFov: recrise must be of a scalar or ndarray(nbeams). Using first element: {}'.format(recrise[0])
			recrise = recrise[0] * ones(nbeams+1)
		# Array is adjusted to add on extra beam edge by copying the last element
		else: recrise = np.append(recrise, recrise[-1])
	else: recrise = array([recrise])
	
	# If altitude or elevation are arrays, then they should be of shape (nbeams,ngates)
	if isinstance(altitude, ndarray):
		if altitude.ndim == 1:
			if altitude.size != ngates:
				print 'getFov: altitude must be of a scalar or ndarray(ngates) or ndarray(nbeans,ngates). Using first element: {}'.format(altitude[0])
				altitude = altitude[0] * ones((nbeams+1, ngates+1))
			# Array is adjusted to add on extra beam/gate edge by copying the last element and replicating the whole array as many times as beams
			else: altitude = np.resize( np.append(altitude, altitude[-1]), (nbeams+1,ngates+1) )
		elif altitude.ndim == 2:
			if altitude.shape != (nbeams, ngates):
				print 'getFov: altitude must be of a scalar or ndarray(ngates) or ndarray(nbeans,ngates). Using first element: {}'.format(altitude[0])
				altitude = altitude[0] * ones((nbeams+1, ngates+1))
			# Array is adjusted to add on extra beam/gate edge by copying the last row and column
			else: 
				altitude = np.append(altitude, altitude[-1,:].reshape(1,ngates), axis=0)
				altitude = np.append(altitude, altitude[:,-1].reshape(nbeams,1), axis=1)
		else:
			print 'getFov: altitude must be of a scalar or ndarray(ngates) or ndarray(nbeans,ngates). Using first element: {}'.format(altitude[0])
			altitude = altitude[0] * ones((nbeams+1, ngates+1))
	if isinstance(elevation, ndarray):
		if elevation.ndim == 1:
			if elevation.size != ngates:
				print 'getFov: elevation must be of a scalar or ndarray(ngates) or ndarray(nbeans,ngates). Using first element: {}'.format(elevation[0])
				elevation = elevation[0] * ones((nbeams+1, ngates+1))
			# Array is adjusted to add on extra beam/gate edge by copying the last element and replicating the whole array as many times as beams
			else: elevation = np.resize( np.append(elevation, elevation[-1]), (nbeams+1,ngates+1) )
		elif elevation.ndim == 2:
			if elevation.shape != (nbeams, ngates):
				print 'getFov: elevation must be of a scalar or ndarray(ngates) or ndarray(nbeans,ngates). Using first element: {}'.format(elevation[0])
				elevation = elevation[0] * ones((nbeams+1, ngates+1))
			# Array is adjusted to add on extra beam/gate edge by copying the last row and column
			else: 
				elevation = np.append(elevation, elevation[-1,:].reshape(1,ngates), axis=0)
				elevation = np.append(elevation, elevation[:,-1].reshape(nbeams,1), axis=1)
		else:
			print 'getFov: elevation must be of a scalar or ndarray(ngates) or ndarray(nbeans,ngates). Using first element: {}'.format(elevation[0])
			elevation = elevation[0] * ones((nbeams+1, ngates+1))
	
	# Generate beam/gate arrays
	beams = arange(nbeams+1)
	gates = arange(ngates+1)
	
	# Create output arrays
	slantRangeFull = zeros((nbeams+1, ngates+1), dtype='float')
	latFull = zeros((nbeams+1, ngates+1), dtype='float')
	lonFull = zeros((nbeams+1, ngates+1), dtype='float')
	slantRangeCenter = zeros((nbeams+1, ngates+1), dtype='float')
	latCenter = zeros((nbeams+1, ngates+1), dtype='float')
	lonCenter = zeros((nbeams+1, ngates+1), dtype='float')
	
	# Calculate deviation from boresight for center of beam
	bOffCenter = bmsep * (beams - nbeams/2.0)
	# Calculate deviation from boresight for edge of beam
	bOffEdge = bmsep * (beams - nbeams/2.0 - 0.5)
	
	# Iterates through beams
	for ib in beams:
		# if none of frang, rsep or recrise are arrays, then only execute this for the first loop, otherwise, repeat for every beam
		if (~isParamArray and ib == 0) or isParamArray:
			# Calculate center slant range
			sRangCenter = davitpy.pydarn.radar.slantRange(frang[ib], rsep[ib], recrise[ib], gates, center=True)
			# Calculate edges slant range
			sRangEdge = davitpy.pydarn.radar.slantRange(frang[ib], rsep[ib], recrise[ib], gates, center=False)
		# Save into output arrays
		slantRangeCenter[ib, :-1] = sRangCenter[:-1]
		slantRangeFull[ib,:] = sRangEdge
		
		# Calculate coordinates for Edge and Center of the current beam
		for ig in gates:
			# This is a bit redundant, but I could not think of any other way to deal with the array-or-not-array issue
			if not isinstance(altitude, ndarray) and not isinstance(elevation, ndarray):
				tElev = elevation
				tAlt = altitude
			elif isinstance(altitude, ndarray) and not isinstance(elevation, ndarray):
				tElev = elevation
				tAlt = altitude[ib,ig]
			elif isinstance(elevation, ndarray) and not isinstance(altitude, ndarray):
				tElev = elevation[ib,ig]
				tAlt = altitude
			else:
				tElev = elevation[ib,ig]
				tAlt = altitude[ib,ig]


			if (sRangCenter[ig] != -1) and (sRangEdge[ig] != -1):
			  # Then calculate projections
			  latC, lonC = davitpy.pydarn.radar.calcFieldPnt(siteLat, siteLon, siteAlt*1e-3, 
						siteBore, bOffCenter[ib], sRangCenter[ig],
						elevation=tElev, altitude=tAlt)
			  latE, lonE = davitpy.pydarn.radar.calcFieldPnt(siteLat, siteLon, siteAlt*1e-3, 
						siteBore, bOffEdge[ib], sRangEdge[ig],
						elevation=tElev, altitude=tAlt)
						  
			else:
			  latC, lonC = nan, nan
			  latE, lonE = nan, nan
				
			# Save into output arrays

			latFull[ib, ig] = latE
			lonFull[ib, ig] = lonE
	
	return (latFull,lonFull)

def latRange(origLat, origLon, origAlt, \
            dist=None, el=None, az=None, \
            distLat=None, distLon=None, distAlt=None):
	"""Calculate: 
		- the coordinates and altitude of a distant point given a point of origin, distance, azimuth and elevation, or 
		- the coordinates and distance of a distant point given a point of origin, altitude, azimuth and elevation, or 
		- the distance, azimuth and elevation between a point of origin and a distant point or 
		- the distance, azimuth between a point of origin and a distant point and the altitude of said distant point given 
		a point of origin, distant point and elevation angle.
	Input/output is in geodetic coordinates, distances are in km and angles in degrees.
	
	**Args**:
		* **origLat**: geographic latitude of point of origin [degree]
		* **origLon**: geographic longitude of point of origin [degree]
		* **origAlt**: altitude of point of origin [km]
		* **[dist]**: distance to point [km]
		* **[el]**: azimuth [degree]
		* **[az]**: elevation [degree]
		* **[distLat]**: latitude [degree] of distant point
		* **[distLon]**: longitude [degree] of distant point
		* **[distAlt]**: altitide [km] of distant point
	**Returns**:
		* **dict**: a dictionary containing all the information about origin and distant points and their relative positions
	"""
	from math import sqrt, pi
	from numpy import degrees, radians, cos, sin, tan, arctan, arctan2, sqrt
		
	
	
	# convert pointing azimuth and elevation to geocentric
	(gcLat, gcLon, origRe, gaz, gel) = geoPack.geodToGeocAzEl(origLat, origLon, az, el)
	# convert pointing direction from local spherical to local cartesian
	(pX, pY, pZ) = geoPack.lspToLcar(gaz, gel, dist)
	(nX, nY, nZ) = geoPack.lspToLcar(gaz, gel, (-1)*dist)
	# convert pointing direction from local cartesian to global cartesian
	(dX1, dY1, dZ1) = geoPack.gcarToLcar(pX, pY, pZ, gcLat, gcLon, origRe+origAlt, inverse=True)
	(dX2, dY2, dZ2) = geoPack.gcarToLcar(nX, nY, nZ, gcLat, gcLon, origRe+origAlt, inverse=True)
	# Convert distant point from global cartesian to geocentric
	(gcDistLat1, gcDistLon1, rho1) = geoPack.gspToGcar(dX1, dY1, dZ1, inverse=True)
	(gcDistLat2, gcDistLon2, rho2) = geoPack.gspToGcar(dX2, dY2, dZ2, inverse=True)
	# Convert distant point from geocentric to geodetic
	(distLat1, distLon1, Re1) = geoPack.geodToGeoc(gcDistLat1, gcDistLon1, inverse=True)
	(distLat2, distLon2, Re2) = geoPack.geodToGeoc(gcDistLat2, gcDistLon2, inverse=True)
	
	
	
	
	return (distLat1,distLat2,distLon1,distLon2)

