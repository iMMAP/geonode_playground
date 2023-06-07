from django.contrib import admin
from .models import OchaDashboard
from django import forms
from myapp.models import OchaDashboard


class OchaDashboardAdminForm(forms.ModelForm):
    class Meta:
        model = OchaDashboard
        exclude = ('slug',)
        
class OchaDashboardAdmin(admin.ModelAdmin):
    list_display = ('name', 'description','updated','created')
    # prepopulated_fields = {"slug": ("name",)}
    form = OchaDashboardAdminForm

admin.site.register(OchaDashboard,OchaDashboardAdmin)

