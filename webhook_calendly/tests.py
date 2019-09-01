from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.dateparse import parse_datetime
from django.contrib.admin.models import LogEntry
from constance import config
from unittest.mock import Mock

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

class ApprovalTests(TestCase):
    def setUp(self):
        user = User.objects.create_superuser('approval', 'approval@localhost', 'approval')
        config.APPROVAL_USER_ID = user.pk

        ag1 = ApprovalGroup.objects.create(name="Group 1", approval_type=ApprovalGroup.APPROVAL_TYPE_FIRST_BOOKED)
        ag2 = ApprovalGroup.objects.create(name="Group 2")

        Invitee.objects.create(email="a@localhost", group=ag1)
        Invitee.objects.create(email="b@localhost", group=ag2)

        b = Booking.objects.create(
            event_type_id="1",
            email="a@localhost",
            spot_start="2019-01-01 14:30:00-0400",
            spot_end="2019-01-01 14:40:00-0400",
            approval_status=Booking.APPROVAL_STATUS_DECLINED,
        )
        BookingCalendlyData.objects.create(
            calendly_uuid="1",
            booking=b,
        )
        b.delete()
        # cancelled items should not be included

        BookingCalendlyData.objects.create(
            calendly_uuid="2",
            booking=Booking.objects.create(
                email="a@localhost",
                event_type_id="2",
                spot_start="2019-01-01 14:40:00-0400",
                spot_end="2019-01-01 14:50:00-0400",
                approval_status=Booking.APPROVAL_STATUS_DECLINED,
            ),
        )
        # non_latest item will be omitted

        BookingCalendlyData.objects.create(
            calendly_uuid="3",
            booking=Booking.objects.create(
                email="a@localhost",
                event_type_id="1",
                spot_start="2019-01-01 14:50:00-0400",
                spot_end="2019-01-01 15:00:00-0400",
                approval_status=Booking.APPROVAL_STATUS_DECLINED,
                approval_protected=True,
            ),
        )

        BookingCalendlyData.objects.create(
            calendly_uuid="4",
            booking=Booking.objects.create(
                email="b@localhost",
                event_type_id="1",
                spot_start="2019-01-01 15:00:00-0400",
                spot_end="2019-01-01 15:10:00-0400",
                approval_status=Booking.APPROVAL_STATUS_APPROVED,
            ),
        )

    def test_update_approval_groups(self):
        'Protected booking still needs to be updated'
        email = "a@localhost"
        qs = Booking.objects.filter(email=email)
        # This should not include deleted ones
        ag = Invitee.objects.get(email=email).group
        ag.update_approval_groups(qs)

        self.assertEqual(Booking.objects.filter(email=email, calendly_data__approval_group=ag).count(), 2)

    def test_update_manual_approval_groups(self):
        'Protected booking with manual approval group still needs to be updated'
        email = "a@localhost"
        qs = Booking.objects.filter(email=email)
        # This should not include deleted ones
        ag = Invitee.objects.get(email=email).group
        ag.approval_type = ApprovalGroup.APPROVAL_TYPE_MANUAL
        ag.update_approval_groups(qs)

        self.assertEqual(Booking.objects.filter(email=email, calendly_data__approval_group=ag).count(), 2)

    def test_get_approval_executor_manual(self):
        def _update_approval_groups(bookings):
            self.assertEqual(len(bookings), 2)
            raise GeneratorExit

        ag = ApprovalGroup.objects.get(name="Group 1")
        ag.approval_type = ApprovalGroup.APPROVAL_TYPE_MANUAL

        BookingCalendlyData.objects.create(
            calendly_uuid="5",
            booking=Booking.objects.create(
                email="a@localhost",
                event_type_id="2",
                spot_start="2019-01-01 15:40:00-0400",
                spot_end="2019-01-01 15:50:00-0400",
                approval_status=Booking.APPROVAL_STATUS_NEW,
            ),
        )
        ag.update_approval_groups = _update_approval_groups
        with self.assertRaises(GeneratorExit):
            bookings_approved, bookings_declined = ag.get_approval_executor("2")
            self.assertEqual(len(bookings_approved), 0)
            self.assertEqual(len(bookings_declined), 0)

    def test_get_approval_executor_first_booked(self):
        ag = ApprovalGroup.objects.get(name="Group 1")
        ag.approval_type = ApprovalGroup.APPROVAL_TYPE_FIRST_BOOKED

        Invitee.objects.create(email="aa@localhost", group=ag)

        bc2 = BookingCalendlyData.objects.create(
            calendly_uuid="5",
            booking=Booking.objects.create(
                email="a@localhost",
                event_type_id="2",
                spot_start="2019-01-01 15:40:00-0400",
                spot_end="2019-01-01 15:50:00-0400",
                approval_status=Booking.APPROVAL_STATUS_NEW,
            ),
        )

        bc3 = BookingCalendlyData.objects.create(
            calendly_uuid="6",
            booking=Booking.objects.create(
                email="aa@localhost",
                event_type_id="2",
                spot_start="2019-01-01 10:00:00-0400",
                spot_end="2019-01-01 10:10:00-0400",
                approval_status=Booking.APPROVAL_STATUS_NEW,
            ),
        )
        # spot early, but booked late

        bookings_approved, bookings_declined = ag.get_approval_executor("2")
        self.assertEqual(len(bookings_approved), 1)
        self.assertEqual(len(bookings_declined), 2)
        self.assertEqual(set(bookings_declined), set([bc2.booking, bc3.booking]))

    def test_get_approval_executor_declined(self):
        ag = ApprovalGroup.objects.get(name="Group 1")
        ag.approval_type = ApprovalGroup.APPROVAL_TYPE_DECLINE

        Invitee.objects.create(email="aa@localhost", group=ag)

        bc2 = BookingCalendlyData.objects.create(
            calendly_uuid="5",
            booking=Booking.objects.create(
                email="a@localhost",
                event_type_id="2",
                spot_start="2019-01-01 15:40:00-0400",
                spot_end="2019-01-01 15:50:00-0400",
                approval_status=Booking.APPROVAL_STATUS_NEW,
            ),
        )

        bc3 = BookingCalendlyData.objects.create(
            calendly_uuid="6",
            booking=Booking.objects.create(
                email="aa@localhost",
                event_type_id="2",
                spot_start="2019-01-01 10:00:00-0400",
                spot_end="2019-01-01 10:10:00-0400",
                approval_status=Booking.APPROVAL_STATUS_NEW,
            ),
        )

        bookings_approved, bookings_declined = ag.get_approval_executor("2")
        self.assertEqual(len(bookings_approved), 0)
        self.assertEqual(len(bookings_declined), 3)

    def _execute_approval_init(self):
        ag = ApprovalGroup.objects.get(name="Group 1")
        Invitee.objects.create(email="aa@localhost", group=ag)

        bc2 = BookingCalendlyData.objects.create(
            calendly_uuid="5",
            booking=Booking.objects.create(
                email="a@localhost",
                event_type_id="2",
                spot_start="2019-01-01 15:40:00-0400",
                spot_end="2019-01-01 15:50:00-0400",
                approval_status=Booking.APPROVAL_STATUS_NEW,
            ),
        )

        bc3 = BookingCalendlyData.objects.create(
            calendly_uuid="6",
            booking=Booking.objects.create(
                email="aa@localhost",
                event_type_id="2",
                spot_start="2019-01-01 10:00:00-0400",
                spot_end="2019-01-01 10:10:00-0400",
                approval_status=Booking.APPROVAL_STATUS_NEW,
            ),
        )
        return ag, bc2, bc3

    def _test_execute_approval_meta(self, var, fake):
        ag, bc2, bc3, changed = var
        if changed != None:
            self.assertEqual(changed[0].approval_status, Booking.APPROVAL_STATUS_APPROVED)
            self.assertEqual(changed[1].approval_status, Booking.APPROVAL_STATUS_DECLINED)
            self.assertEqual(changed[0].calendly_data.approval_group, ag)
            self.assertEqual(changed[1].calendly_data.approval_group, ag)

        bc2.refresh_from_db()
        bc3.refresh_from_db()
        if fake:
            self.assertEqual(bc2.booking.approval_status, Booking.APPROVAL_STATUS_NEW)
            self.assertEqual(bc3.booking.approval_status, Booking.APPROVAL_STATUS_NEW)
            self.assertEqual(bc2.approval_group, None)
            self.assertEqual(bc3.approval_group, None)
            self.assertEqual(LogEntry.objects.all().count(), 0)
        else:
            self.assertEqual(bc2.booking.approval_status, Booking.APPROVAL_STATUS_APPROVED)
            self.assertEqual(bc3.booking.approval_status, Booking.APPROVAL_STATUS_DECLINED)
            self.assertEqual(bc2.approval_group, ag)
            self.assertEqual(bc3.approval_group, ag)
            self.assertEqual(LogEntry.objects.all().count(), 2)

    def test_execute_approval_meta(self):
        "approval_group, approval_status (approved/declined) and log_action, returns changed"
        ag, bc2, bc3 = self._execute_approval_init()
        changed = ag.execute_approval([bc2.booking], [bc3.booking], fake=False)
        self._test_execute_approval_meta(var=(ag, bc2, bc3, changed,), fake=False)

    def test_execute_approval_fake(self):
        "make sure fake does not change anything and returns the correct result"
        ag, bc2, bc3 = self._execute_approval_init()
        changed = ag.execute_approval([bc2.booking], [bc3.booking], fake=True)
        self._test_execute_approval_meta(var=(ag, bc2, bc3, changed,), fake=True)

    def _test_execute_approval_protected(self, var, fake):
        ag, bc2, bc3 = var
        changed = ag.execute_approval([bc2.booking], [bc3.booking], fake=fake)
        self.assertEqual(len(changed), 0)

        bc2.refresh_from_db()
        bc3.refresh_from_db()

        self.assertEqual(bc2.booking.approval_status, Booking.APPROVAL_STATUS_NEW)
        self.assertEqual(bc3.booking.approval_status, Booking.APPROVAL_STATUS_NEW)
        self.assertEqual(bc2.approval_group, None)
        self.assertEqual(bc3.approval_group, None)
        self.assertEqual(LogEntry.objects.all().count(), 0)

    def test_execute_approval_protected(self):
        "protected is not touched, and returns correct result"
        ag, bc2, bc3 = self._execute_approval_init()
        bc2.booking.approval_protected = True
        bc3.booking.approval_protected = True
        self._test_execute_approval_protected(var=(ag, bc2, bc3, ), fake=False)

    def test_execute_approval_protected_fake(self):
        "protected is not touched, and returns correct result, in fake"
        ag, bc2, bc3 = self._execute_approval_init()
        bc2.booking.approval_protected = True
        bc3.booking.approval_protected = True
        self._test_execute_approval_protected(var=(ag, bc2, bc3, ), fake=True)

    def test_bc_run_approval_noemail(self):
        "noemail should be untouched"
        bc = BookingCalendlyData.objects.create(
            calendly_uuid="10",
            booking=Booking.objects.create(
                event_type_id="2",
                spot_start="2019-01-01 14:40:00-0400",
                spot_end="2019-01-01 14:50:00-0400",
            ),
        )
        bc.run_approval()
        self.assertEqual(bc.approval_group, None)
        self.assertEqual(bc.booking.approval_status, Booking.APPROVAL_STATUS_NEW)

    def test_bc_run_approval_group_bc2(self):
        ag, bc2, bc3 = self._execute_approval_init()
        bc2.run_approval()
        self._test_execute_approval_meta(var=(ag, bc2, bc3, None,), fake=False)

    def test_bc_run_approval_group_bc3(self):
        ag, bc2, bc3 = self._execute_approval_init()
        bc3.run_approval()
        self._test_execute_approval_meta(var=(ag, bc2, bc3, None,), fake=False)

    def test_bc_run_approval_nogroup_decline(self):
        "APPROVAL_TYPE_DECLINE"
        config.APPROVAL_NO_GROUP_ACTION = ApprovalGroup.APPROVAL_TYPE_DECLINE
        bc = BookingCalendlyData.objects.create(
            calendly_uuid="10",
            booking=Booking.objects.create(
                email="nope@localhost",
                event_type_id="2",
                spot_start="2019-01-01 14:40:00-0400",
                spot_end="2019-01-01 14:50:00-0400",
            ),
        )
        bc.run_approval()
        self.assertEqual(bc.approval_group, None)
        self.assertEqual(bc.booking.approval_status, Booking.APPROVAL_STATUS_DECLINED)

    def test_bc_run_approval_nogroup_manual(self):
        "APPROVAL_TYPE_MANUAL"
        config.APPROVAL_NO_GROUP_ACTION = ApprovalGroup.APPROVAL_TYPE_MANUAL
        bc = BookingCalendlyData.objects.create(
            calendly_uuid="10",
            booking=Booking.objects.create(
                email="nope@localhost",
                event_type_id="2",
                spot_start="2019-01-01 14:40:00-0400",
                spot_end="2019-01-01 14:50:00-0400",
            ),
        )
        bc.run_approval()
        self.assertEqual(bc.approval_group, None)
        self.assertEqual(bc.booking.approval_status, Booking.APPROVAL_STATUS_NEW)


class HookAdminTests(TestCase):
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
