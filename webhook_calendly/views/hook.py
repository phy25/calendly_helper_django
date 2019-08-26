from django.http import (
    HttpRequest, HttpResponse,
    HttpResponseForbidden, HttpResponseBadRequest, HttpResponseServerError, HttpResponseRedirect)
from django.views.decorators.http import require_POST
from constance import config
import json
from django.views.decorators.csrf import csrf_exempt

from bookings.models import Booking
from ..models import BookingCalendlyData


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
    obj = None

    try:
        if j['event'] == 'invitee.canceled':
            is_cancelled = True
            obj = BookingCalendlyData.objects.get(calendly_uuid=payload['invitee']['uuid'])
            # if obj does not exist, jump to create new one
            obj.calendly_data = payload
            obj.save()
        elif j['event'] == 'invitee.created':
            obj = BookingCalendlyData.objects.get(calendly_uuid=payload['invitee']['uuid'])
            # if exists, raise error
            return HttpResponse(status=409)
        else:
            # Don't know what to do
            return HttpResponseBadRequest('event not recognized')
    except KeyError:
        return HttpResponseBadRequest('data not complete')
    except BookingCalendlyData.DoesNotExist:
        try:
            values = {
                'event_type_id':payload['event_type']['uuid'],
                'email':payload['invitee']['email'],
                'spot_start':payload['event']['invitee_start_time'],
                'spot_end':payload['event']['invitee_end_time'],
                'booked_at':payload['invitee']['created_at'],
            }
            booking = Booking(**values)
            booking.save()
            calendly_data = {
                'calendly_uuid':payload['invitee']['uuid'],
                'payload':payload,
                'booking':booking,
            }
            obj = BookingCalendlyData(**calendly_data)
            obj.save()
        except KeyError:
            return HttpResponseBadRequest('data not complete')
    finally:
        if is_cancelled:
            obj.booking.delete() # cancel

    return HttpResponse('OK')
