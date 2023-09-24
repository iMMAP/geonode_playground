from allauth.account.views import SignupView
from django.conf import settings
from django.db.models import Q
from django.shortcuts import render
from geonode.people.models import Profile
from geonode.layers.models import Dataset
from .models import OchaDashboard
from .decorators import staff_or_404
from django.utils import timezone
from django.db.models import Count, Case, When, IntegerField, Sum


from django.http import Http404
from calendar import monthrange
from datetime import datetime



@staff_or_404
def itt_stats(request):
    month_param = request.GET.get('month')
    now = timezone.now()
    
    # Generate month links
    current_month = now.month
    months = [
        {
            'number': i,
            'name': datetime(year=2022, month=i, day=1).strftime('%B'),  # Use any year, we just need the month name
            'is_future': i > current_month
        }
        for i in range(1, 13)
    ]

    if month_param is None:
        month = now.month
    else:
        try:
            month = int(month_param)
        except ValueError:
            raise Http404("Invalid month parameter")

        if month > 12 or month < 1 or month > now.month:
            raise Http404("Invalid month parameter")

    _, last_day = monthrange(now.year, month)
    month_start = timezone.datetime(now.year, month, 1, tzinfo=timezone.utc)
    month_end = timezone.datetime(now.year, month, last_day, tzinfo=timezone.utc)

    active_users = Profile.objects.filter(is_active=True, last_login__range=(month_start, month_end)).count()
    staff_count = Profile.objects.filter(is_staff=True, last_login__range=(month_start, month_end)).count()
    active_users_current_month = Profile.objects.filter(last_login__range=(month_start, month_end), is_active=True).count()

    users_per_position = Profile.objects.filter(last_login__range=(month_start, month_end)).values('position').annotate(user_count=Count('id'))
    users_per_country = Profile.objects.filter(last_login__range=(month_start, month_end)).values('country').annotate(user_count=Count('id'))

    users_per_org = Profile.objects.filter(last_login__range=(month_start, month_end)).values('organization').annotate(
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
    
    # Get all Dataset created in the month range
    # popular_count(views count), owner
    datasets_in_month = Dataset.objects.prefetch_related('owner').filter(created__range=(month_start, month_end))
    

    context = {
        "active_users": active_users,
        "staff_count": staff_count,
        "active_users_current_month": active_users_current_month,
        "users_per_position":users_per_position,
        "users_per_country":users_per_country,
        "users_per_org":users_per_org,
        "months": months,
        "datasets_in_month":datasets_in_month
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



