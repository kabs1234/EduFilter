"""
URL configuration for script_server project.
"""
from django.contrib import admin
from django.urls import include, path
from . import views, admin_views

script_executor_patterns = [
    path('user-settings/<str:user_id>/', views.user_settings, name='user_settings'),
    path('register-ip/', views.register_ip, name='register_ip'),
    path('delete-ip/', views.delete_ip, name='delete_ip'),
]

admin_patterns = [
    path('user-settings/<int:user_id>/', admin_views.get_user_settings, name='admin_get_user_settings'),
    path('user-settings/<int:user_id>/update/', admin_views.update_user_settings, name='admin_update_user_settings'),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(script_executor_patterns)),
    path('api/admin/', include(admin_patterns)),
    path('heartbeat/', views.heartbeat, name='heartbeat'),
    path('online-users/', views.get_online_users, name='online_users'),
    path('user-ips/', views.get_user_ips, name='user_ips'),
]