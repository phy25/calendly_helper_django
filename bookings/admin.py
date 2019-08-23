from django.contrib import admin

# Register your models here.
from .models import Group, Booking, Invitee

admin.site.register(Group)
admin.site.register(Booking)
admin.site.register(Invitee)
