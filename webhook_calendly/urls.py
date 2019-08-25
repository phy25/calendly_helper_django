from django.urls import path
from . import views

urlpatterns = [
    path('', views.ListHooksView.as_view(), name='list_hooks'),
    path('remove/<int:id>', views.remove_hook, name='remove_hook'),
    path('add', views.add_hook, name='add_hook'),
    path('post', views.webhook_post, name='webhook_post'),
]