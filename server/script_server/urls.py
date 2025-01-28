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
]