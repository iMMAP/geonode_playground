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
# from geoalchemy2 import Geometry
import psycopg2
from shapely.geometry import Polygon, MultiPolygon, shape
from osgeo import ogr
from shapely.wkt import loads
import rasterstats

EARTHQUAKE_API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
DB_CREDENTIAL_FILE = "~/geonode_playground/src/hsdc_postgres_db_config.json"
#DB_CREDENTIAL_FILE = 'D:/iMMAP/code/db_config/hsdc_local_db_config.json'
TIMEZONE = "Asia/Kabul"

def get_db_connection():
    with open(os.path.expanduser(DB_CREDENTIAL_FILE), 'r') as f:
        config = json.load(f)
    db_url = f"postgresql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(db_url)

def get_latest_earthquakes():
    query_parameters = {
        "format": "geojson",
        "starttime": "now-30days",
        "minmagnitude": 4,
        "minlatitude": 29.377065,
        "maxlatitude": 38.490842,
        "minlongitude": 60.471977,
        "maxlongitude": 74.889561
    }

    response = requests.get(EARTHQUAKE_API_URL, params=query_parameters)

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return []

    feature_collection = response.json()
    features = feature_collection['features']
    return sorted(features, key=lambda x: x['properties']['time'], reverse=True)[:5]

def fetch_earthquake_details(detail_url):
    response = requests.get(detail_url)
    return response.json()

def earthquake_exists(con, time_value):
    query = text(f"SELECT COUNT(*) FROM all_earthquake_epicenter WHERE time = '{time_value}'")
    cursor = con.connect().execute(query)
    return cursor.fetchone()[0] > 0

def prepare_earthquake_data(attributes, coordinates):
    attributes['time'] = pd.to_datetime(attributes['time'], unit='ms')
    attributes['time'] = attributes['time'].tz_localize('UTC').tz_convert(TIMEZONE)
    attributes['tz'] = TIMEZONE
    attributes['time'] = attributes['time'].strftime('%Y-%m-%d %H:%M:%S')

    # Extract X and Y coordinates and create a 2D point
    x, y, *_ = coordinates['coordinates']
    point_2d = Point(x, y)

    data = pd.DataFrame(attributes, index=[0])
    data_attr = ['title', 'place', 'mag', 'time', 'type', 'cdi', 'mmi', 'alert', 'geometry']
    data['geometry'] = point_2d
    earthquake_epic = data[data_attr]
    epicenter = gpd.GeoDataFrame(earthquake_epic)
    epicenter.set_crs(4326, allow_override=True, inplace=True)
    return epicenter

def save_earthquake_data(con, epicenter):
    epicenter.to_postgis("earthquake_epicenter", con, if_exists="replace")
    print('Earthquake Epicenter replaced successfully')
    epicenter.to_postgis("all_earthquake_epicenter", con, if_exists="append")
    print('All earthquake Epicenter saved successfully')

def create_table_if_not_exists(con):
    """Create the table 'all_earthquake_epicenter' if it doesn't exist."""
    query = text("""
        CREATE TABLE IF NOT EXISTS all_earthquake_epicenter (
            title TEXT,
            place TEXT,
            mag FLOAT,
            time TIMESTAMP,
            type TEXT,
            cdi FLOAT,
            mmi FLOAT,
            alert TEXT,
            geometry GEOMETRY(Point, 4326)
        );
    """)
    con.connect().execute(query)

def process_earthquake_updates():
    con = get_db_connection()
    create_table_if_not_exists(con)

    latest_earthquakes = get_latest_earthquakes()

    for feature in latest_earthquakes:
        details = fetch_earthquake_details(feature['properties']['detail'])
        coordinates = details['geometry']
        attributes = details['properties']
        epicenter = prepare_earthquake_data(attributes, coordinates)
        if not earthquake_exists(con, attributes['time']):
            save_earthquake_data(con, epicenter)
        else:
            print('The earthquake epicenter already exists')

#process_earthquake_updates()

