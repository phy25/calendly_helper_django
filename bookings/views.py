from django.shortcuts import render
from django.http import HttpResponse

def student_reports(request):
    return HttpResponse("EC605 bookings")