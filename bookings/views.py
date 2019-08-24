from django.shortcuts import render
from django.http import HttpResponse

def student_reports(request):
    context = {'invalid_bookings_count': 1}
    return render(request, 'bookings/student_reports.html', context)