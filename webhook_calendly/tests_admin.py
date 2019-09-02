from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.db.models import QuerySet
from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.admin import ModelAdmin, AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from copy import copy
from constance import config
from unittest.mock import Mock

from bookings.models import Booking, CancelledBooking
from .models import ApprovalGroup, Invitee, BookingCalendlyData
from .admin_decorators import admin_link
from .admin import GroupAdmin, InviteeAdmin, CancelledBookingCalendlyInline

def _message_user(request, message, *args, **kwargs):
    request._test_message = message

class TestBookingAdmin(ModelAdmin):
    @admin_link('booking', 'Booking')
    def booking_email(bc, booking):
        return booking.email

class AdminDecoratorTests(TestCase):
    def setUp(self):
        ag1 = ApprovalGroup.objects.create(name="Group 1", approval_type=ApprovalGroup.APPROVAL_TYPE_FIRST_BOOKED)
        Invitee.objects.create(email="a@localhost", group=ag1)
        self.bc = BookingCalendlyData.objects.create(
            calendly_uuid="2",
            booking=Booking.objects.create(
                email="a@localhost",
                event_type_id="2",
                spot_start="2019-01-01 14:40:00-0400",
                spot_end="2019-01-01 14:50:00-0400",
                approval_status=Booking.APPROVAL_STATUS_DECLINED,
            ),
        )
        self.site = AdminSite()

    def test_admin_link(self):
        ma = TestBookingAdmin(Booking, self.site)
        html = ma.booking_email(self.bc)

        self.assertTrue('<a href="' in html)
        self.assertTrue('a@localhost' in html)
        self.assertTrue(reverse('admin:bookings_booking_change', args=(self.bc.booking.pk,)) in html)
        self.assertEqual(ma.booking_email.short_description, 'Booking')
        self.assertEqual(ma.booking_email.allow_tags, True)

    def test_admin_link_empty(self):
        ma = TestBookingAdmin(Booking, self.site)
        bc = copy(self.bc)
        bc.booking = None
        html = ma.booking_email(bc)

        self.assertTrue('-' in html)

class CalendlyAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(
            username='test', email='test@localhost', password='test')
        self.site = AdminSite()
        config.DEFAULT_EVENT_TYPE_ID = "2"
        config.APPROVAL_USER_ID = self.user.id
        ag = ApprovalGroup.objects.create(
            name="Group 1",
        )
        Invitee.objects.create(
            email="a@localhost",
            group=ag,
        )
        BookingCalendlyData.objects.create(
            calendly_uuid="1",
            booking=Booking.objects.create(
                email="a@localhost",
                event_type_id="1",
                spot_start="2019-01-01 14:30:00-0400",
                spot_end="2019-01-01 14:40:00-0400",
                approval_status=Booking.APPROVAL_STATUS_NEW,
            ),
        )

        BookingCalendlyData.objects.create(
            calendly_uuid="2",
            booking=Booking.objects.create(
                email="a@localhost",
                event_type_id="2",
                spot_start="2019-01-01 14:40:00-0400",
                spot_end="2019-01-01 14:50:00-0400",
                approval_status=Booking.APPROVAL_STATUS_DECLINED,
                booked_at="2019-01-01 9:50:00-0400",
            ),
        )
        BookingCalendlyData.objects.create(
            calendly_uuid="3",
            booking=Booking.objects.create(
                email="a@localhost",
                event_type_id="2",
                spot_start="2019-01-01 14:50:00-0400",
                spot_end="2019-01-01 15:00:00-0400",
                approval_status=Booking.APPROVAL_STATUS_NEW,
                booked_at="2019-01-01 10:00:00-0400",
            ),
        )

    def test_execute_approval(self):
        request = self.factory.post(reverse('admin:webhook_calendly_approvalgroup_changelist'))
        request.user = self.user
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = ApprovalGroup.objects.all()
        ma = GroupAdmin(ApprovalGroup, self.site)
        ma.message_user = _message_user
        ma.execute_approval(request, queryset)
        bookings = Booking.objects.filter(event_type_id="2").order_by('booked_at')
        self.assertEqual(bookings[0].approval_status, Booking.APPROVAL_STATUS_APPROVED)
        self.assertEqual(bookings[1].approval_status, Booking.APPROVAL_STATUS_DECLINED)
        self.assertEqual(
            BookingCalendlyData.objects.get(calendly_uuid="1",).booking.approval_status,
            Booking.APPROVAL_STATUS_NEW
        )
        self.assertTrue('2' in request._test_message)

        self.assertEqual(LogEntry.objects.filter(
            user_id=self.user.id,
            action_flag=CHANGE
        ).count(), 2)

    def test_preview_approval(self):
        request = self.factory.post(reverse('admin:webhook_calendly_approvalgroup_changelist'))
        request.user = self.user
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = ApprovalGroup.objects.all()
        ma = GroupAdmin(ApprovalGroup, self.site)
        ma.message_user = _message_user
        ma.preview_approval(request, queryset)
        bookings = Booking.objects.filter(event_type_id="2").order_by('booked_at')
        self.assertEqual(bookings[0].approval_status, Booking.APPROVAL_STATUS_DECLINED)
        self.assertEqual(bookings[1].approval_status, Booking.APPROVAL_STATUS_NEW)
        self.assertEqual(
            BookingCalendlyData.objects.get(calendly_uuid="1",).booking.approval_status,
            Booking.APPROVAL_STATUS_NEW
        )
        self.assertTrue('2' in request._test_message)

        self.assertEqual(LogEntry.objects.filter(
            user_id=self.user.id,
            action_flag=CHANGE
        ).count(), 0)

    def test_admin_actions_fail(self):
        methods = ['execute_approval', 'preview_approval']
        for func_name in methods:
            request = self.factory.post("/")
            request.user = self.user
            setattr(request, 'session', {})
            setattr(request, '_messages', FallbackStorage(request))
            grp = Mock()
            grp.get_approval_executor = Mock(side_effect=Exception('Boom!'))
            queryset = [grp]
            ma = GroupAdmin(ApprovalGroup, self.site)
            ma.message_user = _message_user
            func = getattr(ma, func_name)
            func(request, queryset)
            self.assertTrue('Boom!' in request._test_message, "{} does not include exception message".format(func_name))

    def test_group_queryset(self):
        site = AdminSite()
        ma = GroupAdmin(ApprovalGroup, site)
        request = self.factory.get('/')
        request.user = self.user
        self.assertTrue(isinstance(ma.get_queryset(request), QuerySet))

    def test_invitee_queryset(self):
        site = AdminSite()
        ma = InviteeAdmin(Invitee, site)
        request = self.factory.get('/')
        request.user = self.user
        self.assertTrue(isinstance(ma.get_queryset(request), QuerySet))

class CancelledBookingCalendlyInlineTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(
            username='test', email='test@localhost', password='test')
        self.site = AdminSite()

    def test_permission(self):
        request = self.factory.post(reverse('admin:bookings_booking_changelist'))
        request.user = self.user
        ma = CancelledBookingCalendlyInline(CancelledBooking, self.site)
        self.assertEqual(ma.has_add_permission(request), False)
        self.assertEqual(ma.has_change_permission(request), False)
