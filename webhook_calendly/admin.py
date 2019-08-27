from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.apps import apps
from django.db.models import Count, Subquery, OuterRef
from django.db.models.fields import IntegerField
from django.contrib import messages
from .models import ApprovalGroup, Invitee, BookingCalendlyData
from bookings.models import Booking, CancelledBooking

from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from bookings.admin import BookingAdmin, CancelledBookingAdmin

from .admin_decorators import admin_link
from .views.frontend import get_default_event_type_id


class GroupCreationWidget(ForeignKeyWidget):
    def clean(self, value, row=None, *args, **kwargs):
        return self.model.objects.get_or_create(name=value)[0] if value else None


class InviteeIEResource(resources.ModelResource):
    email = fields.Field(column_name='email', attribute='email')
    group = fields.Field(
        column_name='group',
        attribute='group',
        widget=GroupCreationWidget(ApprovalGroup, 'name')
    )

    class Meta:
        model = Invitee
        fields = ('email', 'group', )
        export_order = ('email', 'group', )
        import_id_fields = ('email', )


class InviteeInline(admin.TabularInline):
    model = Invitee
    extra = 2
    show_change_link = True


class GroupAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['name']}),
    ]
    list_display = ('name', 'invitees_count', 'bookings_total')
    inlines = [InviteeInline]

    def execute_approval(self, request, queryset):
        event_type_id = get_default_event_type_id()
        if not event_type_id:
            self.message_user(request, 'There is no default event_type_id', messages.ERROR)
            return

        try:
            for group in queryset:
                approved, declined = group.get_approval_executor(event_type_id)
                changed = group.execute_approval(approved, declined)
            self.message_user(request, "Updated "+str(changed)+" approval in "+event_type_id+".")
        except Exception as e:
            self.message_user(request, str(e), messages.ERROR)

    execute_approval.short_description = "Execute Default Approval"
    execute_approval.allowed_permissions = ('change',)

    actions = [execute_approval]

    def invitees_count(self, inst):
        return inst._invitees_count
    invitees_count.short_description = 'Invitees Count'
    invitees_count.admin_order_field = '_invitees_count'

    def bookings_total(self, inst):
        #return None
        return inst._bookings_total
    #bookings_total.short_description = 'Bookings Total'
    #bookings_total.admin_order_field = '_bookings_total'

    def get_queryset(self, request):
        qs = super(GroupAdmin, self).get_queryset(request)
        return qs.annotate(
            _invitees_count=Count('invitee', distinct=True),
            _bookings_total=Count('bookingcalendlydata', distinct=True)
        )


class InviteeAdmin(ImportExportModelAdmin):
    resource_class = InviteeIEResource
    list_display = ('email', 'group_link', 'bookings_total')
    list_select_related = ('group',)

    @admin_link('group', _('Group'))
    def group_link(self, group):
        return group

    def bookings_total(self, obj):
        return obj._bookings_total
    bookings_total.admin_order_field = '_bookings_total'

    def get_queryset(self, request):
        qs = super(InviteeAdmin, self).get_queryset(request)
        booking_qs = Booking.objects.filter(
                email=OuterRef('email')
            ).values('email').order_by('email').annotate(
                total=Count('email')
            ).values('total')
        return qs.annotate(
            _bookings_total=Subquery(booking_qs[:1], output_field=IntegerField())
        )


class HookAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect(reverse('list_hooks'))


class Hook(object):
    class Meta(object):
        app_label = 'webhook_calendly'
        object_name = 'Hook'
        model_name = module_name = 'hook'
        verbose_name_plural = _('hooks')
        abstract = False
        swapped = False

        def get_ordered_objects(self):
            return False

        def get_change_permission(self):
            return 'change_%s' % self.model_name

        @property
        def app_config(self):
            return apps.get_app_config(self.app_label)

        @property
        def label(self):
            return '%s.%s' % (self.app_label, self.object_name)

        @property
        def label_lower(self):
            return '%s.%s' % (self.app_label, self.model_name)

    _meta = Meta()


class BookingCalendlyInline(admin.StackedInline):
    model = BookingCalendlyData
    # extra = 0
    show_change_link = True


class CancelledBookingCalendlyInline(BookingCalendlyInline):
    def get_readonly_fields(self, request, obj=None):
        # make all fields readonly
        readonly_fields = list(set(
            [field.name for field in self.model._meta.fields]
        ))
        return readonly_fields


class BookingCalendlyAdmin(BookingAdmin):
    inlines = [BookingCalendlyInline]


class CancelledBookingCalendlyAdmin(CancelledBookingAdmin):
    inlines = [CancelledBookingCalendlyInline]


admin.site.unregister(Booking)
admin.site.register(Booking, BookingCalendlyAdmin)
admin.site.unregister(CancelledBooking)
admin.site.register(CancelledBooking, CancelledBookingCalendlyAdmin)

admin.site.register((Hook,), HookAdmin)
admin.site.register(ApprovalGroup, GroupAdmin)
admin.site.register(Invitee, InviteeAdmin)
