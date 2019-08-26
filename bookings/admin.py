from django.contrib import admin

# Register your models here.
from .models import Booking, CancelledBooking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    readonly_fields = ('created_at', 'updated_at', 'cancelled_at', )
    list_display = ('email', 'event_type_id', 'spot_start', 'booked_at', 'approval_status')
    list_filter = ('approval_status', 'booked_at', 'spot_start', 'event_type_id')


@admin.register(CancelledBooking)
class CancelledBookingAdmin(admin.ModelAdmin):
    list_display = ('email', 'event_type_id', 'spot_start', 'booked_at', 'approval_status')
    list_filter = ('approval_status', 'cancelled_at', 'spot_start', 'event_type_id')

    #def get_queryset(self, request):
    #    qs = super(CancelledBookingAdmin, self).get_queryset(request)
    #    return qs.cancelled()

    def has_add_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        # make all fields readonly
        readonly_fields = list(set(
            [field.name for field in self.model._meta.fields]
        ))
        if 'cancelled_at' in readonly_fields:
            readonly_fields.remove('cancelled_at')
        return readonly_fields
