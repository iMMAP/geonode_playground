
from django.conf.urls import include
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from geonode.urls import include, path, urlpatterns, re_path

from myapp.views import CustomSignupView

urlpatterns += [
    re_path(r'^account/signup/', CustomSignupView.as_view(), name='account_signup'),

    path('/help',
        login_required(TemplateView.as_view(template_name='help.html')),
        name='help'),

    path('', include('myapp.urls')),
]
