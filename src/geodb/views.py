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
import rasterio
from netCDF4 import Dataset
from osgeo import gdal
import numpy as np
import numpy.ma as ma
from ftplib import FTP
from django.conf import settings

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.float_format', lambda x: '%.3f' % x)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.width', 500)


EARTHQUAKE_API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
DB_CREDENTIAL_FILE = "~/geonode_playground/src/hsdc_postgres_db_config.json"
#DB_CREDENTIAL_FILE = 'D:/iMMAP/code/db_config/hsdc_local_db_config.json'
TIMEZONE = "Asia/Kabul"

os.chdir(r'/home/ubuntu/data/GLOFAS/alerts/')


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

        # Load buildings from database
        buildings = gpd.GeoDataFrame.from_postgis('SELECT * from afg_buildings_microsoft_centroids', con, geom_col='geom').to_crs('EPSG:32642')

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
                conn = con.connect()
                cursor = conn.execute(query)
                count = cursor.fetchone()[0]
                
                if count > 0:
                    print('The earthquake shakemap already exist')
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


def get_nc_file_from_ftp(date):
    date_arr = date.split('-')
    server = FTP()
    try:
        server.connect('aux.ecmwf.int')
        server.login(getattr(settings, 'GLOFAS_FTP_UNAME'), getattr(settings, 'GLOFAS_FTP_UPASS'))
        server.cwd("/for_IMMAP/")
        filename = "glofas_areagrid_for_IMMAP_in_Afghanistan_" + date_arr[0] + date_arr[1] + date_arr[2] + "00.nc"
        local_path = getattr(settings, 'GLOFAS_NC_FILES') + filename
        with open(local_path, "wb") as file:
            print(f"Saving file to: {local_path}")
            server.retrbinary("RETR " + filename, file.write)
        server.quit()
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        server.close()
        return False



