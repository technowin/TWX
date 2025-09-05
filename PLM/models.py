from django.db import models

# Create your models here.

class StatusAction(models.Model):
    status = models.TextField()
    action = models.TextField()
    badge_class = models.CharField(max_length=50, default="bg-secondary")
    action_value = models.TextField(default=1)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    created_by =  models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_by =  models.TextField(null=True, blank=True)
    class Meta:
        db_table = 'status_action'