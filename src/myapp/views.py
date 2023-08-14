from allauth.account.views import SignupView
from django.conf import settings
from django.db.models import Q
from django.shortcuts import render

from .models import OchaDashboard


def ocha_dashboards(request):
    q = request.GET.get('q')

    if (request.GET.get('q') == None):
        q = ''

    ocha_dashboards = OchaDashboard.objects.filter(
        Q(name__icontains=q) |
        Q(description__icontains=q)
    )
    
    ocha_dashboards = OchaDashboard.objects.all()

    context = {'ocha_dashboards': ocha_dashboards,}

    return render(request, 'myapp/ocha-dashboard/index.html', context)
    

def ocha_dashboard(request, slug):
    ocha_dashboard = OchaDashboard.objects.get(slug=slug)

    context = {'ocha_dashboard': ocha_dashboard,}

    return render(request, 'myapp/ocha-dashboard/show.html', context)


class CustomSignupView(SignupView):

    def get_context_data(self, **kwargs):
        ret = super().get_context_data(**kwargs)
        ret.update(
            {'account_geonode_local_signup': settings.SOCIALACCOUNT_WITH_GEONODE_LOCAL_SINGUP})
        return ret



