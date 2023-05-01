
from geonode.urls import urlpatterns,path,include
from django.conf.urls import include, url
from myapp.views import CustomSignupView
from django.views.generic import TemplateView


urlpatterns += [
    url(r'^account/signup/', CustomSignupView.as_view(), name='account_signup'),
    path('', include('myapp.urls')),
]
