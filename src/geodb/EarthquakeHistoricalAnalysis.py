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


def getEarthquakeHistoricalAnalysis():

    start_time = 'now-2years'
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

        
        for feature_newest in features_sorted:
            # Open the details url in the feature (contains properties, epicenter and shakemap)
            detail_url = feature_newest['properties']['detail']
            #get url
            url = requests.get(detail_url)

            # Save to new variable
            feature_newest_detail = url.json()
            # Extracting epicenter coordinates
            coordinates = feature_newest_detail['geometry']
            # Extract the epicenter attributes
            attributes = feature_newest_detail['properties']

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
            table = metadata.tables.get('earthquake_historical_epicenter_all')
            if table is not None:
                feature_time_values = attributes['time']
                query = text(f"SELECT COUNT(*) FROM earthquake_historical_epicenter_all WHERE time = '{feature_time_values}'")
                conn = con.connect()
                cursor = conn.execute(query)
                count = cursor.fetchone()[0]
                
                if count > 0:
                    print('This earthquake already exits')
                            
                else:
                    data = pd.DataFrame(attributes, index=[0])
                    dataAttr = ['title','place','mag','time','type','cdi','mmi','alert','geometry']
                    data['geometry'] = Point(coordinates['coordinates'])
                    earthquake_epic = data[dataAttr]
                    epicenter = gpd.GeoDataFrame(earthquake_epic)
                    epicenter = epicenter.set_crs(4326, allow_override=True)
                           
                    epicenter_time_values = attributes['time']
                    print(feature_time_values)
                    epic_query = text(f"SELECT COUNT(*) FROM earthquake_historical_epicenter_all WHERE time = '{epicenter_time_values}'")
                    epic_conn = con.connect()
                    epic_cursor = epic_conn.execute(epic_query)
                    epic_count = epic_cursor.fetchone()[0]
#
                    if epic_count > 0:
                        print('This epicenter already exits')
                    else:
                        epicenter.to_postgis("earthquake_historical_epicenter_all", con, if_exists="append")
                        print('All earthquake Epicenter added successfully')

                    # ====================================================================================================

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
                    # Load buildings from database
                    buildings = gpd.GeoDataFrame.from_postgis('SELECT * from afg_buildings_microsoft_centroids', con, geom_col='geom').to_crs('EPSG:32642')

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
                    #shakemap_repro = shakemap.to_crs('EPSG:32642')
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
                     # Reproject from EPSG:32642 to 4326 before saving
                    new_shakemap = new_shakemap.to_crs('EPSG:4326')
                    
                    # Saving shakemap to database
        #            new_shakemap.to_postgis('earthquake_shakemap', con, if_exists='replace')
        #            print('Earthquake Shakemap saved successfully')

                    # Checkint if all shakemap table exist in the databse
                    new_shakemap.to_postgis("earthquake_historical_shakemap_all", con, if_exists="append")
                    print('All earthquake Shakemap added successfully')
            else:
                data = pd.DataFrame(attributes, index=[0])
                dataAttr = ['title','place','mag','time','type','cdi','mmi','alert','geometry']
                data['geometry'] = Point(coordinates['coordinates'])
                earthquake_epic = data[dataAttr]
                epicenter = gpd.GeoDataFrame(earthquake_epic)
                epicenter = epicenter.set_crs(4326, allow_override=True)
                
                epicenter.to_postgis("earthquake_historical_epicenter_all", con, if_exists="replace")
                print('All earthquake Epicenter saved successfully')

                # ===============================================================================================================

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
                # Load buildings from database
                buildings = gpd.GeoDataFrame.from_postgis('SELECT * from afg_buildings_microsoft_centroids', con, geom_col='geom').to_crs('EPSG:32642')

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
                #shakemap_repro = shakemap.to_crs('EPSG:32642')
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
                 # Reproject from EPSG:32642 to 4326 before saving
                new_shakemap = new_shakemap.to_crs('EPSG:4326')
    
                # Saving shakemap to database
                new_shakemap.to_postgis("earthquake_historical_shakemap_all", con, if_exists="replace")
                print('All earthquake shakemap saved successfully')
    else:
        print('Error:', response.status_code)


getEarthquakeHistoricalAnalysis()