from django.apps import AppConfig
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


class MyappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapp'

    def ready(self):
        import myapp.itt_report_signals
