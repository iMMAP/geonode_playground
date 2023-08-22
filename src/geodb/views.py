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
import rasterstats

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.float_format', lambda x: '%.3f' % x)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.width', 500)

def getLatestEarthQuake():

    start_time = 'now-180days'
    min_magnitude = 5
    # min_magnitude = 0

    latitude = 39.1458
    longitude = 34.1614
    max_radius_km = 1500

    minlatitude = 29.377065
    maxlatitude = 38.490842
    minlongitude = 60.471977
    maxlongitude = 74.889561

    # minlatitude = -90
    # maxlatitude = 90
    # minlongitude = -179
    # maxlongitude = 179

    bbox_query = f'https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime={start_time}&minmagnitude={min_magnitude}&minlatitude={minlatitude}&maxlatitude={maxlatitude}&minlongitude={minlongitude}&maxlongitude={maxlongitude}'

    response = requests.get(bbox_query)
    
    if response.status_code == 200:
        dataJson = response.json()

        # Load database configuration from file
        db_credential_file = r'~/geonode_playground/src/hsdc_postgres_db_config.json'
        db_credential = os.path.expanduser(db_credential_file)
        with open(db_credential, 'r') as f:
            config = json.load(f)
        db_url = f"postgresql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        con = create_engine(db_url)

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

        # Creating a temp earthquake table (Uncomment this section if haven't that table then comment it after) =========================================================================
        
        metadata = MetaData()
        metadata.reflect(bind=con)
        table = metadata.tables.get('temp_earthquake_epicenter')
        if table is None:
            temp_query = text(f"CREATE TABLE temp_earthquake_epicenter as (SELECT * FROM earthquake_epicenter)")
            temp_conn = con.connect()
            temp_conn.execute(temp_query)
            temp_conn.commit()

        # Check the feature record =========================================================================

        feature_time_values = attributes['time']
        query = text(f"SELECT COUNT(*) FROM temp_earthquake_epicenter WHERE time = '{feature_time_values}'")
        conn = con.connect()
        cursor = conn.execute(query)
        count = cursor.fetchone()[0]

        # =============================================================================================

        if count > 0:
            print('The earthquake feature already exist')
        else:
            data = pd.DataFrame(attributes, index=[0])
            dataAttr = ['title','place','mag','time','type','cdi','mmi','alert','geometry']
            data['geometry'] = Point(coordinates['coordinates'])
            earthquake_epic = data[dataAttr]
            epicenter = gpd.GeoDataFrame(earthquake_epic)
            epicenter = epicenter.set_crs(4326, allow_override=True)

            epicenter.to_postgis("temp_earthquake_epicenter", con, if_exists="append")
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
                        print('The epicenter record already exits')
                        
                    else:
                        epicenter['mag'] = epicenter['mag'].astype(float)
                        epicenter.to_postgis("all_earthquake_epicenter", con, if_exists="append")
                        print('Earthquake Epicenter added successfully')
                else:
                    epicenter.to_postgis("all_earthquake_epicenter", con, if_exists="replace")
                    print('All earthquake Epicenter replaced successfully')
            else:
                epicenter.crs = 'EPSG:4326'
                epicenter.to_postgis("all_earthquake_epicenter", con, if_exists="append")
                print('All earthquake Epicenter saved successfully')
    else:
        print('Error:', response.status_code)


