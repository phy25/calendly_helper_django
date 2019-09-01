from django.shortcuts import render
from django.http import HttpResponse

def student_reports(request):
    context = {}
    return render(request, 'bookings/base.html', context)