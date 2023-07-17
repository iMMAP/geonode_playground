#!/usr/bin/env python

#stdlib imports
import urllib2
import urllib
import urllib3
import json
import os.path
from datetime import datetime,timedelta
import re
from xml.dom import minidom 
import sys
import shutil
from collections import OrderedDict
import calendar

#third-party imports
from neicmap import distance
from libcomcat import fixed
import numpy
import types

DEVSERVER = 'dev-earthquake.cr' #comcat server name
SERVER = 'earthquake' #comcat server name
URLBASE = 'https://[SERVER].usgs.gov/fdsnws/event/1/query?%s'.replace('[SERVER]',SERVER)
COUNTBASE = 'https://[SERVER].usgs.gov/fdsnws/event/1/count?%s'.replace('[SERVER]',SERVER)
CHECKBASE = 'https://[SERVER].usgs.gov/fdsnws/event/1/%s'.replace('[SERVER]',SERVER)
EVENTURL = 'https://[SERVER].usgs.gov/fdsnws/event/1/query?eventid=[EVENTID]&format=geojson'.replace('[SERVER]',SERVER)
ALLPRODURL = 'https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&includesuperseded=true&eventid=[EVENTID]'
#EVENTURL = 'https://[SERVER].cr.usgs.gov/fdsnws/event/1/query?eventid=[EVENTID]&format=geojson'.replace('[SERVER]',SERVER)
TIMEFMT = '%Y-%m-%dT%H:%M:%S'
NAN = float('nan')
KM2DEG = 1.0/111.191
MTYPES = ['usmww','usmwb','usmwc','usmwr','gcmtmwc','cimwr','ncmwr']

WEEKSECS = 86400*7

TIMEWINDOW = 16
DISTWINDOW = 100


    """
    Download product contents for event(s) from ComCat, given a product type and list of content files for that product.

    The possible product types include, but are not limited to:
     - origin
     - focal-mechanism
     - moment-tensor
     - shakemap
     - dyfi
     - losspager

    The possible list of contents is long, suffice it to say that you can figure out the name of the 
    content you want by exploring the "Downloads" tab of an event page.  For example, if you specify 
    "shakemap" in the "Search Downloads" box, you should see a long list of possible downloads.  Mouse \
    over the link for the product(s) of interest and note the file name at the end of the url.  Examples
    for ShakeMap include: "stationlist.txt", "stationlist.xml", "grid.xml".

    @param product: Name of desired product (i.e., shakemap).
    @param contentlist: List of desired contents.
    @keyword outfolder: Local directory where output files should be written (defaults to current working directory).
    @keyword bounds: Sequence of (lonmin,lonmax,latmin,latmax)
    @keyword starttime: Start time for search (defaults to ~30 days ago). YYYY-mm-ddTHH:MM:SS
    @keyword endtime: End time for search (defaults to now). YYYY-mm-ddTHH:MM:SS
    @keyword magrange: Sequence of (minmag,maxmag)
    @keyword catalog: Product catalog to use to constrain the search (centennial,nc, etc.).
    @keyword contributor: Product contributor, or who sent the product to ComCat (us,nc,etc.).
    @keyword eventid: Event id to search for - restricts search to a single event (usb000ifva)
    @keyword eventProperties: Dictionary of event properties to match. {'reviewstatus':'approved'}
    @keyword productProperties: Dictionary of event properties to match. {'alert':'yellow'}
    @keyword radius: Sequence of (lat,lon,maxradius)
    @keyword listURL: Boolean indicating whether URL for each product source should be printed to stdout.
    @keyword since: Limit to events after the specified time (ShakeDateTime). 
    @keyword getAll: Get all versions of a product (only works when eventid keyword is set).
    @return: List of output files.
    @raise Exception: When:
      - Input catalog is invalid.
      - Input contributor is invalid.
      - Eventid was supplied, but not found in ComCat.
    """

