from __future__ import unicode_literals
from django.contrib.gis.db import models
from django.db.models import Manager as GeoManager

class earthquake_epicenter(models.Model):
    mag = models.FloatField(blank=True, null=True)
    place = models.CharField(max_length=255, blank=False)
    time = models.FloatField(blank=True, null=False)
    updated = models.FloatField(blank=False, null=False)
    alert = models.CharField(max_length=255, null=True)
    status = models.CharField(max_length=255, null=True)
    type = models.CharField(max_length=50, null=True)
    title = models.CharField(max_length=500, null=True)
    geometry = models.PointField(blank=True, null=True)
    objects = GeoManager()
    class Meta:
        managed = True
        db_table = 'earthquake_epicenter'