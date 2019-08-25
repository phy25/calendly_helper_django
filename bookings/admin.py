from django.contrib import admin

# Register your models here.
from .models import Booking


class BookingAdmin(admin.ModelAdmin):
    readonly_fields=('created_at', 'updated_at', )
    list_display = ('email', 'event_type_id', 'spot_start', 'booked_at', 'approval_status')
    list_filter = ('approval_status', 'cancelled_at', 'booked_at', 'spot_start', 'event_type_id')


admin.site.register(Booking, BookingAdmin)