from __future__ import unicode_literals
from django.contrib.gis.db import models
from django.db.models import Manager as GeoManager

class earthquake_events(models.Model):
    wkb_geometry = models.PointField(blank=True, null=True)
    event_code = models.CharField(max_length=25, blank=False)
    title = models.CharField(max_length=255, blank=False)
    dateofevent = models.DateTimeField(blank=False, null=False)
    magnitude = models.FloatField(blank=True, null=True)
    depth = models.FloatField(blank=True, null=True)
    shakemaptimestamp = models.BigIntegerField(blank=True, null=True)
    objects = GeoManager()
    class Meta:
        managed = True
        db_table = 'earthquake_events'


class earthquake_events(models.Model):
    wkb_geometry = models.PointField(blank=True, null=True)
    event_code = models.CharField(max_length=25, blank=False)
    title = models.CharField(max_length=255, blank=False)
    dateofevent = models.DateTimeField(blank=False, null=False)
    magnitude = models.FloatField(blank=True, null=True)
    depth = models.FloatField(blank=True, null=True)
    shakemaptimestamp = models.BigIntegerField(blank=True, null=True)
    objects = GeoManager()
    class Meta:
        managed = True
        db_table = 'earthquake_events'