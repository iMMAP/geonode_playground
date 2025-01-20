from allauth.account.forms import SignupForm
from django import forms
from .models import *


class SimpleSignupForm(SignupForm):
    organization = forms.CharField(max_length=12, label='organization')
    first_name = forms.CharField(max_length=50, label='first_name')
    last_name = forms.CharField(max_length=50, label='last_name')
    profile = forms.CharField(max_length=50, label='profile')
    city = forms.CharField(max_length=50, label='city')
    position = forms.CharField(max_length=50, label='position')

    def save(self, request):
        user = super(SimpleSignupForm, self).save(request)
        user.organization = self.cleaned_data['organization']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.profile = self.cleaned_data['profile']
        user.city = self.cleaned_data['city']
        user.position = self.cleaned_data['position']
        user.save()
        return user
