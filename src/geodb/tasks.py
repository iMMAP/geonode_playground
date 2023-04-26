
from celery.task.schedules import crontab
from celery.decorators import periodic_task, task
from celery.utils.log import get_task_logger
from datetime import datetime
from geodb.views import getForecastedDisaster, updateSummaryTable, getSnowCover, getLatestEarthQuake, getLatestShakemap, databasevacumm, runGlofasDownloader
from geodb.zonal_stats import downloadtif
from dashboard.views import classmarkerGet

logger = get_task_logger(__name__)

@periodic_task(run_every=(crontab(hour='*')))
def updateLatestEarthQuake():
	getLatestEarthQuake()

@periodic_task(run_every=(crontab(hour='*')))
def updateLatestShakemap():
	getLatestShakemap(True)