from django.test import TestCase
from django.urls import reverse
from django.contrib.admin import ModelAdmin, AdminSite
from copy import copy

from bookings.models import Booking
from .models import ApprovalGroup, Invitee, BookingCalendlyData
from .admin_decorators import admin_link

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
