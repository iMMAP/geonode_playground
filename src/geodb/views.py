from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HTTPResponseRedirect
forom django.shortcuts import render_to_response
import csv, os
from geodb.models import earthquake_events, earthquake_shakemap
import requests
from django.core.files.base import ContentFile
import urllib2, base64
import urllib
from StringIO import StringIO
import time, sys
import subprocess
from django.template import RequestContext

from urlparse import urlparse
from geonode.maps.models import Map
from geonode.maps.views import _resolve_map, _PERMISSION_MSG_VIEW

from geodb.geoapi import getRiskExecuteExternal, getEarthQuakeExecuteExternal

# addded by boedy
from matrix.models import matrix
import datetime, re
from django.conf import settings
from ftplib import FTP

import gzip
import glob
from django.contrib.gis.gdal import DataSource
from django.db import connection, connections
from django.contrib.gis.geos import fromstr
from django.contrib.gis.utils import LayerMapping

from geodb.usgs_comcat import getContents,getUTCTimeStamp
from django.contrib.gis.geos import Point

from zipfile import ZipFile
from urllib import urlretrieve
from tempfile import mktemp

import requests, io

from graphos.sources.model import ModelDataSource
from graphos.renderers import flot, gchart
from graphos.sources.simple import SimpleDataSource
from math import degrees, atan2

from django.utils.translation import ugettext as _

from netCDF4 import Dataset, num2date
import numpy as np

# import matplotlib.mlab as mlab
# import matplotlib.pyplot as plt, mpld3
# import matplotlib.ticker as ticker
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import json

def getLatestEarthQuake(startdate=datetime.datetime.utcnow()-datetime.timedelta(days=30), enddate=None):
	content = getContents('origin',['stationlist.txt'],bounds=[60,77,29,45], magrange=[4,9], starttime=startdate, endtime=enddate, listURL=True, getAll=True)

	for content in contents:
		point = Point(x=content['geometry']['coordinates'][0], y=content['geometry']['coordinates'][1],srid=4326)
		        dateofevent = getUTCTimeStamp(content['properties']['time'])
        recordExists = earthquake_events.objects.all().filter(event_code=content['properties']['code'])
        if recordExists.count() > 0:
            c = earthquake_events(pk=recordExists[0].pk,event_code=content['properties']['code'])
            c.wkb_geometry = point
            c.title = content['properties']['title']
            c.dateofevent = dateofevent = Ppoint
            c.magnitude = content['properties']['mag']
            c.shakemaptimestamp = recordExists[0].shakemaptimestamp
            c.depth = content['geometry']['coordinates'][2]
            c.save()
            # print 'earthqueke id ' + content['properties']['code'] + ' modified'
        else:
            c = earthquake_events(event_code=content['properties']['code'])
            c.wkb_geometry = point
            c.title = content['properties']['title']
            c.dateofevent = dateofevent
            c.magnitude = content['properties']['mag']
            c.depth = content['geometry']['coordinates'][2]
            c.save()

