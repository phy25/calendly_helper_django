from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.dateparse import parse_datetime
from django.contrib.admin.models import LogEntry
from django.contrib.admin import ModelAdmin, AdminSite
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from constance import config
from unittest.mock import Mock, patch
from io import BytesIO
from urllib.request import HTTPError

from bookings.models import Booking
from .models import BookingCalendlyData
from .admin import Hook, HookAdmin
from .views.hooksmgr import get_hook_url, ListHooksView, add_hook, remove_hook
import json


class HookAdminTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser("test", "test@localhost", "test")

        self.get_hooks_byteio = BytesIO(b'{"data":[{"type":"hooks","id":12345,"attributes":{"url":"http://foo.bar/1","created_at":"2016-08-23T19:15:24Z","state":"active","events":["invitee.created","invitee.canceled"]}},{"type":"hooks","id":1234,"attributes":{"url":"http://localhost:8000/calendly/post?token=TOK","created_at":"2016-02-11T19:10:12Z","state":"disabled","events":["invitee.created"]}}]}')

        config.CALENDLY_WEBHOOK_TOKEN = '1'

    def tearDown(self):
        self.user.delete()
        LogEntry.objects.all().delete()

    def test_redirect(self):
        config.CALENDLY_WEBHOOK_TOKEN = None
        self.client.force_login(self.user)
        response = self.client.get(reverse('admin:webhook_calendly_hook_changelist'), follow=True)

        self.assertEqual(response.status_code, 400) # No token has been set up yet
        self.assertTrue(reverse('list_hooks') in response.redirect_chain[0][0])

    def test_get_hook_url(self):
        url = get_hook_url(self.factory.get('/'))
        self.assertTrue(config.WEBHOOK_TOKEN in url)
        self.assertTrue('://' in url) # Absolute URL

    def test_permission(self):
        site = AdminSite()
        ma = HookAdmin(Hook, site)
        request = self.factory.get('/')
        request.user = self.user
        self.assertEqual(ma.has_add_permission(request), False)
        self.assertEqual(ma.has_change_permission(request), False)
        self.assertEqual(ma.has_view_permission(request), True)
        self.assertEqual(ma.has_delete_permission(request), True)

    def test_get_queryset(self):
        with patch('urllib.request.urlopen') as urlopen:
            urlopen.return_value = self.get_hooks_byteio
            data = ListHooksView.get_queryset(None)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]['attributes']['url'], 'http://foo.bar/1')
            self.assertEqual(data[1]['attributes']['url'], 'http://localhost:8000/calendly/post?token=TOK')

    def test_get_hook(self):
        config.WEBHOOK_TOKEN = 'TOK'
        with patch('urllib.request.urlopen') as urlopen:
            urlopen.return_value = self.get_hooks_byteio
            self.client.force_login(self.user)
            response = self.client.get(reverse('list_hooks'), HTTP_HOST='localhost:8000')
            self.assertTrue(response.context['has_hook'])

    def test_add_hook(self):
        request = self.factory.post('/')
        request.user = self.user
        response = Mock()
        response.status = 201

        with patch('urllib.request.urlopen', return_value=response) as urlopen:
            data = add_hook(request)
            self.assertTrue(isinstance(data, HttpResponseRedirect))

    def test_add_hook_notoken(self):
        config.CALENDLY_WEBHOOK_TOKEN = None
        request = self.factory.post('/')
        request.user = self.user
        response = Mock()
        response.status = 404

        with patch('urllib.request.urlopen', return_value=response) as urlopen:
            data = add_hook(request)
            self.assertTrue(isinstance(data, HttpResponseBadRequest))

    def test_add_hook_error(self):
        request = self.factory.post('/')
        request.user = self.user

        resp = BytesIO(b'')
        resp.status = 412
        error = HTTPError('', 412, '', {}, resp)
        with patch('urllib.request.urlopen', side_effect=error) as urlopen:
            data = add_hook(request)
            self.assertTrue(isinstance(data, HttpResponse))
            self.assertTrue(data.status_code, 412)

    def test_remove_hook(self):
        request = self.factory.post('/')
        request.user = self.user
        response = BytesIO(b'')
        response.status = 200

        with patch('urllib.request.urlopen', return_value=response) as urlopen:
            data = remove_hook(request, 1)
            self.assertTrue(isinstance(data, HttpResponseRedirect))

    def test_remove_hook_notoken(self):
        config.CALENDLY_WEBHOOK_TOKEN = None
        request = self.factory.post('/')
        request.user = self.user
        response = BytesIO(b'')
        response.status = 404

        with patch('urllib.request.urlopen', return_value=response) as urlopen:
            data = remove_hook(request, 1)
            self.assertTrue(isinstance(data, HttpResponseBadRequest))

    def test_remove_hook_error(self):
        config.CALENDLY_WEBHOOK_TOKEN = '1'
        request = self.factory.post('/')
        request.user = self.user
        response = BytesIO(b'')
        response.status = 404

        with patch('urllib.request.urlopen', return_value=response) as urlopen:
            data = remove_hook(request, 1)
            self.assertTrue(isinstance(data, HttpResponse))
            self.assertEqual(data.status_code, 404)


