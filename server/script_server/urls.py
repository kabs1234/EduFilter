"""
URL configuration for script_server project.
"""
from django.contrib import admin
from django.urls import include, path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('script_executor.urls')),
    path('heartbeat/', views.heartbeat, name='heartbeat'),
    path('online-users/', views.get_online_users, name='online_users'),
    path('register-ip/', views.register_ip, name='register_ip'),
    path('user-ips/', views.get_user_ips, name='user_ips'),
    path('delete-ip/', views.delete_ip, name='delete_ip'),
]