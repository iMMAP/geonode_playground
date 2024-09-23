# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2017 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

import ast

# Django settings for the GeoNode project.
import os
import sentry_sdk

try:
    from urllib.parse import urlparse, urlunparse
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen
    from urlparse import urlparse, urlunparse
# Load more settings from a file called local_settings.py if it exists
try:
    from my_geonode.local_settings import *
#    from geonode.local_settings import *
except ImportError:
    from geonode.settings import *

# import glofas flood settings
try:
    from my_geonode.glofas_settings import *
except ImportError:
    pass

from celery.schedules import crontab
#
# General Django development settings
#
PROJECT_NAME = 'my_geonode'

# add trailing slash to site url. geoserver url will be relative to this
if not SITEURL.endswith('/'):
    SITEURL = '{}/'.format(SITEURL)


SITENAME = os.getenv("SITENAME", 'my_geonode', )
APP_ENV = os.getenv("APP_ENV", 'local')

# Defines the directory that contains the settings file as the LOCAL_ROOT
# It is used for relative settings elsewhere.
LOCAL_ROOT = os.path.abspath(os.path.dirname(__file__))

WSGI_APPLICATION = "{}.wsgi.application".format(PROJECT_NAME)

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = os.getenv('LANGUAGE_CODE', "en")

if PROJECT_NAME not in INSTALLED_APPS:
    INSTALLED_APPS += (PROJECT_NAME, 'myapp', 'geodb','rangefilter')

# Location of url mappings
ROOT_URLCONF = os.getenv('ROOT_URLCONF', '{}.urls'.format(PROJECT_NAME))

# Additional directories which hold static files
# - Give priority to local geonode-project ones
STATICFILES_DIRS = [os.path.join(LOCAL_ROOT, "static"), ] + STATICFILES_DIRS

# Location of locale files
LOCALE_PATHS = (
    os.path.join(LOCAL_ROOT, 'locale'),
) + LOCALE_PATHS

TEMPLATES[0]['DIRS'].insert(0, os.path.join(LOCAL_ROOT, "templates"))
loaders = TEMPLATES[0]['OPTIONS'].get('loaders') or [
    'django.template.loaders.filesystem.Loader', 'django.template.loaders.app_directories.Loader']
# loaders.insert(0, 'apptemplates.Loader')
TEMPLATES[0]['OPTIONS']['loaders'] = loaders
TEMPLATES[0].pop('APP_DIRS', None)


TEMPLATES[0]['OPTIONS']['context_processors'] += ('django.contrib.auth.context_processors.auth','my_geonode.context_processors.export_vars')   


LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d '
                      '%(thread)d %(message)s'
        },
        'simple': {
            'format': '%(message)s',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'console': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        }
    },
    "loggers": {
        "django": {
            "handlers": ["console"], "level": "ERROR", },
        "geonode": {
            "handlers": ["console"], "level": "INFO", },
        "geoserver-restconfig.catalog": {
            "handlers": ["console"], "level": "ERROR", },
        "owslib": {
            "handlers": ["console"], "level": "ERROR", },
        "pycsw": {
            "handlers": ["console"], "level": "ERROR", },
        "celery": {
            "handlers": ["console"], "level": "DEBUG", },
        "mapstore2_adapter.plugins.serializers": {
            "handlers": ["console"], "level": "DEBUG", },
        "geonode_logstash.logstash": {
            "handlers": ["console"], "level": "DEBUG", },
    },
}

MIDDLEWARE_CLASSES = [
    'geodb.middleware.multiDomainAccessMiddleware',
]

# Celery App Configuration
CELERY_APP = 'geodb'
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_DEFAULT_EXCHANGE = 'default'
CELERY_TASK_DEFAULT_ROUTING_KEY = 'default'
CELERY_TASK_DEFAULT_EXCHANGE_TYPE = "direct"

# Celery Beat Configuration (optional)
CELERY_BEAT_SCHEDULE = {
    # 'get_latest_shakemap_every_10_minutes': {
    #     'task':'geodb.tasks.updateLatestShakemap',
    #     'schedule': timedelta(minutes=10),
    #     'options': {
    #         'priority': 0
    #     }
    # },

    # 'get_latest_earthquake_every_10_minutes': {
    #     'task':'geodb.tasks.updateLatestEarthQuake',
    #     'schedule': timedelta(minutes=10),
    #     'options': {
    #         'priority': 1
    #     }
    # },
    # # PRODUCTION GLOFAS TASKS
    # 'get_get_nc_glofas_file_every_at_1_am': {
    #     'task':'geodb.tasks.getNCGlofasFlood',
    #     'schedule': crontab(hour=1, minute=0),
    #     'options': {
    #         'priority': 2
    #     }
    # },
    
    # 'get_latest_glofas_flood_every_at_1_am': {
    #     'task':'geodb.tasks.UpdateLatestGlofasFlood',
    #     'schedule': crontab(hour=1, minute=0),
    #     'options': {
    #         'priority': 3
    #     }
    # },

    # DEV GLOFAS TASKS
    # 'get_get_nc_glofas_file_every_at_1_am': {
    #     'task':'geodb.tasks.getNCGlofasFlood',
    #     'schedule': timedelta(minutes=10),
    #     'options': {
    #         'priority': 2
    #     }
    # },
    
    # 'get_latest_glofas_flood_every_10_minutes': {
    #     'task':'geodb.tasks.UpdateLatestGlofasFlood',
    #     'schedule': timedelta(minutes=10),
    #     'options': {
    #         'priority': 2
    #     }
    # },
    
    # 'delete_nc_files_every_10_minutes': {
    #     'task':'geodb.tasks.RemoveNcFilesFor7Days',
    #     'schedule': timedelta(minutes=10),
    #     'options': {
    #         'priority': 3
    #     }
    # },
}

