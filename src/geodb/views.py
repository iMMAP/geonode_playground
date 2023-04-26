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

