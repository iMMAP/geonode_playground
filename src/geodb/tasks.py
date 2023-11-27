from datetime import datetime
from celery import shared_task
from celery.utils.log import get_task_logger
from geodb.views import getLatestEarthQuake, getLatestShakemap, get_nc_file_from_ftp, getLatestGlofasFlood
# from geodb.EarthquakeHistoricalAnalysis import getEarthquakeHistoricalAnalysis

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
    current_date = datetime.now().date()
    date = current_date.strftime("%Y-%m-%d")
    getLatestGlofasFlood(date)