from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_remote_webhooks, name='list_remote_webhooks'),
    path('post', views.webhook_post, name='webhook_post'),
]