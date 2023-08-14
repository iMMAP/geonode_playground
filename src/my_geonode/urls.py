
from django.conf.urls import include, url
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from geonode.urls import include, path, urlpatterns

from myapp.views import CustomSignupView

urlpatterns += [
    url(r'^account/signup/', CustomSignupView.as_view(), name='account_signup'),

    url('/help',
        login_required(TemplateView.as_view(template_name='help.html')),
        name='help'),

    path('', include('myapp.urls')),
]
