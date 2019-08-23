"""calendly_helper URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from constance import config

urlpatterns = [
    path('', include('bookings.urls')),
    path('admin/', admin.site.urls),
]


from django.dispatch import receiver
from constance.signals import config_updated

admin.site.site_header = config.SITE_TITLE
admin.site.index_title = config.SITE_TITLE

@receiver(config_updated)
def constance_updated(sender, key, old_value, new_value, **kwargs):
    if key == 'SITE_TITLE':
        admin.site.site_header = new_value
        admin.site.index_title = new_value