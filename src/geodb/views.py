import requests
import datetime, re
import requests, io
import pandas as pd
import json
from sqlalchemy import create_engine, text, MetaData
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt
import urllib.request
import os
import zipfile
from geoalchemy2 import Geometry
import psycopg2
from shapely.geometry import Polygon, MultiPolygon, shape
from osgeo import ogr
from shapely.wkt import loads

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.float_format', lambda x: '%.3f' % x)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.width', 500)

def getLatestEarthQuake(startdate=datetime.datetime.utcnow()-datetime.timedelta(days=30), enddate=None):

    start_time = 'now-180days'
    # min_magnitude = 5
    min_magnitude = 0

    latitude = 39.1458
    longitude = 34.1614
    max_radius_km = 1500

    # minlatitude = 29.377065
    # maxlatitude = 38.490842
    # minlongitude = 60.471977
    # maxlongitude = 74.889561

    minlatitude = -90
    maxlatitude = 90
    minlongitude = -179
    maxlongitude = 179

    bbox_query = f'https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime={start_time}&minmagnitude={min_magnitude}&minlatitude={minlatitude}&maxlatitude={maxlatitude}&minlongitude={minlongitude}&maxlongitude={maxlongitude}&producttype=shakemap'

    response = requests.get(bbox_query)
    
    if response.status_code == 200:
        dataJson = response.json()

        features = dataJson['features']
        geojson_list = features
        geojson_string = json.dumps(geojson_list)

        geojson_feature_collection = json.loads(geojson_string)
        geojson_string = json.dumps(geojson_feature_collection)

        data = json.loads(geojson_string)

        sorted_features = sorted(data, key=lambda x: x['properties']['time'], reverse=False)

        most_recent_feature = sorted_features[-1]
        attributes = most_recent_feature['properties']
        coordinates = most_recent_feature['geometry']

        data = pd.DataFrame(attributes, index=[0])
        dataAttr = ['mag','place','time','updated','alert','status','type','title','geometry']
        data['geometry'] = Point(coordinates['coordinates'])
        earthquake_epic = data[dataAttr]
        epicenter = gpd.GeoDataFrame(earthquake_epic)


        db_url = f"postgresql://my_geonode:geonode@localhost:5432/my_geonode_data"
        con = create_engine(db_url)
        epicenter.to_postgis("earthquake_epicenter", con, if_exists="replace")
        print('Earthquake Epicenter saved successfully')

        metadata = MetaData()
        metadata.reflect(bind=con)
        table = metadata.tables.get('all_earthquake_epicenter')

        if table is not None:
            if 'time' in table.columns:
                unique_time_values = epicenter['time'].unique()[0]
                query = text(f"SELECT COUNT(*) FROM all_earthquake_epicenter WHERE time = {unique_time_values}")

                conn = con.connect()
                cursor = conn.execute(query)
                count = cursor.fetchone()[0]

                if count > 0:
                    print('The record already exits')
                    
                else:
                    epicenter['mag'] = epicenter['mag'].astype(float)
                    epicenter.crs = 'EPSG:4326'
                    epicenter.to_postgis("all_earthquake_epicenter", con, if_exists="append", index=False, dtype={'geometry': Geometry('POINT', srid=4326)})
                    print('Earthquake Epicenter added successfully')
            else:
                epicenter.to_postgis("all_earthquake_epicenter", con, if_exists="replace")
                print('All earthquake Epicenter replaced successfully')
        else:
            epicenter.crs = 'EPSG:4326'
            epicenter.to_postgis("all_earthquake_epicenter", con, if_exists="append", index=False, dtype={'geometry': Geometry('POINT', srid=4326)})
            print('All earthquake Epicenter saved successfully')

    else:
        print('Error:', response.status_code)



