from django.shortcuts import render
from allauth.account.views import SignupView
from django.conf import settings


class CustomSignupView(SignupView):

    def get_context_data(self, **kwargs):
        ret = super().get_context_data(**kwargs)
        ret.update(
            {'account_geonode_local_signup': settings.SOCIALACCOUNT_WITH_GEONODE_LOCAL_SINGUP})
        return ret
