from django.contrib import admin

# Register your models here.
from .models import Group, Booking, Invitee


class InviteeInline(admin.TabularInline):
    model = Invitee
    extra = 2
    show_change_link = True


class GroupAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['name']}),
    ]
    inlines = [InviteeInline]


class InviteeAdmin(admin.ModelAdmin):
    list_display = ('email', 'group_name')

    def group_name(self, obj):
        return obj.group.name

    group_name.admin_order_field = 'group__name'


admin.site.register(Group, GroupAdmin)
admin.site.register(Invitee, InviteeAdmin)
admin.site.register(Booking)