def getContents(product,contentlist,outfolder=None,bounds = None,
                starttime = None,endtime = None,magrange = None,
                catalog = None,contributor = None,eventid = None,
                eventProperties=None,productProperties=None,radius=None,
                listURL=False,since=None,getAll=False):

    if catalog is not None and catalog not in checkCatalogs():
        raise Exception,'Unknown catalog %s' % catalog
    if contributor is not None and contributor not in checkContributors():
        raise Exception,'Unknown contributor %s' % contributor

    if outfolder is None:
        outfolder = os.getcwd()

    #make the output folder if it doesn't already exist
    if not os.path.isdir(outfolder):
        os.makedirs(outfolder)
    
    #if someone asks for a specific eventid, then we can shortcut all of this stuff
    #below, and just parse the event json
    if eventid is not None:
        try:
            outfiles = readEventURL(product,contentlist,outfolder,eventid,listURL=listURL,getAll=getAll)
            return outfiles
        except Exception,errobj:
            raise Exception,'Could not retrieve data for eventid "%s" due to "%s"' % (eventid,str(errobj))
    
    #start creating the url parameters
    urlparams = {}
    urlparams['producttype'] = product
    if starttime is not None:
        urlparams['starttime'] = starttime.strftime(TIMEFMT)
        if endtime is None:
            urlparams['endtime'] = ShakeDateTime.utcnow().strftime(TIMEFMT)
    if endtime is not None:
        urlparams['endtime'] = endtime.strftime(TIMEFMT)
        if starttime is None:
            urlparams['starttime'] = ShakeDateTime(1900,1,1,0,0,0).strftime(TIMEFMT)

    #if specified, only get events updated after a particular time
    if since is not None:
        urlparams['updatedafter'] = since.strftime(TIMEFMT)

    if bounds is not None and radius is not None:
        raise Exception,"Choose one of bounds or radius, not both"
        
    #we're using a rectangle search here
    if bounds is not None:
        urlparams['minlongitude'] = bounds[0]
        urlparams['maxlongitude'] = bounds[1]
        urlparams['minlatitude'] = bounds[2]
        urlparams['maxlatitude'] = bounds[3]

        #fix possible issues with 180 meridian crossings
        minwest = urlparams['minlongitude'] > 0 and urlparams['minlongitude'] < 180
        maxeast = urlparams['maxlongitude'] < 0 and urlparams['maxlongitude'] > -180
        if minwest and maxeast:
            urlparams['maxlongitude'] += 360

    if radius is not None:
        urlparams['latitude'] = radius[0]
        urlparams['longitude'] = radius[1]
        urlparams['maxradiuskm'] = radius[2]

    if magrange is not None:
        urlparams['minmagnitude'] = magrange[0]
        urlparams['maxmagnitude'] = magrange[1]
    
    if catalog is not None:
        urlparams['catalog'] = catalog
    if contributor is not None:
        urlparams['contributor'] = contributor

    #search parameters we're not making available to the user (yet)
    urlparams['orderby'] = 'time-asc'
    urlparams['format'] = 'geojson'
    params = urllib.urlencode(urlparams)
    url = URLBASE % params
    #fh = urllib2.urlopen(url)
    fh = getURLHandle(url)
    feed_data = fh.read()
    fh.close()
    fdict = json.loads(feed_data)
    outfiles = []
    earthquakes_features = []
    for feature in fdict['features']:
        if eventProperties is not None:
            skip=False
            for key,value in eventProperties.iteritems():
                if not feature['properties'].has_key(key):
                    skip=True
                    break
                else:
                    fvalue = feature['properties'][key]
                    if fvalue is None:
                        skip=True
                        break
                    if fvalue.lower() != value.lower():
                        skip=True
                        break
            if skip:
                continue
        eid = feature['id']
        lat,lon,depth = feature['geometry']['coordinates']
        mag = feature['properties']['mag']
        efiles = readEventURL(product,contentlist,outfolder,eid,listURL=listURL,productProperties=productProperties)
        # outfiles += efiles
        # outfiles.append(efiles)
        feature['shakemap_url'] = efiles
        earthquakes_features.append(feature)
        

    return earthquakes_features