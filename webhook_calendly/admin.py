from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.apps import apps
from .views import ListHooksView


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

admin.site.register([Hook], HookAdmin)