def getLatestShakemap(startdate=datetime.datetime.utcnow()-datetime.timedelta(days=35), enddate=None):

    start_time = 'now-180days'
    # min_magnitude = 5
    min_magnitude = 0

    latitude = 39.1458
    longitude = 34.1614
    max_radius_km = 1500

    # minlatitude = 29.377065
    # maxlatitude = 38.490842
    # minlongitude = 60.471977
    # maxlongitude = 74.889561

    minlatitude = -90
    maxlatitude = 90
    minlongitude = -179
    maxlongitude = 179

    bbox_query = f'https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime={start_time}&minmagnitude={min_magnitude}&minlatitude={minlatitude}&maxlatitude={maxlatitude}&minlongitude={minlongitude}&maxlongitude={maxlongitude}&producttype=shakemap'

    response = requests.get(bbox_query)
    
    if response.status_code == 200:
        dataJson = response.json()

        features = dataJson['features']
        geojson_list = features
        geojson_string = json.dumps(geojson_list)

        geojson_feature_collection = json.loads(geojson_string)
        geojson_string = json.dumps(geojson_feature_collection)

        data = json.loads(geojson_string)

        sorted_features = sorted(data, key=lambda x: x['properties']['time'], reverse=False)

        most_recent_feature = sorted_features[0]
        attributes = most_recent_feature['properties']
        coordinates = most_recent_feature['geometry']

        data = pd.DataFrame(attributes, index=[0])
        # dataAttr = ['mag','place','time','updated','alert','status','type','title','geometry']
        data['geometry'] = Point(coordinates['coordinates'])
        earthquake_epic = data
        epicenter = gpd.GeoDataFrame(earthquake_epic)

        detail_url = most_recent_feature['properties']['detail']
        url = requests.get(detail_url)
        detail_url_open = url.json()
        shakemap_files = detail_url_open['properties']['products']['shakemap']
        shakemap_shape_url = shakemap_files[0]['contents']['download/shape.zip']['url']
        file_url = shakemap_shape_url

        # save_path = r'~/Documents/shp.zip'
        save_path = r'~/Earthquake_shakemap/shp.zip'
        save_expanded_path = os.path.expanduser(save_path)
        urllib.request.urlretrieve(file_url, save_expanded_path)

        zip_ref_path = r'~/Earthquake_shakemap/temp_extracted_files'
        # zip_ref_path = r'~/Documents/temp_extracted_files'
        zip_expanded_path = os.path.expanduser(zip_ref_path)
        with zipfile.ZipFile(save_expanded_path, "r") as zip_ref:
            zip_ref.extractall(zip_expanded_path)

        # shapefile_path = zip_expanded_path + '/mi.shp'
        # shakemap = gpd.read_file(shapefile_path)

        shapefile = ogr.Open(zip_expanded_path + '/mi.shp')
        layer = shapefile.GetLayer()
        data = []
        for feature in layer:
            attributes = feature.items()
            geometry = feature.GetGeometryRef().ExportToWkt()
            
            data.append(attributes | {'geometry':geometry})
            
        df = pd.DataFrame(data)
        shakemap = gpd.GeoDataFrame(df)
        shakemap.geometry =  shakemap['geometry'].apply(loads)
        shakemap.crs = layer.GetSpatialRef().ExportToProj4()


        epicenter_attributes = epicenter.drop(columns='geometry')
        merged_gdf = gpd.GeoDataFrame(shakemap.merge(epicenter_attributes, how='cross'))

        column_order = list(epicenter_attributes.columns) + [col for col in merged_gdf.columns if col not in epicenter_attributes.columns]
        new_shakemap = merged_gdf.reindex(columns=column_order)

        db_url = f"postgresql://my_geonode:geonode@localhost:5432/my_geonode_data"
        con = create_engine(db_url)

        new_shakemap.to_postgis('earthquake_shakemap', con, if_exists='replace')
        print('Earthquake Shakemap saved successfully')

        metadata = MetaData()
        metadata.reflect(bind=con)
        table = metadata.tables.get('all_earthquake_shakemap')
        unique_time_values = new_shakemap['time'].unique()[0]

        if table is not None:
            if 'time' in table.columns:
                query = text(f"SELECT COUNT(*) FROM all_earthquake_shakemap WHERE time = {unique_time_values}")

                conn = con.connect()
                cursor = conn.execute(query)
                count = cursor.fetchone()[0]

                if count > 0:
                    print('The record already exits')
                    
                else:
                    new_shakemap['mag'] = new_shakemap['mag'].astype(float)
                    new_shakemap.to_postgis("all_earthquake_shakemap", con, if_exists="append")
                    print('All Earthquake Shakemap added successfully')
            else:
                new_shakemap.to_postgis("all_earthquake_shakemap", con, if_exists="replace")
                print('All earthquake Shakemap replaced successfully')
        else:
            new_shakemap.to_postgis("all_earthquake_shakemap", con, if_exists="append")
            print('All earthquake Shakemap saved successfully')
            # print('the table does not exist')

    else:
        print('Error:', response.status_code)