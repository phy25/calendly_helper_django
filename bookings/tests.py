import datetime

from django.test import TestCase, RequestFactory, Client
from django.urls import reverse
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.admin import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.messages import get_messages
from unittest.mock import Mock

from .models import Booking, CancelledBooking
from .admin import BookingAdmin, CancelledBookingAdmin
from .views import student_reports

class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_student_reports(self):
        self.assertTrue(isinstance(student_reports(RequestFactory().get('/')), HttpResponse))

    def test_ping(self):
        response = self.client.get(reverse('ping'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'pong')

class BookingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='test', email='test@localhost', password='test')
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
            cancelled_at="2019-01-01 17:10:00-0400",
        )
        Booking.objects.create(
            event_type_id="2",
            spot_start="2019-01-01 14:50:00-0400",
            spot_end="2019-01-01 15:00:00-0400",
            approval_status=Booking.APPROVAL_STATUS_APPROVED,
            approval_protected=True,
        )

    def test_queryset_and_obj_delete(self):
        self.assertEqual(Booking.objects.count(), 2)
        self.assertEqual(Booking.objects.cancelled().count(), 0)
        self.assertEqual(Booking.all_objects.cancelled().count(), 1)

        Booking.objects.first().delete() # object
        self.assertEqual(Booking.all_objects.active().count(), 1)
        self.assertEqual(Booking.all_objects.cancelled().count(), 2)

        b = Booking.all_objects.cancelled().first()
        b.cancelled_at = None
        b.save()
        self.assertEqual(Booking.all_objects.active().count(), 2)
        self.assertEqual(Booking.all_objects.cancelled().count(), 1)

        Booking.objects.first().hard_delete() # object
        self.assertEqual(Booking.all_objects.active().count(), 1)
        self.assertEqual(Booking.all_objects.cancelled().count(), 1)
        self.assertEqual(CancelledBooking.objects.all().count(), 1)

        CancelledBooking.objects.all().first().delete() # object
        self.assertEqual(Booking.all_objects.active().count(), 1)
        self.assertEqual(Booking.all_objects.cancelled().count(), 0)

    def test_queryset_delete(self):
        self.assertEqual(Booking.objects.count(), 2)
        self.assertEqual(Booking.all_objects.cancelled().count(), 1)
        Booking.objects.delete()
        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(Booking.all_objects.cancelled().count(), 3)

    def test_queryset_hard_delete(self):
        self.assertEqual(Booking.objects.count(), 2)
        self.assertEqual(Booking.all_objects.cancelled().count(), 1)
        Booking.objects.hard_delete()
        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(Booking.all_objects.cancelled().count(), 1)

    def test_cancelled_is_proxy(self):
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
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
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

    def test_admin_actions_fail(self):
        def _message_user(request, message, *args, **kwargs):
            request._test_message = message

        methods = ['approve_and_protect', 'decline_and_protect', 'reset_approval']
        for func_name in methods:
            request = self.factory.post(reverse('admin:bookings_booking_changelist'))
            request.user = self.user
            setattr(request, 'session', {})
            setattr(request, '_messages', FallbackStorage(request))
            queryset = Mock()
            queryset.update = Mock(side_effect=Exception('Boom!'))
            ma = BookingAdmin(Booking, self.site)
            ma.message_user = _message_user
            func = getattr(ma, func_name)
            func(request, queryset)

            self.assertTrue('Boom!' in request._test_message, "{} does not include exception message".format(func_name))

    def test_decline_and_protect(self):
        self.assertEqual(Booking.objects.filter(approval_status=Booking.APPROVAL_STATUS_DECLINED).count(), 1)
        self.assertEqual(Booking.objects.filter(approval_protected=True).count(), 1)

        request = self.factory.post(reverse('admin:bookings_booking_changelist'))
        request.user = self.user
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = Booking.objects.all()
        all_count = queryset.count()
        ma = BookingAdmin(Booking, self.site)
        ma.decline_and_protect(request, queryset)
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
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
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
