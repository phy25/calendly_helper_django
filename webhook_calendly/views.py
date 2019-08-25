from django.shortcuts import render
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
from urllib.parse import urlencode
from django.views.decorators.csrf import csrf_exempt
from django.views import generic

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


@require_POST
@csrf_exempt
def webhook_post(request: HttpRequest):
    try:
        assert request.GET['token'] == config.WEBHOOK_TOKEN
    except Exception:
        return HttpResponseForbidden()

    json_text = request.body.decode()
    j = json.loads(json_text)
    payload = j['payload']

    is_cancelled = False

    try:
        if j['event'] == 'invitee.canceled':
            is_cancelled = True
            obj = Booking.objects.get(calendly_uuid=payload['invitee']['uuid'])
            # if obj does not exist, jump to create new one
            obj.is_cancelled = is_cancelled
            obj.calendly_data = payload
            obj.save()
        elif j['event'] == 'invitee.created':
            obj = Booking.objects.get(calendly_uuid=payload['invitee']['uuid'])
            # if exists, raise error
            return HttpResponse(status=409)
        else:
            # Don't know what to do
            return HttpResponseBadRequest('event not recognized')
    except KeyError:
        return HttpResponseBadRequest('data not complete')
    except Booking.DoesNotExist:
        try:
            values = {
                'calendly_uuid':payload['invitee']['uuid'],
                'email':payload['invitee']['email'],
                'spot_start':payload['event']['invitee_start_time'],
                'spot_end':payload['event']['invitee_end_time'],
                'booked_at':payload['invitee']['created_at'],
                'is_cancelled':is_cancelled,
                'calendly_data':payload,
                'calendly_event_type_id':payload['event_type']['uuid']
            }
            obj = Booking(**values)
            obj.save()
        except KeyError:
            return HttpResponseBadRequest('data not complete')

    return HttpResponse('OK')


@method_decorator(superuser_required, name='dispatch')
class ListHooksView(generic.ListView):
    template_name = 'webhook_calendly/list.html'
    context_object_name = 'hooks_list'

    def dispatch(self, request, *args, **kwargs):
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
                return j['data']
        return []

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
    post_data = "events[]=invitee.created&events[]=invitee.canceled&"+urlencode({'url': request.build_absolute_uri(reverse('webhook_post')+'?token='+config.WEBHOOK_TOKEN)})
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