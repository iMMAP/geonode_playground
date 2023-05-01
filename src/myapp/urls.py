from geonode.urls import urlpatterns,path
from django.views.generic import TemplateView
from . import views



urlpatterns = [
    path('landing',TemplateView.as_view(template_name='landing.html'),name='landing'),
    path('ocha_dashboards',views.ocha_dashboards,name='ocha_dashboards'),
    path('ocha_dashboards/<str:slug>',views.ocha_dashboard,name='ocha_dashboards.show'),
]
