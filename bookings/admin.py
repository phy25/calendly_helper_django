from django.contrib import admin

# Register your models here.
from .models import Group, Booking, Invitee


from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin

class GroupCreationWidget(ForeignKeyWidget):
    def clean(self, value, row=None, *args, **kwargs):
        return self.model.objects.get_or_create(name=value)[0] if value else None


class InviteeIEResource(resources.ModelResource):
    email = fields.Field(column_name='email', attribute='email')
    group = fields.Field(
        column_name='group',
        attribute='group',
        widget=GroupCreationWidget(Group, 'name')
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
    inlines = [InviteeInline]


class InviteeAdmin(ImportExportModelAdmin):
    resource_class = InviteeIEResource
    list_display = ('email', 'group_name')

    def group_name(self, obj):
        return obj.group.name

    group_name.admin_order_field = 'group__name'


class BookingAdmin(admin.ModelAdmin):
    readonly_fields=('created_at', 'updated_at', )
    list_display = ('email', 'calendly_event_type_id', 'spot_start', 'booked_at', 'is_cancelled', 'is_approved')
    list_filter = ('is_approved', 'is_cancelled', 'booked_at', 'spot_start', 'calendly_event_type_id')


admin.site.register(Group, GroupAdmin)
admin.site.register(Invitee, InviteeAdmin)
admin.site.register(Booking, BookingAdmin)