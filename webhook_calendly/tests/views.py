from django.test import TestCase, Client
from constance import config

from bookings.models import Booking
from .models import ApprovalGroup, Invitee, BookingCalendlyData


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

    def test_declined_count(self):
        config.SHOW_DECLINED_COUNT_FRONTEND = True
        response = self.client.get(reverse('student_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['groups_list']), 1)
        self.assertEqual(response.context['declined_bookings_count'], 1)

    def test_hide_declined_count(self):
        config.SHOW_DECLINED_COUNT_FRONTEND = False
        response = self.client.get(reverse('student_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['groups_list']), 1)
        self.assertEqual(response.context['declined_bookings_count'], 0)

    def test_default_event_type_id(self):
        config.DEFAULT_EVENT_TYPE_ID = "2"
        response = self.client.get(reverse('student_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['groups_list']), 0)
        self.assertEqual(response.context['declined_bookings_count'], 1)

    def test_accept_txt(self):
        response = self.client.get(reverse('student_reports'), HTTP_ACCEPT='text/plain')
        self.assertEqual(response.content_type, 'text/plain')
