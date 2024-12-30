from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import pre_save
from django.dispatch import receiver
from geonode.layers.models import Dataset
from django.db.models import F
from myapp.models import UserLoginLog
import logging

logger = logging.getLogger(__name__)

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    UserLoginLog.objects.create(user=user)