class HookPostTests(TestCase):
    json_create = '{"event":"invitee.created","time":"2018-03-14T19:16:01Z","payload":{"event_type":{"uuid":"CCCCCCCCCCCCCCCC","kind":"One-on-One","slug":"event_type_name","name":"Event Type Name","duration":15,"owner":{"type":"users","uuid":"DDDDDDDDDDDDDDDD"}},"event":{"uuid":"BBBBBBBBBBBBBBBB","assigned_to":["Jane Sample Data"],"extended_assigned_to":[{"name":"Jane Sample Data","email":"user@example.com","primary":false}],"start_time":"2018-03-14T12:00:00Z","start_time_pretty":"12:00pm - Wednesday, March 14, 2018","invitee_start_time":"2018-03-14T12:00:00Z","invitee_start_time_pretty":"12:00pm - Wednesday, March 14, 2018","end_time":"2018-03-14T12:15:00Z","end_time_pretty":"12:15pm - Wednesday, March 14, 2018","invitee_end_time":"2018-03-14T12:15:00Z","invitee_end_time_pretty":"12:15pm - Wednesday, March 14, 2018","created_at":"2018-03-14T00:00:00Z","location":"The Coffee Shop","canceled":false,"canceler_name":null,"cancel_reason":null,"canceled_at":null},"invitee":{"uuid":"AAAAAAAAAAAAAAAA","first_name":"Joe","last_name":"Sample Data","name":"Joe Sample Data","email":"not.a.real.email@example.com","text_reminder_number":"+14045551234","timezone":"UTC","created_at":"2018-03-14T00:00:00Z","is_reschedule":false,"payments":[{"id":"ch_AAAAAAAAAAAAAAAAAAAAAAAA","provider":"stripe","amount":1234.56,"currency":"USD","terms":"sample terms of payment (up to 1,024 characters)","successful":true}],"canceled":false,"canceler_name":null,"cancel_reason":null,"canceled_at":null},"questions_and_answers":[{"question":"Skype ID","answer":"fake_skype_id"},{"question":"Facebook ID","answer":"fake_facebook_id"},{"question":"Twitter ID","answer":"fake_twitter_id"},{"question":"Google ID","answer":"fake_google_id"}],"questions_and_responses":{"1_question":"Skype ID","1_response":"fake_skype_id","2_question":"Facebook ID","2_response":"fake_facebook_id","3_question":"Twitter ID","3_response":"fake_twitter_id","4_question":"Google ID","4_response":"fake_google_id"},"tracking":{"utm_campaign":null,"utm_source":null,"utm_medium":null,"utm_content":null,"utm_term":null,"salesforce_uuid":null},"old_event":null,"old_invitee":null,"new_event":null,"new_invitee":null}}'
    json_cancel = '{"event":"invitee.canceled","time":"2018-03-14T19:16:01Z","payload":{"event_type":{"uuid":"ZZZZZZZZZZZZZZZZ","kind":"One-on-One","slug":"event_type_name","name":"Event Type Name","duration":15,"owner":{"type":"users","uuid":"DDDDDDDDDDDDDDDD"}},"event":{"uuid":"BBBBBBBBBBBBBBBB","assigned_to":["Jane Sample Data"],"extended_assigned_to":[{"name":"Jane Sample Data","email":"user@example.com","primary":false}],"start_time":"2018-03-14T12:00:00Z","start_time_pretty":"12:00pm - Wednesday, March 14, 2018","invitee_start_time":"2018-03-14T12:00:00Z","invitee_start_time_pretty":"12:00pm - Wednesday, March 14, 2018","end_time":"2018-03-14T12:15:00Z","end_time_pretty":"12:15pm - Wednesday, March 14, 2018","invitee_end_time":"2018-03-14T12:15:00Z","invitee_end_time_pretty":"12:15pm - Wednesday, March 14, 2018","created_at":"2018-03-14T00:00:00Z","location":"The Coffee Shop","canceled":true,"canceler_name":"Joe Sample Data","cancel_reason":"This was not a real meeting.","canceled_at":"2018-03-14T00:00:00Z"},"invitee":{"uuid":"AAAAAAAAAAAAAAAA","first_name":"Joe","last_name":"Sample Data","name":"Joe Sample Data","email":"not.a.real.email@example.com","text_reminder_number":"+14045551234","timezone":"UTC","created_at":"2018-03-14T00:00:00Z","is_reschedule":false,"payments":[{"id":"ch_AAAAAAAAAAAAAAAAAAAAAAAA","provider":"stripe","amount":1234.56,"currency":"USD","terms":"sample terms of payment (up to 1,024 characters)","successful":true}],"canceled":true,"canceler_name":"Joe Sample Data","cancel_reason":"This was not a real meeting.","canceled_at":"2018-03-14T00:00:00Z"},"questions_and_answers":[{"question":"Skype ID","answer":"fake_skype_id"},{"question":"Facebook ID","answer":"fake_facebook_id"},{"question":"Twitter ID","answer":"fake_twitter_id"},{"question":"Google ID","answer":"fake_google_id"}],"questions_and_responses":{"1_question":"Skype ID","1_response":"fake_skype_id","2_question":"Facebook ID","2_response":"fake_facebook_id","3_question":"Twitter ID","3_response":"fake_twitter_id","4_question":"Google ID","4_response":"fake_google_id"},"tracking":{"utm_campaign":null,"utm_source":null,"utm_medium":null,"utm_content":null,"utm_term":null,"salesforce_uuid":null},"old_event":null,"old_invitee":null,"new_event":null,"new_invitee":null}}'
    json_bad = '{"event":"invitee.created","time":"2018-03-14T19:16:01Z","payload":{"event":{"uuid":"BBBBBBBBBBBBBBBB","assigned_to":["Jane Sample Data"],"extended_assigned_to":[{"name":"Jane Sample Data","email":"user@example.com","primary":false}],"start_time":"2018-03-14T12:00:00Z","start_time_pretty":"12:00pm - Wednesday, March 14, 2018","invitee_start_time":"2018-03-14T12:00:00Z","invitee_start_time_pretty":"12:00pm - Wednesday, March 14, 2018","end_time":"2018-03-14T12:15:00Z","end_time_pretty":"12:15pm - Wednesday, March 14, 2018","invitee_end_time":"2018-03-14T12:15:00Z","invitee_end_time_pretty":"12:15pm - Wednesday, March 14, 2018","created_at":"2018-03-14T00:00:00Z","location":"The Coffee Shop","canceled":false,"canceler_name":null,"cancel_reason":null,"canceled_at":null},"invitee":{"uuid":"AAAAAAAAAAAAAAAA","first_name":"Joe","last_name":"Sample Data","name":"Joe Sample Data","email":"not.a.real.email@example.com","text_reminder_number":"+14045551234","timezone":"UTC","created_at":"2018-03-14T00:00:00Z","is_reschedule":false,"payments":[{"id":"ch_AAAAAAAAAAAAAAAAAAAAAAAA","provider":"stripe","amount":1234.56,"currency":"USD","terms":"sample terms of payment (up to 1,024 characters)","successful":true}],"canceled":false,"canceler_name":null,"cancel_reason":null,"canceled_at":null},"questions_and_answers":[{"question":"Skype ID","answer":"fake_skype_id"},{"question":"Facebook ID","answer":"fake_facebook_id"},{"question":"Twitter ID","answer":"fake_twitter_id"},{"question":"Google ID","answer":"fake_google_id"}],"questions_and_responses":{"1_question":"Skype ID","1_response":"fake_skype_id","2_question":"Facebook ID","2_response":"fake_facebook_id","3_question":"Twitter ID","3_response":"fake_twitter_id","4_question":"Google ID","4_response":"fake_google_id"},"tracking":{"utm_campaign":null,"utm_source":null,"utm_medium":null,"utm_content":null,"utm_term":null,"salesforce_uuid":null},"old_event":null,"old_invitee":null,"new_event":null,"new_invitee":null}}'

    def setUp(self):
        user = User.objects.create_superuser("approval", "approval@localhost", "approval")
        config.APPROVAL_USER_ID = user.pk

    def test_notoken(self):
        response = self.client.post(reverse('webhook_post'), data=self.json_create, content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_create(self):
        response = self.client.post(reverse('webhook_post')+'?token='+config.WEBHOOK_TOKEN, data=self.json_create, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        objs = Booking.objects.all()
        self.assertEqual(len(objs), 1)
        values = {
            'event_type_id':'CCCCCCCCCCCCCCCC',
            'email':'not.a.real.email@example.com',
            'spot_start':parse_datetime('2018-03-14T12:00:00Z'),
            'spot_end':parse_datetime('2018-03-14T12:15:00Z'),
            'booked_at':parse_datetime('2018-03-14T00:00:00Z'),
        }
        for k in values:
            self.assertEqual(getattr(objs[0], k), values[k])

        self.assertEqual(objs[0].calendly_data.calendly_uuid, 'AAAAAAAAAAAAAAAA')
        self.assertEqual(objs[0].calendly_data.payload, json.loads(self.json_create)['payload'])

    def test_create_conflict(self):
        response = self.client.post(reverse('webhook_post')+'?token='+config.WEBHOOK_TOKEN, data=self.json_create, content_type='application/json')
        response2 = self.client.post(reverse('webhook_post')+'?token='+config.WEBHOOK_TOKEN, data=self.json_create, content_type='application/json')
        self.assertEqual(response2.status_code, 409)

    def test_cancel(self):
        self.client.post(reverse('webhook_post')+'?token='+config.WEBHOOK_TOKEN, data=self.json_create, content_type='application/json')
        response = self.client.post(reverse('webhook_post')+'?token='+config.WEBHOOK_TOKEN, data=self.json_cancel, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        objs = Booking.all_objects.all()
        self.assertEqual(len(objs), 1)
        values = {
            'event_type_id':'CCCCCCCCCCCCCCCC',
            'email':'not.a.real.email@example.com',
            'spot_start':parse_datetime('2018-03-14T12:00:00Z'),
            'spot_end':parse_datetime('2018-03-14T12:15:00Z'),
            'booked_at':parse_datetime('2018-03-14T00:00:00Z'),
        }
        for k in values:
            self.assertEqual(getattr(objs[0], k), values[k])
        self.assertIsNotNone(objs[0].cancelled_at)

        self.assertEqual(objs[0].calendly_data.calendly_uuid, 'AAAAAAAAAAAAAAAA')
        self.assertEqual(objs[0].calendly_data.payload, json.loads(self.json_cancel)['payload'])

    def test_cancel_non_existing(self):
        response = self.client.post(reverse('webhook_post')+'?token='+config.WEBHOOK_TOKEN, data=self.json_cancel, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        objs = Booking.all_objects.all()
        self.assertEqual(len(objs), 1)
        values = {
            'event_type_id':'ZZZZZZZZZZZZZZZZ',
            'email':'not.a.real.email@example.com',
            'spot_start':parse_datetime('2018-03-14T12:00:00Z'),
            'spot_end':parse_datetime('2018-03-14T12:15:00Z'),
            'booked_at':parse_datetime('2018-03-14T00:00:00Z'),
        }
        for k in values:
            self.assertEqual(getattr(objs[0], k), values[k])
        self.assertIsNotNone(objs[0].cancelled_at)

        self.assertEqual(objs[0].calendly_data.calendly_uuid, 'AAAAAAAAAAAAAAAA')
        self.assertEqual(objs[0].calendly_data.payload, json.loads(self.json_cancel)['payload'])

    def test_bad_json(self):
        'No event_type object'
        response = self.client.post(reverse('webhook_post')+'?token='+config.WEBHOOK_TOKEN, data=self.json_bad, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_bad_event_type(self):
        response = self.client.post(reverse('webhook_post')+'?token='+config.WEBHOOK_TOKEN, data=self.json_bad.replace('invitee.created', 'invitee.run'), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_bad_event_field(self):
        response = self.client.post(reverse('webhook_post')+'?token='+config.WEBHOOK_TOKEN, data=self.json_bad.replace('"event":"invitee.created",', ''), content_type='application/json')
        self.assertEqual(response.status_code, 400)

def _hookcanceltest_urlopen(request):
    ret = BytesIO(request.data)
    ret.status = 400
    return ret

class HookCancelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='test', email='test@localhost', password='test')
        config.APPROVAL_USER_ID = self.user.id
        self.bc = BookingCalendlyData.objects.create(
            calendly_uuid="1",
            booking=Booking.objects.create(
                email="a@localhost",
                event_type_id="1",
                spot_start="2019-01-01 14:30:00-0400",
                spot_end="2019-01-01 14:40:00-0400",
                approval_status=Booking.APPROVAL_STATUS_NEW,
            ),
        )

    def test_cancel_200(self):
        response = BytesIO(b'')
        response.status = 200

        with patch('urllib.request.urlopen', return_value=response) as urlopen:
            ret = self.bc.calendly_cancel(cancel_reason="", canceled_by="")
            self.assertEqual(ret, True)

    def test_cancel_with_no_by(self):
        with patch('urllib.request.urlopen', _hookcanceltest_urlopen) as urlopen:
            ret = self.bc.calendly_cancel(cancel_reason="", canceled_by="")
            self.assertTrue('"canceled_by": ""' in ret)

    def test_cancel_with_approval_by(self):
        with patch('urllib.request.urlopen', _hookcanceltest_urlopen) as urlopen:
            ret = self.bc.calendly_cancel(cancel_reason="", canceled_by=None)
            self.assertTrue('"canceled_by": "test"' in ret)
