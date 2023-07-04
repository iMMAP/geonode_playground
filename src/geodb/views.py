import requests
import datetime, re
import requests, io
import pandas as pd
import json
from sqlalchemy import create_engine
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.float_format', lambda x: '%.3f' % x)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.width', 500)


def getLatestEarthQuake(startdate=datetime.datetime.utcnow()-datetime.timedelta(days=30), enddate=None):

    start_time = 'now-180days'
    min_magnitude = 5

    latitude = 39.1458
    longitude = 34.1614
    max_radius_km = 1500

    minlatitude = 29.377065
    maxlatitude = 38.490842
    minlongitude = 60.471977
    maxlongitude = 74.889561

    bbox_query = f'https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime={start_time}&minmagnitude={min_magnitude}&minlatitude={minlatitude}&maxlatitude={maxlatitude}&minlongitude={minlongitude}&maxlongitude={maxlongitude}&producttype=shakemap'

    response = requests.get(bbox_query)
    
    if response.status_code == 200:
        dataJson = response.json()

        features = dataJson['features']
        geojson_list = features
        geojson_string = json.dumps(geojson_list)

        geojson_featureCollection = json.loads(geojson_string)
        geojson_string = json.dumps(geojson_featureCollection)

        data = json.loads(geojson_string)

        sorted_features = sorted(data, key=lambda x: x['properties']['time'], reverse=False)

        most_recent_feature = sorted_features[0]
        attributes = most_recent_feature['properties']
        coordinates = most_recent_feature['geometry']

        data = pd.DataFrame(attributes, index=[0])
        data['geometry'] = Point(coordinates['coordinates'])
        epicenter = gpd.GeoDataFrame(data)

        db_url = f"postgresql://my_geonode:geonode@localhost:5432/my_geonode_data"
        con = create_engine(db_url)
        epicenter.to_postgis("earthquake_epicenter", con, if_exists="replace")

        print('Earthquake Epicenter inserted successfully')

    else:
        print('Error:', response.status_code)

# def getLatestShakemap(includeShakeMap=False, startdate=datetime.datetime.utcnow()-datetime.timedelta(days=35), enddate=None):
#     print("Obedi Obadiah")
