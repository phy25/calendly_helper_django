import datetime

from django.test import TestCase

from .models import Booking, CancelledBooking


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