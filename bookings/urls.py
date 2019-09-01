from django.urls import path
from . import views

urlpatterns = [
    path('', views.student_reports, name='student_reports'),
    path('students/', views.student_reports),
    path('ping', views.ping, name='ping')
]