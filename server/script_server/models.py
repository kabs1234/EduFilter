from django.db import models
from django.utils import timezone

class UserIP(models.Model):
    user_id = models.CharField(max_length=100, unique=True)
    ip_address = models.CharField(max_length=100)
    port = models.IntegerField(default=8081)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_id} - {self.ip_address}:{self.port}"

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
