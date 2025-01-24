from django.urls import path
from . import views

urlpatterns = [
    path('execute/', views.execute_script, name='execute_script'),
]