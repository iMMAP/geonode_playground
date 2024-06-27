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
from shapely import wkb
import rasterstats
import rasterio
from netCDF4 import Dataset
from osgeo import gdal
import numpy as np
import numpy.ma as ma
from ftplib import FTP
from django.conf import settings
import traceback
import logging

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.float_format', lambda x: '%.3f' % x)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.width', 500)


EARTHQUAKE_API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
DB_CREDENTIAL_FILE = "~/geonode_playground/src/hsdc_postgres_db_config.json"
#DB_CREDENTIAL_FILE = 'D:/iMMAP/code/db_config/hsdc_local_db_config.json'
TIMEZONE = "Asia/Kabul"

os.chdir(r'/home/ubuntu/data/GLOFAS/')


def get_db_connection():
    with open(os.path.expanduser(DB_CREDENTIAL_FILE), 'r') as f:
        config = json.load(f)
    db_url = f"postgresql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(db_url)


def get_latest_earthquakes():
    query_parameters = {
        "format": "geojson",
        "starttime": "now-180days",
        "minmagnitude": 4.5,
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
    return sorted(features, key=lambda x: x['properties']['time'], reverse=False)[-5:]


def fetch_earthquake_details(detail_url):
    response = requests.get(detail_url)
    return response.json()


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


def create_table_if_not_exists(con):
    """Create the table 'earthquake_epicenter_all' if it doesn't exist."""
    query = text("""
        CREATE TABLE IF NOT EXISTS earthquake_epicenter_all (
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

    """Create the table 'earthquake_epicenter_latest' if it doesn't exist."""
    epic_query = text("""
        CREATE TABLE IF NOT EXISTS earthquake_epicenter_latest (
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

    query_conn = con.connect()
    query_conn.execute(query)
    query_conn.commit()

    epic_query_conn = con.connect()
    epic_query_conn.execute(epic_query)
    epic_query_conn.commit()


def save_earthquake_data(con, epicenter):
    epicenter.to_postgis("earthquake_epicenter_latest", con, if_exists="replace")
    print('Earthquake Epicenter replaced successfully')
    epicenter.to_postgis("earthquake_epicenter_all", con, if_exists="append")
    print('All earthquake Epicenter saved successfully')


def earthquake_exists(con, time_value):
    query = text(f"SELECT COUNT(*) FROM earthquake_epicenter_all WHERE time = '{time_value}'")
    cursor = con.connect().execute(query)
    return cursor.fetchone()[0] > 0


def getLatestEarthQuake():
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




def getLatestShakemap():

    start_time = 'now-180days'
    min_magnitude = 4.5
    # min_magnitude = 0

    # latitude = 39.1458
    # longitude = 34.1614
    # max_radius_km = 1500

    minlatitude = 29.377065
    maxlatitude = 38.490842
    minlongitude = 60.471977
    maxlongitude = 74.889561

    # minlatitude = -90
    # maxlatitude = 90
    # minlongitude = -179
    # maxlongitude = 179

    # Run query and check response
    bbox_query = f'https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime={start_time}&minmagnitude={min_magnitude}&minlatitude={minlatitude}&maxlatitude={maxlatitude}&minlongitude={minlongitude}&maxlongitude={maxlongitude}'

    response = requests.get(bbox_query)
    
    if response.status_code == 200:
        featureCollection = response.json()

        # Load database configuration from file
        db_credential_file = r'~/geonode_playground/src/hsdc_postgres_db_config.json'
        db_credential = os.path.expanduser(db_credential_file)
        with open(db_credential, 'r') as f:
            config = json.load(f)
        db_url = f"postgresql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        con = create_engine(db_url)
        
        features = featureCollection['features']
        # Sort the features based on the 'time' property
        features_sorted = sorted(features, key=lambda x: x['properties']['time'], reverse=False)
        # Get the most recent feature
        feature_newest = features_sorted[-5:]

        for feature in feature_newest:
            # Open the details url in the feature (contains properties, epicenter and shakemap)
            detail_url = feature['properties']['detail']
            url = requests.get(detail_url)

            # Save to new variable
            feature_newest_detail = url.json()
            # Extracting epicenter coordinates
            coordinates = feature_newest_detail['geometry']
            # Extract the epicenter attributes
            attributes = feature_newest_detail['properties']
            
            ### Convert time

            # Convert UNIX timestamp to normal time
            attributes['time'] = pd.to_datetime(attributes['time'], unit='ms')
            # Convert to Kabul time
            timezone = 'Asia/Kabul'
            attributes['time'] = attributes['time'].tz_localize('UTC').tz_convert(timezone)
            # Set time-zone column
            attributes['tz'] = timezone
            # Reformat time
            attributes['time'] = attributes['time'].strftime('%Y-%m-%d %H:%M:%S')
            
            metadata = MetaData()
            metadata.reflect(bind=con)
            table = metadata.tables.get('earthquake_shakemap_all')

            if table is not None:    
            # Check the feature record =========================================================================

                feature_time_values = attributes['time']
                query = text(f"SELECT COUNT(*) FROM earthquake_shakemap_all WHERE time = '{feature_time_values}'")
                with con.connect() as conn:
                    cursor = conn.execute(query)
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        print('The earthquake shakemap already exist')
                    else:
                        # Load buildings from database
                        # buildings = gpd.GeoDataFrame.from_postgis('SELECT * from afg_buildings_microsoft_centroids', con, geom_col='geom').to_crs('EPSG:32642')
                        query = text('SELECT * FROM afg_buildings_microsoft_centroids')
                        result = conn.execute(query)
                        rows = result.fetchall()
                        geometries = [wkb.loads(row[0], hex=True) for row in rows]
                        buildings = gpd.GeoDataFrame(geometry=geometries, columns=result.keys(), crs='EPSG:4326')
                        buildings = buildings.to_crs('EPSG:32642')

                        # Create a pandas DataFrame
                        data = pd.DataFrame(attributes, index=[0])
                        data['geometry'] = Point(coordinates['coordinates'])

                        # Convert to a GeoDataFrame
                        epicenter = gpd.GeoDataFrame(data)
                        epicenter.rename(columns = {'geom':'buildings'}, inplace = True)
                        #  First define the true original crs
                        epicenter.crs = "EPSG:4326"
                        # Reproject to projected crs before calculating shakemap
                        epicenter = epicenter.to_crs('EPSG:32642')  # +proj=cea
                        # Create shakemap as donut rings from epicenter

                        def create_donut_rings(center, radii):
                            # create circles from radii
                            circles = [center.buffer(radius) for radius in radii]
                            
                            # create donut rings by subtracting each inner circle from the outer circle
                            donut_rings = [circles[i].difference(circles[i-1]) for i in range(1, len(circles))]
                            
                            # add the innermost circle
                            donut_rings.insert(0, circles[0])
                            
                            # create a GeoDataFrame with the donut rings and their corresponding radii
                            donut_rings_gdf = gpd.GeoDataFrame(geometry=donut_rings)
                            donut_rings_gdf['distance'] = radii
                            
                            return donut_rings_gdf

                        # specify radii of circles: 10km, 20km, 30km, 40km, 50km
                        radii = [10000, 20000, 30000, 40000, 50000]

                        # create a GeoDataFrame of donut rings
                        donut_rings_gdf = create_donut_rings(epicenter.geometry[0], radii)

                        donut_rings_gdf.crs = "EPSG:32642"  # "+proj=cea"

                        shakemap = donut_rings_gdf

                        # Create list of columns to user for ordering
                        shakemap_columns = list(shakemap.columns)
                        epicenter_columns = list(epicenter.drop(columns='geometry').columns)
                        column_order = epicenter_columns + shakemap_columns

                        # Add a temporary column to both DataFrames with a constant value to create a Cartesian product merge
                        shakemap['_merge_key'] = 1
                        epicenter['_merge_key'] = 1

                        # Perform a merge on the temporary column
                        shakemap = pd.merge(shakemap, epicenter.drop(columns='geometry'), how='outer', on='_merge_key')

                        # Remove the temporary column
                        shakemap = shakemap.drop(columns='_merge_key')

                        #shakemap = shakemap.reindex(columns=column_order)

                        # Get population raster
                        pop = r'~/raster/afg_worldpop_2020_UNadj_unconstrained_projUTM_comp.tif' #_projCEA
                        pop_expanded_path = os.path.expanduser(pop)
                        # Run zonal statistics
                        zonal = rasterstats.zonal_stats(shakemap,pop_expanded_path, stats = 'sum')
                        # Convert to pandas dataframe
                        df = pd.DataFrame(zonal)
                        df = df.rename(columns={'sum': 'pop'})
                        # Drop index column
                        shakemap = shakemap.reset_index(drop=True)
                        # Concatenate pop values and shakemap as a pandas dataframe
                        df_concat = pd.concat([df, shakemap], axis=1)
                        # Turn pandas dataframe back into a geodataframe
                        shakemap = gpd.GeoDataFrame(df_concat, geometry=df_concat.geometry) #wkb_geometry
                        # OBS: change to correct building dataset

                        # Joining the polygon attributes to each point
                        # Creates a point layer of all buildings with the attributes copied from the interesecting polygon uniquely for each point
                        joined_df = gpd.sjoin(
                            buildings,
                            shakemap,
                            how='inner',
                            predicate='intersects')
                            
                        # Count number of buildings within admin polygons (i.e. group by adm code)
                        build_count = joined_df.groupby(
                            ['distance'],
                            as_index=False,
                        )['geom'].count() # column is arbitrary

                        # Change column name to build_count
                        build_count.rename(columns = {'geom': 'buildings'}, inplace = True)
                        # Merge build count back on to shakemap
                        shakemap = shakemap.merge(
                            build_count,
                            on=['distance'],
                            how='left')
                            
                        # Get area from a reprojected version of shakemap
                        #shakemap_repro = shakemap.to_crs('+proj=cea')
                        shakemap['km2'] = shakemap['geometry'].area.div(1000000)
                        columns_shakemap = [
                        'place',
                        'mag',
                        'distance',
                        'pop',
                        'buildings',
                        'km2',
                        'time',
                        'geometry']
                        
                        new_shakemap = shakemap[columns_shakemap]
                        # Reproject from +proj=cea to 4326 before saving
                        new_shakemap = new_shakemap.to_crs('EPSG:4326')

                        # Convert columns to integers and treating NaN values as None
                        new_shakemap['pop'] = new_shakemap['pop'].fillna(0).astype(int)
                        new_shakemap['km2'] = new_shakemap['km2'].fillna(0).astype(int)
                        new_shakemap['buildings'] = new_shakemap['buildings'].fillna(0).astype(int)

                        # Saving shakemap to database
                        new_shakemap.to_postgis('earthquake_shakemap_latest', con, if_exists='replace')
                        print('Earthquake Shakemap replaced successfully')

                        new_shakemap.to_postgis("earthquake_shakemap_all", con, if_exists="append")
                        print('All earthquake Shakemap saved successfully')
            else:
                # Create a pandas DataFrame
                data = pd.DataFrame(attributes, index=[0])
                data['geometry'] = Point(coordinates['coordinates'])

                # Convert to a GeoDataFrame
                epicenter = gpd.GeoDataFrame(data)
                epicenter.rename(columns = {'geom':'buildings'}, inplace = True)
                #  First define the true original crs
                epicenter.crs = "EPSG:4326"
                # Reproject to projected crs before calculating shakemap
                epicenter = epicenter.to_crs('EPSG:32642')
                # Create shakemap as donut rings from epicenter

                def create_donut_rings(center, radii):
                    # create circles from radii
                    circles = [center.buffer(radius) for radius in radii]
            
                    # create donut rings by subtracting each inner circle from the outer circle
                    donut_rings = [circles[i].difference(circles[i-1]) for i in range(1, len(circles))]
            
                    # add the innermost circle
                    donut_rings.insert(0, circles[0])
            
                    # create a GeoDataFrame with the donut rings and their corresponding radii
                    donut_rings_gdf = gpd.GeoDataFrame(geometry=donut_rings)
                    donut_rings_gdf['distance'] = radii
            
                    return donut_rings_gdf
        
                # specify radii of circles: 10km, 20km, 30km, 40km, 50km
                radii = [10000, 20000, 30000, 40000, 50000]

                # create a GeoDataFrame of donut rings
                donut_rings_gdf = create_donut_rings(epicenter.geometry[0], radii)

                donut_rings_gdf.crs = "EPSG:32642"

                shakemap = donut_rings_gdf

                # Create list of columns to user for ordering
                shakemap_columns = list(shakemap.columns)
                epicenter_columns = list(epicenter.drop(columns='geometry').columns)
                column_order = epicenter_columns + shakemap_columns

                # Add a temporary column to both DataFrames with a constant value to create a Cartesian product merge
                shakemap['_merge_key'] = 1
                epicenter['_merge_key'] = 1

                # Perform a merge on the temporary column
                shakemap = pd.merge(shakemap, epicenter.drop(columns='geometry'), how='outer', on='_merge_key')

                # Remove the temporary column
                shakemap = shakemap.drop(columns='_merge_key')
            
                #shakemap = shakemap.reindex(columns=column_order)

                # Get population raster
                pop = r'~/raster/afg_worldpop_2020_UNadj_unconstrained_projUTM_comp.tif' #_projCEA
                pop_expanded_path = os.path.expanduser(pop)
                # Run zonal statistics
                zonal = rasterstats.zonal_stats(shakemap,pop_expanded_path, stats = 'sum')
                # Convert to pandas dataframe
                df = pd.DataFrame(zonal)
                df = df.rename(columns={'sum': 'pop'})
                # Drop index column
                shakemap = shakemap.reset_index(drop=True)
                # Concatenate pop values and shakemap as a pandas dataframe
                df_concat = pd.concat([df, shakemap], axis=1)
                # Turn pandas dataframe back into a geodataframe
                shakemap = gpd.GeoDataFrame(df_concat, geometry=df_concat.geometry) #wkb_geometry
                # OBS: change to correct building dataset

                # Joining the polygon attributes to each point
                # Creates a point layer of all buildings with the attributes copied from the interesecting polygon uniquely for each point
                joined_df = gpd.sjoin(
                    buildings,
                    shakemap,
                    how='inner',
                    predicate='intersects')
        
                # Count number of buildings within admin polygons (i.e. group by adm code)
                build_count = joined_df.groupby(
                    ['distance'],
                    as_index=False,
                )['geom'].count() # column is arbitrary

                # Change column name to build_count
                build_count.rename(columns = {'geom': 'buildings'}, inplace = True)
                # Merge build count back on to shakemap
                shakemap = shakemap.merge(
                    build_count,
                    on=['distance'],
                    how='left')
            
                # Get area from a reprojected version of shakemap
                #shakemap_repro = shakemap.to_crs('+proj=cea')
                shakemap['km2'] = shakemap['geometry'].area.div(1000000)
                columns_shakemap = [
                'place',
                'mag',
                'distance',
                'pop',
                'buildings',
                'km2',
                'time',
                'geometry']
    
                new_shakemap = shakemap[columns_shakemap]
                # Reproject from +proj=cea to 4326 before saving
                new_shakemap = new_shakemap.to_crs('EPSG:4326')

                # Convert columns to integers and treating NaN values as None
                new_shakemap['pop'] = new_shakemap['pop'].fillna(0).astype(int)
                new_shakemap['km2'] = new_shakemap['km2'].fillna(0).astype(int)
                new_shakemap['buildings'] = new_shakemap['buildings'].fillna(0).astype(int)

                new_shakemap.to_postgis('earthquake_shakemap_latest', con, if_exists='replace')
                print('Earthquake Shakemap replaced successfully')

                new_shakemap.to_postgis("earthquake_shakemap_all", con, if_exists="replace")
                print('All earthquake Shakemap replaced successfully')
    else:
        print('Error:', response.status_code)




## GLOFAS processing functions

# Load configurations to connect to database
def load_db_config(config_path):
    with open(config_path, 'r') as f:
        return json.load(f)

# Generate a file path to the .nc file based on date
def generate_file_paths(base_path, date):
    date_arr = date.split('-')
    filenames = [
        f"summary_alerts_1_3_{date_arr[0]}{date_arr[1]}{date_arr[2]}00.nc",
        f"summary_alerts_4_10_{date_arr[0]}{date_arr[1]}{date_arr[2]}00.nc",
        f"summary_alerts_11_30_{date_arr[0]}{date_arr[1]}{date_arr[2]}00.nc"
    ]
    return [os.path.join(base_path, filename) for filename in filenames]

# Download nc files
def download_nc_files(directory_path, date):
    start_time = datetime.datetime.now()
    print(f"download_nc_files start time: {start_time}")
    date_arr = date.split('-')
    filenames = [
        f"summary_alerts_1_3_{date_arr[0]}{date_arr[1]}{date_arr[2]}00.nc",
        f"summary_alerts_4_10_{date_arr[0]}{date_arr[1]}{date_arr[2]}00.nc",
        f"summary_alerts_11_30_{date_arr[0]}{date_arr[1]}{date_arr[2]}00.nc"
    ]
    
    GLOFAS_CREDENTIAL_FILE = r'/home/ubuntu/geonode_playground/src/hsdc_postgres_db_config.json'
    with open(os.path.expanduser(GLOFAS_CREDENTIAL_FILE), 'r') as f:
        config = json.load(f)
            
    # FTP server details
    ftp_server = f"{config['ftp_server']}"
    ftp_username = f"{config['ftp_username']}"
    ftp_password = f"{config['ftp_password']}"
    ftp_folder = f"{config['ftp_folder']}"
    
    for filename in filenames:
        local_path = os.path.join(directory_path, filename)
        if os.path.exists(local_path):
            print(f"The latest Glofas file {filename} already exists.")
        else:
            print(f"Downloading {filename} from FTP server...")
            try:
                server = FTP(ftp_server)
                server.login(ftp_username, ftp_password)
                server.cwd(ftp_folder)
                file_list = server.nlst()
                if filename in file_list:
                    with open(local_path, "wb") as file:
                        server.retrbinary("RETR " + filename, file.write)
                    print(f"File {filename} downloaded successfully.")
                else:
                    print(f"The file {filename} does not exist on the FTP server.")
                server.quit()
            except Exception as e:
                print(f"Failed to download {filename} from FTP server. Error: {e}")
    end_time = datetime.datetime.now()
    print(f"download_nc_files end time: {end_time}")
    print(f"download_nc_files Duration: {end_time - start_time}")

# Save TIF file
def save_tif_file(array, output_path, geotransform, projection, datatype, no_data_value=None):
    start_time = datetime.datetime.now()
    print(f"save_tif_file start time: {start_time}")
    driver = gdal.GetDriverByName("GTiff")
    y_size, x_size = array.shape
    dataset = driver.Create(output_path, x_size, y_size, 1, datatype)
    dataset.SetGeoTransform(geotransform)
    dataset.SetProjection(projection)
    band = dataset.GetRasterBand(1)
    if no_data_value is not None:
        band.SetNoDataValue(float(no_data_value))
    band.WriteArray(array)
    band.FlushCache()
    dataset = None
    end_time = datetime.datetime.now()
    print(f"save_tif_file end time: {end_time}")
    print(f"save_tif_file Duration: {end_time - start_time}")

# Create summary rasters
def create_summary_rasters(date):
    date_arr = date.split('-')
    filenames = [
        f"summary_alerts_1_3_{date_arr[0]}{date_arr[1]}{date_arr[2]}00.nc",
        f"summary_alerts_4_10_{date_arr[0]}{date_arr[1]}{date_arr[2]}00.nc",
        f"summary_alerts_11_30_{date_arr[0]}{date_arr[1]}{date_arr[2]}00.nc"
    ]
    output_paths = [
        f"summary_alerts_1_3_{date_arr[0]}{date_arr[1]}{date_arr[2]}00.tif",
        f"summary_alerts_4_10_{date_arr[0]}{date_arr[1]}{date_arr[2]}00.tif",
        f"summary_alerts_11_30_{date_arr[0]}{date_arr[1]}{date_arr[2]}00.tif"
    ]
    variables = [
        'max_prob_summary_1-3',
        'max_prob_summary_4-10',
        'max_prob_summary_11-30'
    ]
    # New geotransform for the specified extent
    pixel_size = 0.05  # Pixel size from the original raster
    origin_x, origin_y = 55.0, 44.0
    gt = (origin_x, pixel_size, 0.0, origin_y, 0.0, -pixel_size)
    proj = "EPSG:4326"
    no_data_value = -1

    for filename, output_path, variable in zip(filenames, output_paths, variables):
        if os.path.exists(filename):
            nc = Dataset(filename, 'r')
            flood = nc.variables[variable][:]
            # Extract the relevant portion of the array
            x_start = int((55.0 - (-180.0)) / 0.05)
            x_end = x_start + 500
            y_start = int((90.0 - 44.0) / 0.05)
            y_end = y_start + 340
            flood_cut = flood[y_start:y_end, x_start:x_end]
            flood_int = flood_cut.astype(np.int32)  # Convert array to int32
            save_tif_file(flood_int, output_path, gt, proj, gdal.GDT_Int32, no_data_value)
        else:
            print(f"File {filename} does not exist.")

# Update glofas points
def update_glofas_points(conn, flood_summary_paths, column_names, glofas_points):
    start_time = datetime.datetime.now()
    print(f"update_glofas_points start time: {start_time}")

    for flood_summary_path, column_name in zip(flood_summary_paths, column_names):
        with rasterio.open(flood_summary_path) as src:
            raster_array = src.read(1)
            transform = src.transform

            updates = []
            for index, row in glofas_points.iterrows():
                row_x, row_y = row.geom.x, row.geom.y
                row_col, row_row = ~transform * (row_x, row_y)
                row_col, row_row = int(row_col), int(row_row)
                raster_value = raster_array[row_row, row_col]
                updates.append(f"({raster_value}, {row['id_glofas']})")

            values_clause = ', '.join(updates)
            update_query = f"UPDATE glofas_points_v06 SET {column_name} = data.raster_value FROM (VALUES {values_clause}) AS data (raster_value, id_glofas) WHERE glofas_points_v06.id_glofas = data.id_glofas"
            conn.execute(text(update_query))

    end_time = datetime.datetime.now()
    print(f"update_glofas_points end time: {end_time}")
    print(f"update_glofas_points Duration: {end_time - start_time}")

# Execute SQL queries

def execute_sql_queries(conn):
    update_glofas_points_query = text("""
    UPDATE glofas_points_v06
    SET alert_1_3 = CASE
                      WHEN glofas_val_1_3 BETWEEN 11 AND 16 THEN 1
                      ELSE 0
                    END,
        alert_4_10 = CASE
                      WHEN glofas_val_4_10 BETWEEN 11 AND 16 THEN 1
                      ELSE 0
                    END,
        alert_11_30 = CASE
                      WHEN glofas_val_11_30 BETWEEN 11 AND 16 THEN 1
                      ELSE 0
                    END
    """)
# Interpretation of glofas_val:
# 2 year return level:
# 8 = 30% risk
# 9 = 50% risk
# 10 = 75% risk

# 5 year return level:
# 11 = 30% risk
# 12 = 50% risk
# 13 = 75% risk

# 20 year return level:
# 14 = 30% risk
# 15 = 50% risk
# 16 = 75% risk

    update_glofas_join = text("""
        UPDATE glofas_join b
        SET alert_1_3 = sub.alert_1_3,
            alert_4_10 = sub.alert_4_10,
            alert_11_30 = sub.alert_11_30
        FROM (
            SELECT id_basin,
                MAX(alert_1_3) AS alert_1_3,
                MAX(alert_4_10) AS alert_4_10,
                MAX(alert_11_30) AS alert_11_30
            FROM glofas_points_v06
            GROUP BY id_basin
        ) sub
        WHERE b.basin_id = sub.id_basin;
    """)

    update_adm2_query = text("""
    UPDATE afg_adm2_summary a
    SET pop_1_3 = sub.pop_1_3,
        pop_4_10 = sub.pop_4_10,
        pop_11_30 = sub.pop_11_30,
        build_1_3 = sub.build_1_3,
        build_4_10 = sub.build_4_10,
        build_11_3 = sub.build_11_30,
        km2_1_3 = sub.km2_1_3,
        km2_4_10 = sub.km2_4_10,
        km2_11_30 = sub.km2_11_30
    FROM (
        SELECT adm2_pcode,
            SUM(CASE WHEN alert_1_3 = 1 THEN pop ELSE 0 END) as pop_1_3,
            SUM(CASE WHEN alert_4_10 = 1 THEN pop ELSE 0 END) as pop_4_10,
            SUM(CASE WHEN alert_11_30 = 1 THEN pop ELSE 0 END) as pop_11_30,
            SUM(CASE WHEN alert_1_3 = 1 THEN bld ELSE 0 END) as build_1_3,
            SUM(CASE WHEN alert_4_10 = 1 THEN bld ELSE 0 END) as build_4_10,
            SUM(CASE WHEN alert_11_30 = 1 THEN bld ELSE 0 END) as build_11_30,
            SUM(CASE WHEN alert_1_3 = 1 THEN km2 ELSE 0 END) as km2_1_3,
            SUM(CASE WHEN alert_4_10 = 1 THEN km2 ELSE 0 END) as km2_4_10,
            SUM(CASE WHEN alert_11_30 = 1 THEN km2 ELSE 0 END) as km2_11_30
        FROM glofas_join
        GROUP BY adm2_pcode
    ) sub
    WHERE a.adm2_pcode = sub.adm2_pcode;
    """)

    update_basin_query = text("""
    UPDATE afg_basin_summary b
    SET pop_1_3 = sub.pop_1_3,
        pop_4_10 = sub.pop_4_10,
        pop_11_30 = sub.pop_11_30,
        build_1_3 = sub.build_1_3,
        build_4_10 = sub.build_4_10,
        build_11_3 = sub.build_11_30,
        km2_1_3 = sub.km2_1_3,
        km2_4_10 = sub.km2_4_10,
        km2_11_30 = sub.km2_11_30
    FROM (
        SELECT basin_id,
            SUM(CASE WHEN alert_1_3 = 1 THEN pop ELSE 0 END) as pop_1_3,
            SUM(CASE WHEN alert_4_10 = 1 THEN pop ELSE 0 END) as pop_4_10,
            SUM(CASE WHEN alert_11_30 = 1 THEN pop ELSE 0 END) as pop_11_30,
            SUM(CASE WHEN alert_1_3 = 1 THEN bld ELSE 0 END) as build_1_3,
            SUM(CASE WHEN alert_4_10 = 1 THEN bld ELSE 0 END) as build_4_10,
            SUM(CASE WHEN alert_11_30 = 1 THEN bld ELSE 0 END) as build_11_30,
            SUM(CASE WHEN alert_1_3 = 1 THEN km2 ELSE 0 END) as km2_1_3,
            SUM(CASE WHEN alert_4_10 = 1 THEN km2 ELSE 0 END) as km2_4_10,
            SUM(CASE WHEN alert_11_30 = 1 THEN km2 ELSE 0 END) as km2_11_30
        FROM glofas_join
        GROUP BY basin_id
    ) sub
    WHERE b.basin_id = sub.basin_id;
    """)

    try:
        conn.execute(update_glofas_points_query)
        conn.execute(update_glofas_join)
        conn.execute(update_adm2_query)
        conn.execute(update_basin_query)
        print("Glofas_join, Basin, and Adm2 summary tables updated successfully")
    except Exception as e:
        print(f"An error occurred: {e}")


## Main Function

def processGLOFAS(date, db_config_path, flood_summary_paths, column_names, directory_path):
    config = load_db_config(db_config_path)
    db_connection_string = f"postgresql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"

    print('Starting Glofas Flood Processing')

    download_nc_files(directory_path, date)
    create_summary_rasters(date)

    try:
        engine = create_engine(db_connection_string)
        with engine.connect() as conn:
            test_query = conn.execute(text("SELECT 1"))
            test_result = test_query.fetchone()
            if test_result[0] == 1:
                print("Test query successful")
                glofas_points = gpd.read_postgis('SELECT * FROM glofas_points_v06', conn)
                update_glofas_points(conn, flood_summary_paths, column_names, glofas_points)
                execute_sql_queries(conn)

        print("Glofas Flood Processing Completed")

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()

def UpdateLatestGlofasFlood():
    date = datetime.datetime.now().date().strftime('%Y-%m-%d')
    # date = "2024-06-26"
    db_credential_file = r'/home/ubuntu/geonode_playground/src/hsdc_live_db_config.json'
    
#    flood_summary_paths = [
#        r'D:/iMMAP/proj/ASDC/data/GLOFAS/summary_alerts_1_3_2024061100.tif',            # Change to server path
#        r'D:/iMMAP/proj/ASDC/data/GLOFAS/summary_alerts_4_10_2024061100.tif',           # Change to server path
#        r'D:/iMMAP/proj/ASDC/data/GLOFAS/summary_alerts_11_30_2024061100.tif'           # Change to server path
#    ]

    flood_summary_paths = [
         r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmp790rz1b1/summary_alerts_1_3.tif',
         r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpegt2n9wv/summary_alerts_4_10.tif',
         r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpku54neby/summary_alerts_11_30.tif'
     ]

    column_names = ['glofas_val_1_3', 'glofas_val_4_10', 'glofas_val_11_30']
    directory_path = r'/home/ubuntu/data/GLOFAS/'                                 # Change to server path
    processGLOFAS(date, db_credential_file, flood_summary_paths, column_names, directory_path)


def RemoveNcAndTiffFiles():
    directory_path = '/home/ubuntu/data/GLOFAS/'

    # Get a list of all NetCDF files in the directory
    nc_files = [filename for filename in os.listdir(directory_path) if filename.endswith(".nc")]
    tiff_files = [filename for filename in os.listdir(directory_path) if filename.endswith(".tif")]

    # Check if there are files to delete
    if len(nc_files) == 0 and len(tiff_files) == 0:
        print("No NetCDF or TIFF files found in the specified directory. Nothing to delete.")
    else:
        nc_files.sort(key=lambda x: os.path.getmtime(os.path.join(directory_path, x)))
        tiff_files.sort(key=lambda x: os.path.getmtime(os.path.join(directory_path, x)))
        
        files_to_keep = 21
        nc_files_to_remove = nc_files[:-files_to_keep]
        tiff_files_to_remove = tiff_files[:-files_to_keep]

        # Check if there are nc files to delete
        if len(nc_files_to_remove) == 0:
            print("No NetCDF files to delete. Keeping the latest 7 NetCDF files...")
        else:
            # Remove the extra nc files
            for filename in nc_files_to_remove:
                file_path = os.path.join(directory_path, filename)
                os.remove(file_path)
                print(f"Removed NetCDF file: {file_path}")

            print("NetCDF file removal process completed.")

        # Check if there are tiff files to delete
        if len(tiff_files_to_remove) == 0:
            print("No TIFF files to delete. Keeping the latest 7 TIFF files...")
        else:
            for filename in tiff_files_to_remove:
                file_path = os.path.join(directory_path, filename)
                os.remove(file_path)
                print(f"Removed TIFF file: {file_path}")

            print("TIFF file removal process completed.")


    
try:
    print("==================================================================================================")
    print("RUNNING EPICENTER SCRIPT")
    print("==================================================================================================")
    getLatestEarthQuake()
    print("==================================================================================================")
    print("EPICENTER SCRIPT DONE")
    print("==================================================================================================")
except Exception as e:
    logging.error(f"Error in getLatestEarthQuake: {str(e)}")
    
    
try:
    print("==================================================================================================")
    print("RUNNING SHAKEMAP SCRIPT")
    print("==================================================================================================")
    getLatestShakemap()
    print("==================================================================================================")
    print("SHAKEMAP SCRIPT DONE")
    print("==================================================================================================")
except Exception as e:
    logging.error(f"Error in getLatestShakemap: {str(e)}")


try:
    print("==================================================================================================")
    print("RUNNING GLOFAS SCRIPT")
    print("==================================================================================================")
    UpdateLatestGlofasFlood()
    print("------------------------------------------------------------------------")
    print("REMOVE NC FILE")
    print("------------------------------------------------------------------------")
    RemoveNcAndTiffFiles()
    print("------------------------------------------------------------------------")
    print("NC FILE DELETED")
    print("------------------------------------------------------------------------")
    print("==================================================================================================")
    print("GLOFAS SCRIPT DONE")
    print("==================================================================================================")
except Exception as e:
    logging.error(f"Error in UpdateLatestGlofasFlood: {str(e)}")