CENTRALIZED_DASHBOARD_ENABLED = ast.literal_eval(
    os.getenv('CENTRALIZED_DASHBOARD_ENABLED', 'False'))
if CENTRALIZED_DASHBOARD_ENABLED and USER_ANALYTICS_ENABLED and 'geonode_logstash' not in INSTALLED_APPS:
    INSTALLED_APPS += ('geonode_logstash',)

    CELERY_BEAT_SCHEDULE['dispatch_metrics'] = {
        'task': 'geonode_logstash.tasks.dispatch_metrics',
        'schedule': 3600.0,
    }

LDAP_ENABLED = ast.literal_eval(os.getenv('LDAP_ENABLED', 'False'))
if LDAP_ENABLED and 'geonode_ldap' not in INSTALLED_APPS:
    INSTALLED_APPS += ('geonode_ldap',)

CACHES = {
     'default': {
         'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
         'LOCATION': '127.0.0.1:11211',
     },
}

# Add your specific LDAP configuration after this comment:
# https://docs.geonode.org/en/master/advanced/contrib/#configuration


ACCOUNT_FORMS = {'signup': 'myapp.forms.SimpleSignupForm'}


AUTH_EXEMPT_URLS += (f'{FORCE_SCRIPT_NAME}/landing',)





# Settings for MONITORING plugin


CORS_ORIGIN_ALLOW_ALL = ast.literal_eval(os.environ.get('CORS_ORIGIN_ALLOW_ALL', 'False'))
GEOIP_PATH = os.getenv('GEOIP_PATH', os.path.join(PROJECT_ROOT, 'GeoIPCities.dat'))
MONITORING_ENABLED = ast.literal_eval(os.environ.get('MONITORING_ENABLED', 'True'))

MONITORING_CONFIG = os.getenv("MONITORING_CONFIG", None)
MONITORING_HOST_NAME = os.getenv("MONITORING_HOST_NAME", 'localhost')
MONITORING_SERVICE_NAME = os.getenv("MONITORING_SERVICE_NAME", 'local-geonode')

# how long monitoring data should be stored
MONITORING_DATA_TTL = timedelta(days=int(os.getenv("MONITORING_DATA_TTL", 7)))

# this will disable csrf check for notification config views,
# use with caution - for dev purpose only
MONITORING_DISABLE_CSRF = ast.literal_eval(os.environ.get('MONITORING_DISABLE_CSRF', 'False'))

if MONITORING_ENABLED:
    if 'geonode.monitoring' not in INSTALLED_APPS:
        INSTALLED_APPS += ('geonode.monitoring',)
    if 'geonode.monitoring.middleware.MonitoringMiddleware' not in MIDDLEWARE_CLASSES:
        MIDDLEWARE_CLASSES += \
            ('geonode.monitoring.middleware.MonitoringMiddleware',)

# skip certain paths to not to mud stats too much
MONITORING_SKIP_PATHS = ('/api/o/',
                         '/monitoring/',
                         '/admin',
                         '/jsi18n',
                         STATIC_URL,
                         MEDIA_URL,
                         re.compile('^/[a-z]{2}/admin/'),
                         )

# configure aggregation of past data to control data resolution
# list of data age, aggregation, in reverse order
# for current data, 1 minute resolution
# for data older than 1 day, 1-hour resolution
# for data older than 2 weeks, 1 day resolution
MONITORING_DATA_AGGREGATION = (
                               (timedelta(seconds=0), timedelta(minutes=1),),
                               (timedelta(days=1), timedelta(minutes=60),),
                               (timedelta(days=14), timedelta(days=1),),
                               )

# privacy settings
USER_ANALYTICS_ENABLED = ast.literal_eval(os.getenv('USER_ANALYTICS_ENABLED', 'False'))

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CELERY_IMPORTS = ('geodb.tasks',)


if APP_ENV == 'production':
    sentry_sdk.init(
        dsn="https://b384eb8fa97dd85396a43cfcf8c7d837@o4506732599640064.ingest.sentry.io/4506732604030976",
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
    )
    
# PROJECT_ROOT
# STATIC_URL="static/"
# STATIC_ROOT="/var/www/html/static_root"
# STATIC_ROOT= LOCAL_ROOT + "/static_root"

# MEDIA_URL="uploaded/"
# MEDIA_ROOT = LOCAL_ROOT + "/uploaded"
# MEDIA_ROOT="/var/www/html/uploaded"
WHITENOISE_MAX_AGE= os.getenv('WHITENOISE_MAX_AGE', "7200")
