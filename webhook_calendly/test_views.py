from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from constance import config

from bookings.models import Booking
from .models import ApprovalGroup, Invitee, BookingCalendlyData


class ReportViewTests(TestCase):
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
                event_type_id="2",
                spot_start="2019-01-01 15:40:00-0400",
                spot_end="2019-01-01 15:50:00-0400",
                approval_status=Booking.APPROVAL_STATUS_DECLINED,
            ),
        )

        BookingCalendlyData.objects.create(
            calendly_uuid="5",
            approval_group=ag,
            booking=Booking.objects.create(
                event_type_id="1",
                spot_start="2019-01-01 16:00:00-0400",
                spot_end="2019-01-01 16:10:00-0400",
                approval_status=Booking.APPROVAL_STATUS_APPROVED,
            ),
        )


    def test_stud_declined_count(self):
        config.SHOW_DECLINED_COUNT_FRONTEND = True
        response = self.client.get(reverse('student_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['groups_list']), 1)
        self.assertEqual(response.context['declined_bookings_count'], 1)

    def test_stud_hide_declined_count(self):
        config.SHOW_DECLINED_COUNT_FRONTEND = False
        response = self.client.get(reverse('student_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['groups_list']), 1)
        self.assertEqual(response.context['declined_bookings_count'], 0)

    def test_stud_default_event_type_id(self):
        config.DEFAULT_EVENT_TYPE_ID = "2"
        response = self.client.get(reverse('student_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['groups_list']), 1)
        self.assertEqual(response.context['declined_bookings_count'], 2)

    def test_stud_accept_txt(self):
        response = self.client.get(reverse('student_reports'), HTTP_ACCEPT='text/plain')
        self.assertEqual(response['CONTENT-TYPE'], 'text/plain')

    def test_admin_event_type_id(self):
        client = Client()
        client.force_login(User.objects.create_superuser('test', 'test@localhost', 'test'))
        response = client.get(reverse('admin_reports')+'?event_type_id=2')
        self.assertEqual(response.context['event_type_ids_form'].initial['event_type_id'], "2")
