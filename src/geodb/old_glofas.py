
def load_db_config(config_path):
    with open(config_path, 'r') as f:
        return json.load(f)

def generate_file_path(base_path, date):
    date_arr = date.split('-')
    filename = f"glofas_areagrid_for_IMMAP_in_Afghanistan_{date_arr[0]}{date_arr[1]}{date_arr[2]}00.nc"
    return os.path.join(base_path, filename)

def download_nc_file(directory_path, date):
    start_time = datetime.datetime.now()
    print(f"download_nc_file start time: {start_time}")
    date_arr = date.split('-')
    filename = f"glofas_areagrid_for_IMMAP_in_Afghanistan_{date_arr[0]}{date_arr[1]}{date_arr[2]}00.nc"
    local_path = os.path.join(directory_path, filename)

    if os.path.exists(local_path):
        print(f"The latest Glofas file {filename} already exists.")
        return local_path
    else:
        print(f"Downloading {filename} from FTP server...")
        
        # FTP server details
        DB_CREDENTIAL_FILE = r'/home/ubuntu/geonode_playground/src/hsdc_live_db_config.json'
        with open(os.path.expanduser(DB_CREDENTIAL_FILE), 'r') as f:
            config = json.load(f)
            
        # FTP server details
        ftp_server = "{config['ftp_server']}"
        ftp_username = "{config['ftp_username']}"
        ftp_password = "{config['ftp_password']}"
        ftp_folder = "{config['ftp_folder']}"

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
        print(f"download_nc_file end time: {end_time}")
        print(f"download_nc_file Duration: {end_time - start_time}")
    return local_path


# def initialize_paths(directory_path):
#     discharge_tif_paths = [os.path.join(directory_path, f'discharge_day{days}.tif') for days in ['1_3', '4_10', '11_30']]
#     alert_tif_paths = [os.path.join(directory_path, f'alert_day{days}.tif') for days in ['1_3', '4_10', '11_30']]
#     return discharge_tif_paths, alert_tif_paths

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

def create_alert_tif(discharge, return_level, output_path, gt, proj, no_data_value):
    start_time = datetime.datetime.now()
    print(f"create_alert_tif start time: {start_time}")
    # Initialize an array with the no_data_value where the discharge is no data
    alert_array = np.full(discharge.shape, no_data_value, dtype='float32')

    # Apply alert conditions only where discharge data is valid
    valid_data_mask = (discharge != no_data_value)
    alert_conditions = np.where((discharge >= return_level) & valid_data_mask, 1, 0)
    
    # Place the alert conditions into the alert array, preserving no data values
    alert_array[valid_data_mask] = alert_conditions[valid_data_mask]

    # Save the alert array to a .tif file
    save_tif_file(alert_array, output_path, gt, proj, gdal.GDT_Float32, no_data_value)
    end_time = datetime.datetime.now()
    print(f"create_alert_tif end time: {end_time}")
    print(f"create_alert_tif Duration: {end_time - start_time}")

def process_netcdf_data(input_file, time_ranges, discharge_tif_paths, alert_tif_paths, gt, proj, no_data_value):
    start_time = datetime.datetime.now()
    print(f"process_netcdf_data start time: {start_time}")
    with Dataset(input_file, 'r') as nc:
        dis_var = nc.variables['dis']
        rl2 = nc.variables['rl2'][:]
        dis_var_masked = np.ma.masked_values(dis_var[:], no_data_value)
        for (start_day, end_day), discharge_path, alert_path in zip(time_ranges, discharge_tif_paths, alert_tif_paths):
            average_discharge = np.ma.mean(dis_var_masked[:, start_day:end_day, :, :], axis=(0, 1))
            average_discharge.set_fill_value(no_data_value)
            save_tif_file(average_discharge.filled(), discharge_path, gt, proj, gdal.GDT_Float32, no_data_value)
            create_alert_tif(average_discharge.filled(), rl2, alert_path, gt, proj, no_data_value)
    end_time = datetime.datetime.now()
    print(f"process_netcdf_data end time: {end_time}")
    print(f"process_netcdf_data Duration: {end_time - start_time}")

