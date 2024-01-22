from datetime import datetime
from celery import shared_task
from celery.utils.log import get_task_logger
from geodb.views import getLatestEarthQuake, getLatestShakemap, getLatestGlofasFlood, RemoveNcFiles
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

# @shared_task
# def getNCGlofasFlood():
#     current_date = datetime.now().date()
#     date = current_date.strftime("%Y-%m-%d")
# 	# date = '2023-11-24'
#     get_nc_file_from_ftp(date)

@shared_task
def UpdateLatestGlofasFlood():

    current_date = datetime.now().date()
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


@shared_task
def RemoveNcFilesFor7Days():
	RemoveNcFiles()