from django.shortcuts import render
from django.http import HttpRequest, HttpResponseForbidden, HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from constance import config
import json
from django.views.decorators.csrf import csrf_exempt

from bookings.models import Booking

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

@staff_member_required
@user_passes_test(lambda u: u.is_superuser)
def list_remote_webhooks(request: HttpRequest):
    return HttpResponse('Yes!')
