from django.contrib import admin
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry, CHANGE

from .models import Booking, CancelledBooking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    readonly_fields = ('created_at', 'updated_at', 'cancelled_at', )
    list_display = ('email', 'event_type_id', 'spot_start', 'booked_at', 'approval_status', 'approval_protected')
    list_filter = ('approval_status', 'booked_at', 'spot_start', 'event_type_id')

    def get_content_type_id(self):
        return ContentType.objects.get_for_model(Booking).pk

    def approve_and_protect(self, request, queryset):
        try:
            changed = queryset.update(approval_status=Booking.APPROVAL_STATUS_APPROVED, approval_protected=True)
            for b in queryset:
                LogEntry.objects.log_action(
                                    user_id=request.user.id,
                                    content_type_id=self.get_content_type_id(),
                                    object_id=b.pk,
                                    object_repr=str(b),
                                    change_message="Approved and protected",
                                    action_flag=CHANGE)
            self.message_user(request, "Approved and protected "+str(changed)+" rows.")
        except Exception as e:
            self.message_user(request, str(e), messages.ERROR)
    approve_and_protect.short_description = "Approve and protect"
    approve_and_protect.allowed_permissions = ('change',)

    def decline_and_protect(self, request, queryset):
        try:
            changed = queryset.update(approval_status=Booking.APPROVAL_STATUS_DECLINED, approval_protected=True)
            for b in queryset:
                LogEntry.objects.log_action(
                                    user_id=request.user.id,
                                    content_type_id=self.get_content_type_id(),
                                    object_id=b.pk,
                                    object_repr=str(b),
                                    change_message="Declined and protected",
                                    action_flag=CHANGE)
            self.message_user(request, "Declined and protected "+str(changed)+" rows.")
        except Exception as e:
            self.message_user(request, str(e), messages.ERROR)
    decline_and_protect.short_description = "Decline and protect"
    decline_and_protect.allowed_permissions = ('change',)

    def reset_approval(self, request, queryset):
        try:
            changed = queryset.update(approval_status=Booking.APPROVAL_STATUS_NEW, approval_protected=False)
            for b in queryset:
                LogEntry.objects.log_action(
                                    user_id=request.user.id,
                                    content_type_id=self.get_content_type_id(),
                                    object_id=b.pk,
                                    object_repr=str(b),
                                    change_message="Reseted approval",
                                    action_flag=CHANGE)
            self.message_user(request, "Reseted "+str(queryset.count())+" rows.")
        except Exception as e:
            self.message_user(request, str(e), messages.ERROR)
    reset_approval.short_description = "Reset approval"
    reset_approval.allowed_permissions = ('change',)

    actions = [approve_and_protect, decline_and_protect, reset_approval]


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
