from datetime import datetime
from celery import shared_task
from celery.utils.log import get_task_logger
from geodb.views import getLatestEarthQuake, getLatestShakemap, get_nc_file_from_ftp, getLatestGlofasFlood
# from geodb.EarthquakeHistoricalAnalysis import getEarthquakeHistoricalAnalysis
import os
import json

logger = get_task_logger(__name__)

@shared_task
def updateLatestEarthQuake():
	getLatestEarthQuake()

@shared_task
def updateLatestShakemap():
	getLatestShakemap()

# @shared_task
# def getEarthquakeHistorical():
# 	getEarthquakeHistoricalAnalysis()

@shared_task
def getNCGlofasFlood():
    current_date = datetime.now().date()
    date = current_date.strftime("%Y-%m-%d")
	# date = '2023-11-24'
    get_nc_file_from_ftp(date)
    
@shared_task
def UpdateLatestGlofasFlood():
    db_credential_file = r'~/geonode_playground/src/hsdc_postgres_db_config.json'
    db_credential = os.path.expanduser(db_credential_file)
    with open(db_credential, 'r') as f:
        config = json.load(f)
#    db_url = f"postgresql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        
    current_date = datetime.now().date()
    date = current_date.strftime("%Y-%m-%d")
    
    # Usage

    # DEV SERVER =================

    # raster_paths = [
    #     r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpr6onmi52/alert_day1_3.tif',
    #     r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpfpvy4t0u/alert_day4_10.tif',
    #     r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmp5_4vilax/alert_day11_30.tif'
    # ]

    # PRODUCTION SERVER =================
    
    raster_paths = [
        r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmppqszzhtx/alert_day1_3.tif',
        r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpidj7p7ir/alert_day4_10.tif',
        r'/home/ubuntu/.virtualenvs/hsdc/lib/python3.10/site-packages/geonode/uploaded/tmpu9hsaucj/alert_day11_30.tif'
    ]
    column_names = ['alert_1_3', 'alert_4_10', 'alert_11_30']
    db_connection_string = f"postgresql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"

    getLatestGlofasFlood(date, raster_paths, column_names, db_connection_string)