def update_glofas_points(conn, alert_tif_paths, column_names, glofas_points):
    start_time = datetime.datetime.now()
    print(f"update_glofas_points start time: {start_time}")

    for alert_tif_paths, column_name in zip(alert_tif_paths, column_names):
        with rasterio.open(alert_tif_paths) as src:
            raster_array = src.read(1)
            transform = src.transform

            # Prepare batch update
            updates = []
            for index, row in glofas_points.iterrows():
                row_x, row_y = row.geom.x, row.geom.y
                row_col, row_row = ~transform * (row_x, row_y)
                row_col, row_row = int(row_col), int(row_row)
                raster_value = raster_array[row_row, row_col]
                updates.append(f"({raster_value}, {row['id_glofas']})")

            # Perform batch update
            values_clause = ', '.join(updates)
            update_query = f"UPDATE glofas_points SET {column_name} = data.raster_value FROM (VALUES {values_clause}) AS data (raster_value, id_glofas) WHERE glofas_points.id_glofas = data.id_glofas"
            conn.execute(text(update_query))

    end_time = datetime.datetime.now()
    print(f"update_glofas_points end time: {end_time}")
    print(f"update_glofas_points Duration: {end_time - start_time}")


# Update summary glofas join table (adm2-basin-flood polygons), and aggregate to adm2 and basin level 
def execute_sql_queries(conn):
    start_time = datetime.datetime.now()
    print(f"execute_sql_queries start time: {start_time}")
    
    conn.autocommit = True

    # SQL query to update glofas_join
    update_glofas_join = text("""
    UPDATE glofas_join b
    SET alert_1_3 = g.alert_1_3,
        alert_4_10 = g.alert_4_10,
        alert_11_30 = g.alert_11_30
    FROM glofas_points g
    WHERE b.basin_id = g.id_basin;
    """)

    # SQL query to update data for afg_adm2_summary
    update_adm2_query = text("""
    UPDATE afg_adm2_summary a
    SET pop_1_3 = sub.pop_1_3,
        pop_4_10 = sub.pop_4_10,
        pop_11_30 = sub.pop_11_30,
        build_1_3 = sub.build_1_3,
        build_4_10 = sub.build_4_10,
        build_11_3 = sub.build_11_3,
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
            SUM(CASE WHEN alert_11_30 = 1 THEN bld ELSE 0 END) as build_11_3,
            SUM(CASE WHEN alert_1_3 = 1 THEN km2 ELSE 0 END) as km2_1_3,
            SUM(CASE WHEN alert_4_10 = 1 THEN km2 ELSE 0 END) as km2_4_10,
            SUM(CASE WHEN alert_11_30 = 1 THEN km2 ELSE 0 END) as km2_11_30
        FROM glofas_join
        GROUP BY adm2_pcode
    ) sub
    WHERE a.adm2_pcode = sub.adm2_pcode;
    """)

    # SQL query to update data for afg_basin_summary
    update_basin_query = text("""
    UPDATE afg_basin_summary b
    SET pop_1_3 = sub.pop_1_3,
        pop_4_10 = sub.pop_4_10,
        pop_11_30 = sub.pop_11_30,
        build_1_3 = sub.build_1_3,
        build_4_10 = sub.build_4_10,
        build_11_3 = sub.build_11_3,
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
            SUM(CASE WHEN alert_11_30 = 1 THEN bld ELSE 0 END) as build_11_3,
            SUM(CASE WHEN alert_1_3 = 1 THEN km2 ELSE 0 END) as km2_1_3,
            SUM(CASE WHEN alert_4_10 = 1 THEN km2 ELSE 0 END) as km2_4_10,
            SUM(CASE WHEN alert_11_30 = 1 THEN km2 ELSE 0 END) as km2_11_30
        FROM glofas_join
        GROUP BY basin_id
    ) sub
    WHERE b.basin_id = sub.basin_id;
    """)

    try:
        # Execute the update query for afg_basin_summary
        conn.execute(update_glofas_join)
        conn.execute(update_basin_query)
        conn.execute(update_adm2_query)
        conn.commit()

        # Confirmation message
        print("Glofas_join, Basin and Adm2 summary tables updated successfully")

    except SQLAlchemyError as e:
        print(f"An error occurred: {e}")

    end_time = datetime.datetime.now()
    print(f"execute_sql_queries end time: {end_time}")
    print(f"execute_sql_queries Duration: {end_time - start_time}")