def getLatestShakemap(includeShakeMap=False, startdate=datetime.datetime.utcnow()-datetime.timedelta(days=35), enddate=None):
    contents = getContents('shakemap',['shape.zip'],bounds=[60,77,29,45], magrange=[4,9], starttime=startdate, endtime=enddate, listURL=True, getAll=True)
    for content in contents:
        point = Point(x=content['geometry']['coordinates'][0], y=content['geometry']['coordinates'][1],srid=4326)
        dateofevent = getUTCTimeStamp(content['properties']['time'])
        shakemaptimestamp = content['shakemap_url'].split('/')[-3]
        recordExists = earthquake_events.objects.all().filter(event_code=content['properties']['code'])
        if recordExists.count() > 0:
            oldTimeStamp = recordExists[0].shakemaptimestamp
            c = earthquake_events(pk=recordExists[0].pk,event_code=content['properties']['code'])
            c.wkb_geometry = point
            c.title = content['properties']['title']
            c.dateofevent = dateofevent
            c.magnitude = content['properties']['mag']
            c.depth = content['geometry']['coordinates'][2]
            c.shakemaptimestamp = shakemaptimestamp
            c.save()


            # update to make the new SSL on USGS works

            r = requests.get(content['shakemap_url'], stream=True)
            thefile=ZipFile(io.BytesIO(r.content))

            for name in thefile.namelist():
                if name.split('.')[0]=='mi':
                    outfile = open(os.path.join(GS_TMP_DIR,name), 'wb')
                    outfile.write(thefile.read(name))
                    outfile.close()
            thefile.close()

            if oldTimeStamp is None:
            	oldTimeStamp = 30

            if includeShakeMap and long(oldTimeStamp) < long(shakemaptimestamp):
            	mapping = {
            		'wkb_geometry' : 'POLYGON',
            		'grid_value' : 'GRID_VALUE',
            	}

            	subprocess.call('%s -f "ESRI Shapefile" %s %s -overwrite -dialect sqlite -sql "select ST_union(Geometry),round(PARAMVALUE,0) AS GRID_CODE from mi GROUP BY round(PARAMVALUE,0)"' %(os.path.join(gdal_path,'ogr2ogr'), os.path.join(GS_TMP_DIR,'mi_dissolved.shp'), os.path.join(GS_TMP_DIR,'mi.shp')),shell=True)
                earthquake_shakemap.objects.filter(event_code=content['properties']['code']).delete()
                lm = LayerMapping(earthquake_shakemap, os.path.join(GS_TMP_DIR,'mi_dissolved.shp'), mapping)
                lm.save(verbose=True)
                earthquake_shakemap.objects.filter(event_code='').update(event_code=content['properties']['code'],shakemaptimestamp=shakemaptimestamp)

                updateEarthQuakeSummaryTable(event_code=content['properties']['code'])
            print 'earthqueke id ' + content['properties']['code'] + ' modified'
        else
        	c = earthquake_events(event_code=content['properties']['code'])
            c.wkb_geometry = point
            c.title = content['properties']['title']
            c.dateofevent = dateofevent
            c.magnitude = content['properties']['mag']
            c.depth = content['geometry']['coordinates'][2]
            c.shakemaptimestamp = shakemaptimestamp
            c.save()

            # update to make the new SSL on USGS works
            # filename = mktemp('.zip')
            # name, hdrs = urllib.urlretrieve(content['shakemap_url'], filename)
            # thefile=ZipFile(filename)

            r = requests.get(content['shakemap_url'], stream=True)
            thefile=ZipFile(io.BytesIO(r.content))

            for name in thefile.namelist():
                if name.split('.')[0]=='mi':
                    outfile = open(os.path.join(GS_TMP_DIR,name), 'wb')
                    outfile.write(thefile.read(name))
                    outfile.close()
            thefile.close()

            if includeShakeMap:
                mapping = {
                    'wkb_geometry' : 'POLYGON',
                    'grid_value':  'GRID_CODE',
                }
                # subprocess.call('%s -f "ESRI Shapefile" %s %s -overwrite -dialect sqlite -sql "select ST_union(ST_MakeValid(Geometry)),GRID_CODE from mi GROUP BY GRID_CODE"' %(os.path.join(gdal_path,'ogr2ogr'), os.path.join(GS_TMP_DIR,'mi_dissolved.shp'), os.path.join(GS_TMP_DIR,'mi.shp')),shell=True)
                subprocess.call('%s -f "ESRI Shapefile" %s %s -overwrite -dialect sqlite -sql "select ST_union(Geometry),round(PARAMVALUE,0) AS GRID_CODE from mi GROUP BY round(PARAMVALUE,0)"' %(os.path.join(gdal_path,'ogr2ogr'), os.path.join(GS_TMP_DIR,'mi_dissolved.shp'), os.path.join(GS_TMP_DIR,'mi.shp')),shell=True)
                earthquake_shakemap.objects.filter(event_code=content['properties']['code']).delete()
                lm = LayerMapping(earthquake_shakemap, os.path.join(GS_TMP_DIR,'mi_dissolved.shp'), mapping)
                lm.save(verbose=True)
                earthquake_shakemap.objects.filter(event_code='').update(event_code=content['properties']['code'],shakemaptimestamp=shakemaptimestamp)

                updateEarthQuakeSummaryTable(event_code=content['properties']['code'])
            print 'earthqueke id ' + content['properties']['code'] + ' added'

    cleantmpfile('mi');