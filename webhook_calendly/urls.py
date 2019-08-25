from django.urls import path
from . import views

urlpatterns = [
    path('', views.hooksmgr.ListHooksView.as_view(), name='list_hooks'),
    path('remove/<int:id>', views.hooksmgr.remove_hook, name='remove_hook'),
    path('add', views.hooksmgr.add_hook, name='add_hook'),
    path('post', views.hook.webhook_post, name='webhook_post'),
]