# Main Function 
def getLatestGlofasFlood(date, db_config_path, alert_tif_paths, discharge_tif_paths, column_names, directory_path):
    config = load_db_config(db_config_path)
    db_connection_string = f"postgresql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"

    print('Starting Glofas Flood Processing')

    # Download the NetCDF file          # OBS blocking out download function for testing
    input_file = download_nc_file(directory_path, date)
    #input_file = r'D:\iMMAP\proj\ASDC\data\GLOFAS\v02\glofas_areagrid_for_IMMAP_in_Afghanistan_2023122500.nc'
    #input_file = r'D:\iMMAP\proj\ASDC\data\GLOFAS\v02\glofas_areagrid_for_IMMAP_in_Afghanistan_2023110700_FAKE_QA_VERSION.nc'
    #input_file = directory_path + "glofas_areagrid_for_IMMAP_in_Afghanistan_2023110700_FAKE_QA_VERSION.nc"
    #input_file = directory_path + "glofas_areagrid_for_IMMAP_in_Afghanistan_2024010900.nc"

    # Initialize paths for reference TIFF and output TIFFs
    #discharge_tif_paths, alert_tif_paths = initialize_paths(directory_path)
    
    # Read geotransform and projection from reference TIFF
    #gt, proj = read_reference_tif(reference_tif_path)
    gt = (55.0, 0.05, 0.0, 44.0, 0.0, -0.05)
    proj = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]'

    # Define the no data value and time ranges
    no_data_value = -9999  # Define your no data value
    time_ranges = [(0, 3), (3, 10), (10, 30)]

    # Process NetCDF data and generate output TIFFs
    process_netcdf_data(input_file, time_ranges, discharge_tif_paths, alert_tif_paths, gt, proj, no_data_value)

    try:
        # Create database connection and perform updates
        engine = create_engine(db_connection_string)
        with engine.connect() as conn:
            # Perform a simple test query to check connection
            test_query = conn.execute(text("SELECT 1"))
            test_result = test_query.fetchone()
            if test_result[0] == 1:
                print("Test query successful")
                glofas_points = gpd.read_postgis('SELECT * FROM glofas_points', conn)
                update_glofas_points(conn, alert_tif_paths, column_names, glofas_points)
                execute_sql_queries(conn)

        print("Glofas Flood Processing Completed")

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()



def UpdateLatestGlofasFlood():

    current_date = datetime.datetime.now().date()
    date = current_date.strftime("%Y-%m-%d")
    # date = "2024-01-07"

    db_credential_file = r'/home/ubuntu/geonode_playground/src/hsdc_live_db_config.json'


    # DEV SERVER =================

    # alert_tif_paths = [
    #     r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpr6onmi52/alert_day1_3.tif',
    #     r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpfpvy4t0u/alert_day4_10.tif',
    #     r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmp5_4vilax/alert_day11_30.tif',
    # ]

    # discharge_tif_paths = [
    #     r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmp0_59ziks/discharge_day1_3.tif',
    #     r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpt_yo98g6/discharge_day4_10.tif',
    #     r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpinmh2_mr/discharge_day11_30.tif'
    # ]

    # # PRODUCTION SERVER =================
    
    alert_tif_paths = [
        r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmppqszzhtx/alert_day1_3.tif',
        r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpidj7p7ir/alert_day4_10.tif',
        r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpu9hsaucj/alert_day11_30.tif'
    ]
    discharge_tif_paths = [
        r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpmkwaw7sz/discharge_day1_3.tif',
        r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpkri6v1ve/discharge_day4_10.tif',
        r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpeydpsn1v/discharge_day11_30.tif'
    ]

    column_names = ['alert_1_3', 'alert_4_10', 'alert_11_30']
    directory_path =  r'/home/ubuntu/data/GLOFAS/'
    #directory_path =  r'D:/iMMAP/proj/ASDC/data/GLOFAS/v02/'
    getLatestGlofasFlood(date, db_credential_file, alert_tif_paths, discharge_tif_paths, column_names, directory_path)



def RemoveNcFiles():
    # Specify the target directory where the NetCDF files are located
    directory_path = '/home/ubuntu/data/GLOFAS/'

    # Get a list of all NetCDF files in the directory
    nc_files = [filename for filename in os.listdir(directory_path) if filename.endswith(".nc")]
    
    # Check if there are files to delete
    if len(nc_files) == 0:
        print("No NetCDF files found in the specified directory. Nothing to delete.")
    else:
        # Sort the files based on their creation time (modification time)
        nc_files.sort(key=lambda x: os.path.getmtime(os.path.join(directory_path, x)))

        # Calculate the number of files to keep (latest 7 files)
        files_to_keep = 7

        # Determine the files to be removed
        files_to_remove = nc_files[:-files_to_keep]

        # Check if there are files to delete
        if len(files_to_remove) == 0:
            print("No files to delete. Keeping the latest 7 files...")
        else:
            # Remove the extra files
            for filename in files_to_remove:
                file_path = os.path.join(directory_path, filename)
                os.remove(file_path)
                print(f"Removed file: {file_path}")

            print("File removal process completed.")

