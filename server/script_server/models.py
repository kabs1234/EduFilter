from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField

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

class UserSettings(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.CharField(max_length=255, unique=True)
    blocked_sites = ArrayField(models.TextField(), default=list)  # Use ArrayField for TEXT[]
    excluded_sites = ArrayField(models.TextField(), default=list)  # Use ArrayField for TEXT[]
    categories = models.JSONField(default=dict)  # Use Django's built-in JSONField
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_settings'

    def __str__(self):
        return f"Settings for user {self.user_id}"

    @classmethod
    def get_user_settings(cls, user_id):
        """
        Fetch user settings or create with defaults if not exists.
        """
        default_settings = {
            'blocked_sites': [],
            'excluded_sites': [],
            'categories': {}
        }
        settings, created = cls.objects.get_or_create(
            user_id=user_id,
            defaults=default_settings
        )
        return settings

    def get_blocked_sites(self):
        """Get blocked sites as a Python list."""
        return self.blocked_sites if self.blocked_sites is not None else []

    def set_blocked_sites(self, sites):
        """Set blocked sites from a Python list."""
        self.blocked_sites = sites
        self.save()

    def get_excluded_sites(self):
        """Get excluded sites as a Python list."""
        return self.excluded_sites if self.excluded_sites is not None else []

    def set_excluded_sites(self, sites):
        """Set excluded sites from a Python list."""
        self.excluded_sites = sites
        self.save()

    def get_categories(self):
        """Get categories as a Python dict."""
        return self.categories if self.categories is not None else {}

    def set_categories(self, categories):
        """Set categories from a Python dict."""
        self.categories = categories
        self.save()

    def update_settings(self, **kwargs):
        """Update user settings with provided values."""
        if 'blocked_sites' in kwargs:
            self.blocked_sites = kwargs.pop('blocked_sites')
        if 'excluded_sites' in kwargs:
            self.excluded_sites = kwargs.pop('excluded_sites')
        if 'categories' in kwargs:
            self.categories = kwargs.pop('categories')
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()
