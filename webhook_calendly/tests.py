from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.dateparse import parse_datetime
from django.contrib.admin.models import LogEntry
from constance import config

from bookings.models import Booking
from .models import ApprovalGroup, Invitee, BookingCalendlyData
import json

class StudentViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        ag = ApprovalGroup.objects.create(
            name="Group",
        )

        b = Booking.objects.create(
            event_type_id="1",
            spot_start="2019-01-01 14:30:00-0400",
            spot_end="2019-01-01 14:40:00-0400",
            approval_status=Booking.APPROVAL_STATUS_DECLINED,
        )
        BookingCalendlyData.objects.create(
            calendly_uuid="1",
            approval_group=ag,
            booking=b,
        )
        b.delete()
        # cancelled items should not be included

        BookingCalendlyData.objects.create(
            calendly_uuid="2",
            approval_group=ag,
            booking=Booking.objects.create(
                event_type_id="2",
                spot_start="2019-01-01 14:40:00-0400",
                spot_end="2019-01-01 14:50:00-0400",
                approval_status=Booking.APPROVAL_STATUS_DECLINED,
            ),
        )
        # non_latest item will be omitted

        BookingCalendlyData.objects.create(
            calendly_uuid="3",
            approval_group=ag,
            booking=Booking.objects.create(
                event_type_id="1",
                spot_start="2019-01-01 14:50:00-0400",
                spot_end="2019-01-01 15:00:00-0400",
                approval_status=Booking.APPROVAL_STATUS_DECLINED,
            ),
        )

        BookingCalendlyData.objects.create(
            calendly_uuid="4",
            approval_group=ag,
            booking=Booking.objects.create(
                event_type_id="1",
                spot_start="2019-01-01 15:00:00-0400",
                spot_end="2019-01-01 15:10:00-0400",
                approval_status=Booking.APPROVAL_STATUS_APPROVED,
            ),
        )

    def test_declinedcount(self):
        config.SHOW_DECLINED_COUNT_FRONTEND = True
        response = self.client.get(reverse('student_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['groups_list']), 1)
        self.assertEqual(response.context['declined_bookings_count'], 1)

    def test_hidedeclinedcount(self):
        config.SHOW_DECLINED_COUNT_FRONTEND = False
        response = self.client.get(reverse('student_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['groups_list']), 1)
        self.assertEqual(response.context['declined_bookings_count'], 0)

class HookAdminTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser("test", "test@localhost", "test")

    def tearDown(self):
        self.user.delete()
        LogEntry.objects.all().delete()

    def test_redirect(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('admin:webhook_calendly_hook_changelist'), follow=True)

        self.assertEqual(response.status_code, 400) # No token has been set up yet
        self.assertTrue(reverse('list_hooks') in response.redirect_chain[0][0])

class HookPostTest(TestCase):
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