def getLatestGlofasFlood(date, raster_paths, column_names, db_connection_string):
    # Open source file
    # Select based on date
    date_arr = date.split('-')
    directory_path = '/home/ubuntu/data/GLOFAS/'
    input_file = directory_path + "glofas_areagrid_for_IMMAP_in_Afghanistan_" + date_arr[0] + date_arr[1] + date_arr[2] + "00.nc"
    input_file_fake = directory_path + "glofas_areagrid_for_IMMAP_in_Afghanistan_2023110700_FAKE_QA_VERSION.nc" # Path to the input NetCDF file with discharge data.

    if os.path.exists(input_file):
        print("The latest Glofas file already exists")
    else:
            
        # DEV SERVER =================

        reference_tif_path = r"/home/ubuntu/data/GLOFAS/reference_tif.tif"  # Path to the GeoTIFF file used for georeferencing.
        # discharge_tif_paths = ['/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmp0_59ziks/discharge_day1_3.tif', '/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpt_yo98g6/discharge_day4_10.tif', '/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpinmh2_mr/discharge_day11_30.tif']  # Output paths for average discharge TIFFs.
        # alert_tif_paths = ['/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpr6onmi52/alert_day1_3.tif', '/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpfpvy4t0u/alert_day4_10.tif', '/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmp5_4vilax/alert_day11_30.tif']  # Output paths for alert TIFFs.
        
        # PRODUCTION SERVER =================

        discharge_tif_paths = ['/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpmkwaw7sz/discharge_day1_3.tif', '/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpkri6v1ve/discharge_day4_10.tif', '/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpeydpsn1v/discharge_day11_30.tif']  # Output paths for average discharge TIFFs.
        alert_tif_paths = ['/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmppqszzhtx/alert_day1_3.tif', '/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpidj7p7ir/alert_day4_10.tif', '/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpu9hsaucj/alert_day11_30.tif']  # Output paths for alert TIFFs.
        
        
        time_ranges = [(0, 3), (3, 10), (10, 30)]  # Time ranges corresponding to the categories.

        # Read geotransform and projection from reference GeoTIFF
        reference_tif = gdal.Open(reference_tif_path)
        gt = reference_tif.GetGeoTransform()  # Geotransform for output TIFFs.
        proj = reference_tif.GetProjection()  # Projection for output TIFFs.
        reference_tif = None  # Close the reference TIFF.

        # Function to save a TIFF file with no data value handling
        def save_tif_file(array, output_path, geotransform, projection, datatype, no_data_value=None):
            driver = gdal.GetDriverByName("GTiff")
            y_size, x_size = array.shape
            dataset = driver.Create(output_path, x_size, y_size, 1, datatype)
            dataset.SetGeoTransform(geotransform)
            dataset.SetProjection(projection)
            band = dataset.GetRasterBand(1)
            if no_data_value is not None:
                # Explicitly cast no_data_value to float
                band.SetNoDataValue(float(no_data_value))
            band.WriteArray(array)
            band.FlushCache()
            dataset = None  # Ensure the dataset is properly closed.
            
            
        # Function to create alert .tif file with no data values
        def create_alert_tif(discharge, return_level, output_path, gt, proj, no_data_value):
            # Initialize an array with the no_data_value where the discharge is no data
            alert_array = np.full(discharge.shape, no_data_value, dtype='float32')

            # Apply alert conditions only where discharge data is valid
            valid_data_mask = (discharge != no_data_value)
            alert_conditions = np.where((discharge >= return_level) & valid_data_mask, 1, 0)
            
            # Place the alert conditions into the alert array, preserving no data values
            alert_array[valid_data_mask] = alert_conditions[valid_data_mask]

            # Save the alert array to a .tif file
            save_tif_file(alert_array, output_path, gt, proj, gdal.GDT_Float32, no_data_value)

        # Process data and save TIFFs (as before)
        with Dataset(input_file_fake, 'r') as nc:
            dis_var = nc.variables['dis']
            rl2 = nc.variables['rl2'][:]
            no_data_value = dis_var.getncattr('_FillValue')
            
            # Convert dis_var to a masked array
            dis_var_masked = ma.masked_values(dis_var[:], no_data_value)
            
            # Calculate average discharge considering the no data values
            for (start_day, end_day), discharge_path, alert_path in zip(time_ranges, discharge_tif_paths, alert_tif_paths):
                average_discharge = ma.mean(dis_var_masked[:, start_day:end_day, :, :], axis=(0, 1))
                average_discharge.set_fill_value(no_data_value)
                
                # Save the average discharge as a TIFF
                save_tif_file(average_discharge.filled(), discharge_path, gt, proj, gdal.GDT_Float32, no_data_value)
                
                # Generate and save the alert TIFF based on rl2 thresholds
                create_alert_tif(average_discharge.filled(), rl2, alert_path, gt, proj, no_data_value)

        # Confirmation message
        print("TIF files have been created and saved.")
        
        # Create a database connection using SQLAlchemy
        engine = create_engine(db_connection_string)
        # Load the point geometry table into a GeoDataFrame
        conn = engine.connect()
        glofas_points = gpd.read_postgis('SELECT * FROM glofas_points_basin', conn)
        
    #    with engine.connect() as conn:
    #        glofas_points = gpd.read_postgis('SELECT * FROM glofas_points_basin', conn)

        # Process each raster file
        for raster_path, column_name in zip(raster_paths, column_names):
            with rasterio.open(raster_path) as src:
                # Read the entire raster as a numpy array
                raster_array = src.read(1)
                transform = src.transform

                    # Iterate over points in the GeoDataFrame
                for index, row in glofas_points.iterrows():
                    # Convert the point geometry to raster spacex
                    row_x, row_y = row.geom.x, row.geom.y

                    # Calculate raster indices manually
                    row_col, row_row = ~transform * (row_x, row_y)
                    row_col, row_row = int(row_col), int(row_row)

                    # Extract the raster value for the point
                    raster_value = raster_array[row_row, row_col]

                    # Update the specified column with the raster value
                    update_query = f"UPDATE glofas_points_basin SET {column_name} = {raster_value} WHERE id_glofas = {row['id_glofas']}"
                    conn.execute(text(update_query))
                        
        try:
            # SQLAlchemy connection string
            conn_string = db_connection_string
            
            # Create an engine instance
            engine = create_engine(conn_string)

            # Connect to PostgreSQL server
            with engine.connect() as conn:

                # SQL query to update basin_flood_adm2_overlay_stats
                update_query = text("""
                UPDATE glofas_join b
                SET alert_1_3 = g.alert_1_3,
                    alert_4_10 = g.alert_4_10,
                    alert_11_30 = g.alert_11_30
                FROM glofas_points_basin g
                WHERE b.basin_id = g.id_basin;
                """)

                # Execute the update query
                conn.execute(update_query)

                # SQL query to update data for adm2_summary
                update_adm2_query = text("""
                UPDATE adm2_summary a
                SET pop_fl_1_3 = sub.pop_fl_1_3,
                    pop_fl_4_1 = sub.pop_fl_4_10,
                    pop_fl_11_ = sub.pop_fl_11_30,
                    build_fl_1 = sub.build_fl_1_3,
                    build_fl_4 = sub.build_fl_4_10,
                    build_fl_2 = sub.build_fl_11_30,
                    km2_fl_1_3 = sub.km2_fl_1_3,
                    km2_fl_4_1 = sub.km2_fl_4_10,
                    km2_fl_11_ = sub.km2_fl_11_30
                FROM (
                    SELECT adm2_pcode,
                        SUM(CASE WHEN alert_1_3 = 1 THEN pop ELSE 0 END) as pop_fl_1_3,
                        SUM(CASE WHEN alert_4_10 = 1 THEN pop ELSE 0 END) as pop_fl_4_10,
                        SUM(CASE WHEN alert_11_30 = 1 THEN pop ELSE 0 END) as pop_fl_11_30,
                        SUM(CASE WHEN alert_1_3 = 1 THEN bld ELSE 0 END) as build_fl_1_3,
                        SUM(CASE WHEN alert_4_10 = 1 THEN bld ELSE 0 END) as build_fl_4_10,
                        SUM(CASE WHEN alert_11_30 = 1 THEN bld ELSE 0 END) as build_fl_11_30,
                        SUM(CASE WHEN alert_1_3 = 1 THEN km2 ELSE 0 END) as km2_fl_1_3,
                        SUM(CASE WHEN alert_4_10 = 1 THEN km2 ELSE 0 END) as km2_fl_4_10,
                        SUM(CASE WHEN alert_11_30 = 1 THEN km2 ELSE 0 END) as km2_fl_11_30
                    FROM glofas_join
                    GROUP BY adm2_pcode
                ) sub
                WHERE a.adm2_pcode = sub.adm2_pcode;
                """)

                # Execute the update query for adm2_summary
                conn.execute(update_adm2_query)

                # SQL query to update data for basin_summary
                update_basin_query = text("""
                UPDATE basin_summary b
                SET pop_fl_1_3 = sub.pop_fl_1_3,
                    pop_fl_4_1 = sub.pop_fl_4_10,
                    pop_fl_11_ = sub.pop_fl_11_30,
                    build_fl_1 = sub.build_fl_1_3,
                    build_fl_4 = sub.build_fl_4_10,
                    build_fl_2 = sub.build_fl_11_30,
                    km2_fl_1_3 = sub.km2_fl_1_3,
                    km2_fl_4_1 = sub.km2_fl_4_10,
                    km2_fl_11_ = sub.km2_fl_11_30
                FROM (
                    SELECT basin_id,
                        SUM(CASE WHEN alert_1_3 = 1 THEN pop ELSE 0 END) as pop_fl_1_3,
                        SUM(CASE WHEN alert_4_10 = 1 THEN pop ELSE 0 END) as pop_fl_4_10,
                        SUM(CASE WHEN alert_11_30 = 1 THEN pop ELSE 0 END) as pop_fl_11_30,
                        SUM(CASE WHEN alert_1_3 = 1 THEN bld ELSE 0 END) as build_fl_1_3,
                        SUM(CASE WHEN alert_4_10 = 1 THEN bld ELSE 0 END) as build_fl_4_10,
                        SUM(CASE WHEN alert_11_30 = 1 THEN bld ELSE 0 END) as build_fl_11_30,
                        SUM(CASE WHEN alert_1_3 = 1 THEN km2 ELSE 0 END) as km2_fl_1_3,
                        SUM(CASE WHEN alert_4_10 = 1 THEN km2 ELSE 0 END) as km2_fl_4_10,
                        SUM(CASE WHEN alert_11_30 = 1 THEN km2 ELSE 0 END) as km2_fl_11_30
                    FROM glofas_join
                    GROUP BY basin_id
                ) sub
                WHERE b.basin_id = sub.basin_id;
                """)

                # Execute the update query for basin_summary
                conn.execute(update_basin_query)

                # Confirmation message
                print("Basin and Adm2 summary tables updated successfully")

        except Exception as e:
            print("Error: ", e)