from connection import serverCon,disconnect
from pydarn.sdio import beamData, scanData
import matplotlib.pyplot as plot
from radarPos import RadarPos
import sys, datetime, pytz
from utils import plotUtils,mapObj
from pydarn.radar import radFov
sys.path.append('~/davitpy')


'''
Parses the passed in arguments 
sets up each graph's inputs
clears out old graphs on start
and creates initial datasets on start

'''
class parseStart:
	
	def __init__(self,*args,**kwargs):
		parseArgs(self)

					
		
		self.i = 0
		self.rad = self.rad[0]
		self.fan = None
		self.geo = None
		self.status = None
		#fan data
		self.data = {}
		self.data['param'] = ['velocity','power','width']
		self.data['sc'] = [[-1000,1000],[0,30],[0,500]]
		self.data['gsct'] = True
		self.data['drawEdge'] = False
		self.data['gridColor']='k'
		self.data['backgColor'] = 'w'
		self.data['figure'] = 3*[plot.figure(figsize=(11,8.5))]
		self.fan = self.data
	
	
		#time data
		self.data = {}
		self.data['param'] = ['velocity','power','width']
		self.data['sc'] = [[-1000,1000],[0,30],[0,500]]
		self.data['gsct'] = True
		self.data['drawEdge'] = False
		self.data['figure'] = plot.figure(figsize=(12,8))
		self.time = self.data
		
	
		#geo data
		self.data = {}
		self.data['param'] = ['velocity','power','width']
		self.data['sc'] = [[-1000,1000],[0,30],[0,500]]
		self.data['gsct'] = True
		self.data['drawEdge'] = False
		self.data['gridColor']='k'
		self.data['backgColor'] = 'w'
		self.data['waterColor'] = '#cce5ff'
		self.data['continentBorder'] = '0.75'
		self.data['continentColor'] = 'w'
		self.data['merColor'] = '0.75'
		self.data['merGrid'] = True
		self.data['figure'] = 3*[plot.figure(figsize=(12,8))]
		self.geo = self.data
		createData(self)
		loadVerts(self)
		#print len(self.verts),self.verts[0][2][0]
		serverCon(self)
		
'''
Start the whole program
'''
def run():

	parseStart()


#parses input arguments	
def parseArgs(self):
	
	for argL in sys.argv:
		indEq = argL.find('=')
		indEq +=1

		if 'hosts' in argL:
			self.hosts = argL[indEq:].split(',')
		elif 'ports' in argL:
			self.ports = argL[indEq:].split(',')
		elif 'names' in argL:
			self.names = argL[indEq:].split(',')
		elif 'streams' in argL:
			self.streams = argL[indEq:].split(',')
		elif 'channels' in argL:
			self.channels = argL[indEq:].split(',')
		elif 'beams' in argL:
			self.beams = argL[indEq:].split(',')
		elif 'nrangs' in argL:
			self.nrangs = argL[indEq:].split(',')
		elif 'maxbeam' in argL:
			self.maxbeam = argL[indEq:].split(',')
		elif 'deltas' in argL:
			self.deltas = argL[indEq:].split(',')
		elif 'mapname' in argL:
			self.mapname = argL[indEq:].split(',')
		elif 'scale' in argL:
			self.scale = argL[indEq:].split(',')
		elif 'rad' in argL:
			self.rad = argL[indEq:].split(',')
		elif 'filepath' in argL:
			self.filepath = argL[indEq:].split(',')


#creates empty datasets used by all plots
#datasets later updated by incoming data
def createData(self):
	self.myScan = scanData()
	self.myBeamList = scanData()
	for i in range(0, int(self.maxbeam[0])):
		myBeam = beamData()
		today = datetime.datetime.utcnow()
		today = today.replace(tzinfo=pytz.utc)
		myBeam.time= today
		myBeam.bmnum = i
		myBeam.prm.nrang = int(self.nrangs[0])
		if i == 0:
			self.myBeam = myBeam
		self.myScan.append(myBeam)
	self.site = RadarPos(code = self.rad)
	self.site.tval = datetime.datetime.utcnow()
	self.llcrnrlon,self.llcrnrlat,self.urcrnrlon,self.urcrnrlat,self.lon_0,self.lat_0, self.fovs,self.dist = plotUtils.geoLoc(self.site,
		int(self.nrangs[0]),self.site.rsep,
		int(self.maxbeam[0]))
	self.myMap = mapObj(coords='geo', projection='stere', lat_0=self.lat_0, lon_0=self.lon_0,
											 llcrnrlon=self.llcrnrlon, llcrnrlat=self.llcrnrlat, urcrnrlon=self.urcrnrlon,
											 urcrnrlat=self.urcrnrlat,grid =True,
											 lineColor='0.75')

            
            
def loadVerts(self):
	self.verts = []

	fov = radFov.fov(site=self.site,rsep=self.site.rsep,\
        ngates=int(self.nrangs[0])+1,nbeams= int(self.maxbeam[0]),coords='geo') 
	for i in range(0, int(self.maxbeam[0])):
		self.verts.append([])
		for k in range(0,int(self.nrangs[0])):
			x1,y1 = fov.lonFull[i,k],fov.latFull[i,k]
			x2,y2 = fov.lonFull[i,k+1],fov.latFull[i,k+1]
			x3,y3 = fov.lonFull[i+1,k+1],fov.latFull[i+1,k+1]
			x4,y4 = fov.lonFull[i+1,k],fov.latFull[i+1,k]
			#save the polygon vertices
			self.verts[i].append(((x1,y1),(x2,y2),(x3,y3),(x4,y4),(x1,y1)))
	



run()

