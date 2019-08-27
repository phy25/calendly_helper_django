from django.urls import path
from .views import frontend

urlpatterns = [
    path('', frontend.student_reports, name='student_reports'),
    path('invitees/', frontend.student_reports),
    path('reports/', frontend.admin_reports, name='admin_reports')
]
