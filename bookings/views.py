from django.shortcuts import render
from django.http import HttpResponse

def student_reports(request):
    return render(request, 'bookings/base.html', context)