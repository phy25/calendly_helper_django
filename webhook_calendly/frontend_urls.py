from django.urls import path
from .views import frontend

urlpatterns = [
    path('', frontend.student_reports, name='student_reports'),
    path('students/', frontend.student_reports),
]
