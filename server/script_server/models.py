from django.db import models
from django.utils import timezone

class UserStatus(models.Model):
    user_id = models.IntegerField(unique=True)
    last_heartbeat = models.DateTimeField(default=timezone.now)
    is_online = models.BooleanField(default=True)

    def update_heartbeat(self):
        self.last_heartbeat = timezone.now()
        self.is_online = True
        self.save()

    @classmethod
    def mark_offline_inactive_users(cls, timeout_minutes=5):
        timeout = timezone.now() - timezone.timedelta(minutes=timeout_minutes)
        cls.objects.filter(last_heartbeat__lt=timeout).update(is_online=False)
