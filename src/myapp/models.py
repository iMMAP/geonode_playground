from django.db import models
from django.utils.text import slugify
from geonode.people.models import Profile

class ProfileProxy(Profile):

    class Meta:
        proxy = True
        verbose_name = 'HSDC User'



class OchaDashboard(models.Model):
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    content = models.TextField(null=True, blank=True)
    thumbnail = models.ImageField(null=True, blank=True, upload_to='external_dashboard_thumbnails')

    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-updated', '-created']
        constraints = [
            models.UniqueConstraint(fields=['slug'], name='unique_slug')
        ]

    def save(self, *args, **kwargs):  
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class UserLoginLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    login_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} logged in at {self.login_time}"