"""
URL configuration for script_server project.
"""
from django.contrib import admin
from django.urls import include, path
from . import views

script_executor_patterns = [
    path('user-settings/', views.user_settings, name='user_settings'),
    path('register-ip/', views.register_ip, name='register_ip'),
    path('delete-ip/', views.delete_ip, name='delete_ip'),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(script_executor_patterns)),
    path('heartbeat/', views.heartbeat, name='heartbeat'),
    path('online-users/', views.get_online_users, name='online_users'),
    path('user-ips/', views.get_user_ips, name='user_ips'),
]