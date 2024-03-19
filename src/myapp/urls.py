from django.views.generic import TemplateView
from geonode.urls import path, urlpatterns

from . import views

urlpatterns = [
    path('itt_stats',views.itt_stats,name="itt_stats"),
    path('landing/', views.landing_redirect, name='landing'),
    # path('landing',TemplateView.as_view(template_name='myapp/landing.html'),name='landing'),
    path('ocha_dashboards',views.ocha_dashboards,name='ocha_dashboards'),
    path('ocha_dashboards/<str:slug>',views.ocha_dashboard,name='ocha_dashboards.show'),
]
