from django.db import models


class OchaDashboard(models.Model):
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    content = models.TextField(null=True, blank=True)

    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-updated', '-created']
        constraints = [
            models.UniqueConstraint(fields=['slug'], name='unique_slug')
        ]

    def __str__(self):
        return self.name
