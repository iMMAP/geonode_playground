from django.contrib import admin
from .models import OchaDashboard

# Register your models here.

class OchaDashboardAdmin(admin.ModelAdmin):
    list_display = ('name', 'description','updated','created')

admin.site.register(OchaDashboard,OchaDashboardAdmin)

