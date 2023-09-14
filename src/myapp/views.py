from allauth.account.views import SignupView
from django.conf import settings
from django.db.models import Q
from django.shortcuts import render
from geonode.people.models import Profile
from .models import OchaDashboard
from .decorators import staff_or_404
from django.utils import timezone
from django.db.models import Count, Case, When, IntegerField, Sum




@staff_or_404
def itt_stats(request):
    active_users = Profile.objects.filter(is_active=True).count()
    staff_count = Profile.objects.filter(is_staff=True).count()
    
    now = timezone.now()
    month_start = timezone.datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    active_users_current_month = Profile.objects.filter(last_login__gte=month_start, is_active=True).count()
    
    users_per_position = Profile.objects.values('position').annotate(user_count=Count('id'))
    users_per_country = Profile.objects.values('country').annotate(user_count=Count('id'))
    
    users_per_org = Profile.objects.values('organization').annotate(
        user_count=Count('id'),
        active_user_count=Sum(
            Case(
                When(is_active=True, then=1),
                default=0,
                output_field=IntegerField()
            )
        ),
        inactive_user_count=Sum(
            Case(
                When(is_active=False, then=1),
                default=0,
                output_field=IntegerField()
            )
        )
    )

    context = {
        "active_users": active_users,
        "staff_count": staff_count,
        "active_users_current_month": active_users_current_month,
        "users_per_position":users_per_position,
        "users_per_country":users_per_country,
        "users_per_org":users_per_org
    }
    
    return render(request, 'myapp/itt_stats.html', context) 

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



