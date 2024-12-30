from allauth.account.views import SignupView
from django.conf import settings
from django.db.models import Q, Max
from django.shortcuts import render
from geonode.people.models import Profile
from geonode.base.models import ResourceBase
from geonode.layers.models import Dataset
from .models import OchaDashboard, UserLoginLog
from .decorators import staff_or_404
from django.utils import timezone
from django.db.models import Count, Case, When, IntegerField, Sum
from django.shortcuts import redirect
from django.utils.timezone import localtime


from django.http import Http404, HttpResponse
from calendar import monthrange
from datetime import datetime
from django.core.exceptions import ValidationError
import traceback
from django.db.models.functions import TruncMonth

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse




@staff_or_404
def itt_stats(request):
    month_param = request.GET.get('month')
    now = timezone.now()
    
    # Generate month links
    current_month = now.month
    current_year = now.year
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
    month_end = timezone.datetime(now.year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    active_users = UserLoginLog.objects.filter(login_time__range=(month_start, month_end)).values('user__username').distinct().count()
    month_total_logins = UserLoginLog.objects.filter(login_time__range=(month_start, month_end)).count()

    staff_count = UserLoginLog.objects.filter(user__is_staff=True, login_time__range=(month_start, month_end)).values('user__username').distinct().count()
    recent_user_logs = UserLoginLog.objects.filter(
        user__is_active=True,
        login_time__range=(month_start, month_end)
    ).values('user').annotate(latest_login=Max('login_time')).order_by('-latest_login')

    active_users_list = UserLoginLog.objects.filter(
        login_time__range=(month_start, month_end)
    ).values(
        'user__id',
        'user__first_name',
        'user__last_name',
        'user__email',
        'user__organization',
        'user__country',
        'user__is_active'
    ).annotate(
        last_login=Max('login_time'),
        login_count=Count('id')
    )

    users_per_position = UserLoginLog.objects.filter(login_time__range=(month_start, month_end)).values('user__position').annotate(last_login=Max('login_time'), user_count=Count('user__id', distinct=True))
    users_per_country = UserLoginLog.objects.filter(login_time__range=(month_start, month_end)).values('user__country').annotate(last_login=Max('login_time'), user_count=Count('user__id', distinct=True))
    users_per_org = UserLoginLog.objects.filter(login_time__range=(month_start, month_end)).values('user__organization').annotate(
        last_login=Max('login_time'),
        active_user_count=Count(
            Case(
                When(user__is_active=True, then="user__id"),
                output_field=IntegerField()
            ),
            distinct=True
        ),
        inactive_user_count=Count(
            Case(
                When(user__is_active=False, then="user__id"),
                output_field=IntegerField()
            ),
            distinct=True,
        ),
    )

    previous_month = month - 1 if month > 1 else 12
    previous_year = now.year if month > 1 else now.year - 1
    _, last_day_prev = monthrange(previous_year, previous_month)
    datasets_in_month = Dataset.objects.prefetch_related('owner').filter(created__range=(month_start, month_end)).values('owner', 'owner__organization', 'name', 'popular_count', 'created')
    for datasets_in_month_created in datasets_in_month:
        datasets_in_month_created['created'] = localtime(datasets_in_month_created['created']).strftime('%Y-%m-%d %H:%M:%S')


    #PERCENTAGE CALCULATION
    
    prev_month_start = timezone.make_aware(datetime(previous_year, previous_month, 1), timezone.get_current_timezone())
    prev_month_end = timezone.make_aware(datetime(previous_year, previous_month, last_day_prev, 23, 59, 59), timezone.get_current_timezone())
    active_users_last_month = UserLoginLog.objects.filter(user__is_active=True, login_time__range=(prev_month_start, prev_month_end)).distinct().count()
    # active_users = UserLoginLog.objects.filter(login_time__range=(month_start, month_end)).values('user__username').distinct().count()
    
    if active_users_last_month > 0:
        percent_change = round(((active_users - active_users_last_month) / active_users_last_month) * 100)
    else:
        percent_change = 100 if active_users > 0 else 0
    
    if percent_change > 100:
        percent_change = 100

    if percent_change > 0:
        change_phrase = f"{percent_change}% more than last month"
    elif percent_change < 0:
        change_phrase = f"{abs(percent_change)}% less than last month"
    else:
        change_phrase = "No change from last month"

    context = {
        "months":months,
        "change_phrase":change_phrase,
        'active_users': active_users,
        'month_total_logins': month_total_logins,
        'staff_count': staff_count,
        'percent_change': percent_change,
        'users_per_position': users_per_position,
        'users_per_country': users_per_country,
        'users_per_org': users_per_org,
        'active_users_list': active_users_list,
        'datasets_in_month': datasets_in_month,
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


def landing_redirect(request):
    next_url = request.GET.get('next')
    if next_url == '/':
        return render(request, 'myapp/landing.html')

    elif next_url and next_url.startswith('/'):
        # login_url = f"https://dev.hsdc.immap.org/account/login/?next={next_url}"
        login_url = f"https://hsdc.immap.org/account/login/?next={next_url}"
        return redirect(login_url)

    else:
        return render(request, 'myapp/landing.html', {'next': next_url})
