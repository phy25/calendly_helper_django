from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.apps import apps
from .models import ApprovalGroup, Invitee

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
    inlines = [InviteeInline]


class InviteeAdmin(ImportExportModelAdmin):
    resource_class = InviteeIEResource
    list_display = ('email', 'group_name')

    def group_name(self, obj):
        return obj.group.name

    group_name.admin_order_field = 'group__name'

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

admin.site.register((Hook,), HookAdmin)
admin.site.register(ApprovalGroup, GroupAdmin)
admin.site.register(Invitee, InviteeAdmin)
