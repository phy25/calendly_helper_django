import datetime

from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.admin import AdminSite

from .models import Booking, CancelledBooking
from .admin import BookingAdmin, CancelledBookingAdmin

class CancelledBookingTests(TestCase):
    def test_deleting_booking(self):
        """
        was_published_recently() returns False for questions whose pub_date
        is in the future.
        """
        b = Booking(spot_start=1, spot_end=2)
        #b.delete()

    def test_is_proxy(self):
        self.assertEqual(CancelledBooking._meta.proxy, True)

class BookingAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(
            username='test', email='test@localhost', password='test')
        self.site = AdminSite()
        Booking.objects.create(
            event_type_id="1",
            spot_start="2019-01-01 14:30:00-0400",
            spot_end="2019-01-01 14:40:00-0400",
            approval_status=Booking.APPROVAL_STATUS_NEW,
        )
        Booking.objects.create(
            event_type_id="2",
            spot_start="2019-01-01 14:40:00-0400",
            spot_end="2019-01-01 14:50:00-0400",
            approval_status=Booking.APPROVAL_STATUS_DECLINED,
        )
        Booking.objects.create(
            event_type_id="2",
            spot_start="2019-01-01 14:50:00-0400",
            spot_end="2019-01-01 15:00:00-0400",
            approval_status=Booking.APPROVAL_STATUS_APPROVED,
            approval_protected=True
        )

    def test_approve_and_protect(self):
        self.assertEqual(Booking.objects.filter(approval_status=Booking.APPROVAL_STATUS_APPROVED).count(), 1)
        self.assertEqual(Booking.objects.filter(approval_protected=True).count(), 1)

        request = self.factory.post(reverse('admin:bookings_booking_changelist'))
        request.user = self.user
        queryset = Booking.objects.all()
        all_count = queryset.count()
        ma = BookingAdmin(Booking, self.site)
        ma.approve_and_protect(request, queryset)
        self.assertEqual(Booking.objects.filter(approval_status=Booking.APPROVAL_STATUS_APPROVED).count(), all_count)
        self.assertEqual(Booking.objects.filter(approval_protected=True).count(), all_count)

        self.assertEqual(LogEntry.objects.filter(
            user_id=self.user.id,
            content_type_id=ma.get_content_type_id(),
            action_flag=CHANGE
        ).count(), all_count)

    def test_decline_and_protect(self):
        self.assertEqual(Booking.objects.filter(approval_status=Booking.APPROVAL_STATUS_DECLINED).count(), 1)
        self.assertEqual(Booking.objects.filter(approval_protected=True).count(), 1)

        request = self.factory.post(reverse('admin:bookings_booking_changelist'))
        request.user = self.user
        queryset = Booking.objects.all()
        all_count = queryset.count()
        ma = BookingAdmin(Booking, self.site)
        ma.approve_and_protect(request, queryset)
        self.assertEqual(Booking.objects.filter(approval_status=Booking.APPROVAL_STATUS_DECLINED).count(), all_count)
        self.assertEqual(Booking.objects.filter(approval_protected=True).count(), all_count)

        self.assertEqual(LogEntry.objects.filter(
            user_id=self.user.id,
            content_type_id=ma.get_content_type_id(),
            action_flag=CHANGE
        ).count(), all_count)

    def test_reset_approval(self):
        self.assertEqual(Booking.objects.filter(approval_status=Booking.APPROVAL_STATUS_NEW).count(), 1)
        self.assertEqual(Booking.objects.filter(approval_protected=True).count(), 1)

        request = self.factory.post(reverse('admin:bookings_booking_changelist'))
        request.user = self.user
        queryset = Booking.objects.all()
        all_count = queryset.count()
        ma = BookingAdmin(Booking, self.site)
        ma.reset_approval(request, queryset)
        self.assertEqual(Booking.objects.filter(approval_status=Booking.APPROVAL_STATUS_NEW).count(), all_count)
        self.assertEqual(Booking.objects.filter(approval_protected=True).count(), 0)

        self.assertEqual(LogEntry.objects.filter(
            user_id=self.user.id,
            content_type_id=ma.get_content_type_id(),
            action_flag=CHANGE
        ).count(), all_count)

class CancelledBookingAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(
            username='test', email='test@localhost', password='test')
        self.site = AdminSite()

    def test_add_permission(self):
        request = self.factory.post(reverse('admin:bookings_booking_changelist'))
        request.user = self.user
        ma = CancelledBookingAdmin(CancelledBooking, self.site)
        self.assertEqual(ma.has_add_permission(request), False)

    def test_count_readonly(self):
        request = self.factory.post(reverse('admin:bookings_booking_changelist'))
        request.user = self.user
        ma = CancelledBookingAdmin(CancelledBooking, self.site)
        f = ma.get_readonly_fields(request)
        self.assertGreater(len(f), 0)
        self.assertTrue('cancelled_at' not in f)
