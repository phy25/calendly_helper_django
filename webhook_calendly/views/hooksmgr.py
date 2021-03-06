from django.http import (
    HttpRequest, HttpResponse, JsonResponse,
    HttpResponseForbidden, HttpResponseBadRequest, HttpResponseServerError, HttpResponseRedirect)
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from django.contrib.auth import REDIRECT_FIELD_NAME
from constance import config
import json
import urllib.request
from django.utils.dateparse import parse_datetime
from urllib.parse import urlencode
from django.views.decorators.csrf import csrf_exempt
from django.views import generic
from django.contrib import admin

from bookings.models import Booking


def superuser_required(view_func=None, redirect_field_name=REDIRECT_FIELD_NAME,
                   login_url='admin:login'):
    """
    Decorator for views that checks that the user is logged in and is a
    superuser, redirecting to the login page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_active and u.is_superuser,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator


def get_hook_url(request):
    return request.build_absolute_uri(reverse('webhook_post')+'?token='+config.WEBHOOK_TOKEN)


@method_decorator(superuser_required, name='dispatch')
class ListHooksView(generic.ListView):
    template_name = 'webhook_calendly/list.html'
    context_object_name = 'hooks_list'
    cached_request = None

    def dispatch(self, request, *args, **kwargs):
        self.cached_request = request
        if not config.CALENDLY_WEBHOOK_TOKEN:
            return HttpResponseBadRequest('Please set up token first!')
        return super(generic.ListView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        req = urllib.request.Request(url='https://calendly.com/api/v1/hooks',
            headers={'X-TOKEN':config.CALENDLY_WEBHOOK_TOKEN})
        with urllib.request.urlopen(req) as f:
            text = f.read().decode()
            j = json.loads(text)
            if j['data']:
                for i in j['data']:
                    i['attributes']['created_at'] = parse_datetime(i['attributes']['created_at'])
                return j['data']
        return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Calendly Hooks'
        context['site_title'] = admin.site.site_title
        context['site_header'] = admin.site.site_header
        urls = [i['attributes']['url'] for i in context[self.context_object_name]]
        hook_url = get_hook_url(self.cached_request)
        context['has_hook'] = (hook_url in urls)
        return context


@superuser_required
@require_POST
def remove_hook(request: HttpRequest, id: int):
    if not config.CALENDLY_WEBHOOK_TOKEN:
        return HttpResponseBadRequest('Please set up token first!')
    req = urllib.request.Request(url='https://calendly.com/api/v1/hooks/'+str(id),
        headers={'X-TOKEN':config.CALENDLY_WEBHOOK_TOKEN}, method='DELETE')
    with urllib.request.urlopen(req) as f:
        if f.status == 200:
            return HttpResponseRedirect(reverse('list_hooks'))
        else:
            return HttpResponse(f.read().decode(), status=f.status, content_type='application/json')


@superuser_required
@require_POST
def add_hook(request: HttpRequest):
    if not config.CALENDLY_WEBHOOK_TOKEN:
        return HttpResponseBadRequest('Please set up token first!')
    post_data = "events[]=invitee.created&events[]=invitee.canceled&"+urlencode({'url': get_hook_url(request)})
    req = urllib.request.Request(url='https://calendly.com/api/v1/hooks/',
        data=post_data.encode(),
        headers={'X-TOKEN':config.CALENDLY_WEBHOOK_TOKEN}, method='POST')
    try:
        f = urllib.request.urlopen(req)
        if f.status == 201:
            return HttpResponseRedirect(reverse('list_hooks'))
        else:
            return HttpResponse(f.read().decode(), status=f.status, content_type='application/json')
    except urllib.request.HTTPError as e:
        f = e.file
        return HttpResponse(f.read().decode(), status=f.status, content_type='application/json')