def getLatestShakemap():

    start_time = 'now-180days'
    min_magnitude = 5
    # min_magnitude = 0

    latitude = 39.1458
    longitude = 34.1614
    max_radius_km = 1500

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
        dataJson = response.json()

        # Load database configuration from file
        db_credential_file = r'~/geonode_playground/src/hsdc_postgres_db_config.json'
        db_credential = os.path.expanduser(db_credential_file)
        with open(db_credential, 'r') as f:
            config = json.load(f)
        db_url = f"postgresql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        con = create_engine(db_url)

        # Restructure to get a list of features instead of a feature collection
        features = dataJson['features']
        geojson_list = features
        geojson_string = json.dumps(geojson_list)

        geojson_feature_collection = json.loads(geojson_string)
        geojson_string = json.dumps(geojson_feature_collection)
        data = json.loads(geojson_string)

        # Sort the features based on the 'time' property
        sorted_features = sorted(data, key=lambda x: x['properties']['time'], reverse=False)

        # Get the most recent feature
        most_recent_feature = sorted_features[-1]

        # Extracting epicenter coordinates and attributes
        attributes = most_recent_feature['properties']
        coordinates = most_recent_feature['geometry']

        # Convert time ================================================================================

        # Convert UNIX timestamp to normal time
        attributes['time'] = pd.to_datetime(attributes['time'], unit='ms')
        # Convert to Kabul time
        timezone = 'Asia/Kabul'
        attributes['time'] = attributes['time'].tz_localize('UTC').tz_convert(timezone)
        # Set time-zone column
        attributes['tz'] = timezone
        # Reformat time
        attributes['time'] = attributes['time'].strftime('%Y-%m-%d %H:%M:%S')

        # =============================================================================================

        # Creating a temp earthquake table (Uncomment this section if haven't that table then comment it after) =========================================================================
        
        metadata = MetaData()
        metadata.reflect(bind=con)
        table = metadata.tables.get('temp_earthquake_shakemap')
        if table is None:
            temp_query = text(f"CREATE TABLE temp_earthquake_shakemap as (SELECT * FROM earthquake_shakemap)")
            temp_conn = con.connect()
            temp_conn.execute(temp_query)
            temp_conn.commit()
    
        # Check the feature record =========================================================================

        feature_time_values = attributes['time']
        query = text(f"SELECT COUNT(*) FROM temp_earthquake_shakemap WHERE time = '{feature_time_values}'")
        conn = con.connect()
        cursor = conn.execute(query)
        count = cursor.fetchone()[0]

        # =============================================================================================

        if count > 0:
            print('The earthquake feature already exist')
        else:
            # Create a pandas DataFrame
            data = pd.DataFrame(attributes, index=[0])
            data['geometry'] = Point(coordinates['coordinates'])
            earthquake_epic = data

            # Convert to a GeoDataFrame
            epicenter = gpd.GeoDataFrame(earthquake_epic)
            epicenter.rename(columns = {'geom':'buildings'}, inplace = True)
            epicenter = epicenter.set_crs(4326, allow_override=True)

            # Open the details url in the feature (contains properties, epicenter and shakemap)
            detail_url = most_recent_feature['properties']['detail']
            url = requests.get(detail_url)
            detail_url_open = url.json()

            if 'shakemap' in detail_url_open['properties']['products']:

                # Get the URLs for the ShakeMap files (many different data format available)
                shakemap_files = detail_url_open['properties']['products']['shakemap']

                # Select the shape format and specify the URL of the file to download
                shakemap_shape_url = shakemap_files[0]['contents']['download/shape.zip']['url']
                file_url = shakemap_shape_url

                # Specify the URL of the file to download
                # save_path = r'~/Documents/shp.zip'
                save_path = r'~/Earthquake_shakemap/shp.zip'
                save_expanded_path = os.path.expanduser(save_path)
                urllib.request.urlretrieve(file_url, save_expanded_path)

                zip_ref_path = r'~/Earthquake_shakemap/temp_extracted_files'
                # zip_ref_path = r'~/Documents/temp_extracted_files'
                zip_expanded_path = os.path.expanduser(zip_ref_path)
                with zipfile.ZipFile(save_expanded_path, "r") as zip_ref:
                    zip_ref.extractall(zip_expanded_path)

                # Read the shapefile as a GeoPandas DataFrame
                shakemap = gpd.read_file(zip_expanded_path + '/mi.shp')

                # Remove rows if PARAMVALUE = 1
                shakemap = shakemap[shakemap['PARAMVALUE'] != 1]

                # Apply the Multipolygon and Polygon on Geometry
                shakemap['geometry'] = shakemap['geometry'].apply(lambda geom: MultiPolygon([geom]) if geom.type == 'Polygon' else geom)

                # Create list of columns to user for ordering
                shakemap_columns = list(shakemap.columns)
                epicenter_attributes = list(epicenter.drop(columns='geometry').columns)
                column_order = epicenter_attributes + shakemap_columns

                # Add a temporary column to both DataFrames with a constant value to create a Cartesian product merge
                shakemap['_merge_key'] = 1
                epicenter['_merge_key'] = 1

                # Perform a merge on the temporary column
                shakemap = pd.merge(shakemap, epicenter.drop(columns='geometry'), how='outer', on='_merge_key')

                # Remove the temporary column
                shakemap = shakemap.drop(columns='_merge_key')
                
                # Reorder columns
                shakemap = shakemap.reindex(columns=column_order)

                #setting shakemap crs
                shakemap = shakemap.set_crs(4326, allow_override=True)

                # Merging Shakemap =================================================================================    

                # Define the merge categories
                merge_categories = [(4, 5), (5, 6), (6, 7), (7, 8), (8, 9)] #(1, 2),(2, 3),(3, 4),

                # Create a new column to store the merged categories
                shakemap['MergeCategory'] = None

                # Iterate over the merge categories
                for category in merge_categories:
                    # Extract the minimum and maximum values of the category
                    min_value, max_value = category
                    
                    # Select polygons within the current category
                    category_polygons = shakemap[(shakemap['PARAMVALUE'] >= min_value) & (shakemap['PARAMVALUE'] < max_value)]
                    
                    # Assign the merge category to the selected polygons
                    shakemap.loc[category_polygons.index, 'MergeCategory'] = f'{min_value}-{max_value}'
                    
                # Dissolve the polygons based on the merge category
                shakemap = shakemap.dissolve(by='MergeCategory')

                #======================================================================================================

                # Calculating population count =======================================================================

                # Get population raster
                pop = r'~/raster/afg_worldpop_2020_UNadj_unconstrained_comp.tif' #_projCEA
                pop_expanded_path = os.path.expanduser(pop)

                # Run zonal statistics
                zonal = rasterstats.zonal_stats(shakemap, pop_expanded_path, stats = 'sum')
                # Convert to pandas dataframe
                df = pd.DataFrame(zonal)
                df = df.rename(columns={'sum': 'pop'})
                # Drop index column
                shakemap = shakemap.reset_index(drop=True)
                # Concatenate pop values and shakemap as a pandas dataframe
                df_concat = pd.concat([df, shakemap], axis=1)
                # Turn pandas dataframe back into a geodataframe
                shakemap = gpd.GeoDataFrame(df_concat, geometry=df_concat.geometry) #wkb_geometry

                # ========================================================================================================

                #Calculating building count =============================================================================

                # Load buildings from database
                buildings = gpd.GeoDataFrame.from_postgis('SELECT * from point_sample', con)   #Dev
                # buildings = gpd.GeoDataFrame.from_postgis('SELECT * from afg_buildings_microsoft_centroids', con) #Prod

                # Joining the polygon attributes to each point
                # Creates a point layer of all buildings with the attributes copied from the interesecting polygon uniquely for each point
                joined_df = gpd.sjoin(
                    buildings,
                    shakemap,
                    how='inner',
                    predicate='intersects')

                # Count number of buildings within admin polygons (i.e. group by adm code)
                build_count = joined_df.groupby(
                    ['PARAMVALUE'],
                    as_index=False,
                )['geom'].count() # column is arbitrary

                # Change column name to build_count
                build_count.rename(columns = {'geom': 'buildings'}, inplace = True)

                # Merge build count back on to shakemap
                shakemap = shakemap.merge(
                    build_count, 
                    on=['PARAMVALUE'], 
                    how='left')

                # ==========================================================================================================

                # Calculating Area ========================================================================================

                shakemap['km2'] = shakemap['geometry'].area.div(1000000)

                # Get area from a reprojected version of shakemap
                shakemap_repro = shakemap.to_crs('+proj=cea')
                shakemap['km2'] = shakemap_repro['geometry'].area.div(1000000)

                # ===========================================================================================================

                # Cleaning tables ===========================================================================================

                columns_shakemap = [
                'title',
                'place',
                'mag',
                'time',
                'type',
                'cdi',
                'mmi',
                'alert',
                'PARAMVALUE',
                'pop',
                'buildings',
                'km2',
                'geometry']

                new_shakemap = shakemap[columns_shakemap]
                new_shakemap = new_shakemap.rename(columns={'PARAMVALUE': 'mag_zone'})

                # ============================================================================================================

                # Saving outputs to database ===========================================================================
                
                # Saving in shakemap table
                new_shakemap.to_postgis('earthquake_shakemap', con, if_exists='replace')
                print('Earthquake Shakemap saved successfully')

                # Checkint if all shakemap table exist in the databse
                metadata = MetaData()
                metadata.reflect(bind=con)
                table = metadata.tables.get('all_earthquake_shakemap')
                unique_time_values = new_shakemap['time'].unique()[0]

                if table is not None:
                    if 'time' in table.columns:
                        query = text(f"SELECT COUNT(*) FROM all_earthquake_shakemap WHERE time = '{unique_time_values}'")

                        conn = con.connect()
                        cursor = conn.execute(query)
                        count = cursor.fetchone()[0]

                        if count > 0:
                            print('The shakemap record already exits')
                            
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
            else:
                print("The earthquake doesn't have a shakemap")
    else:
        print('Error:', response.status_code)