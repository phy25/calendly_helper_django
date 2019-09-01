from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry
from constance import config

from bookings.models import Booking
from .models import ApprovalGroup, Invitee, BookingCalendlyData


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

    def _test_run_approval_meta(self, var):
        ag, bc2, bc3 = var

        bc2.refresh_from_db()
        bc3.refresh_from_db()
        bc1 = BookingCalendlyData.objects.get(calendly_uuid="2")
        self.assertEqual(bc1.booking.approval_status, Booking.APPROVAL_STATUS_APPROVED)
        self.assertEqual(bc2.booking.approval_status, Booking.APPROVAL_STATUS_DECLINED)
        self.assertEqual(bc3.booking.approval_status, Booking.APPROVAL_STATUS_DECLINED)
        self.assertEqual(bc1.approval_group, ag)
        self.assertEqual(bc2.approval_group, ag)
        self.assertEqual(bc3.approval_group, ag)
        self.assertEqual(LogEntry.objects.all().count(), 3)

    def test_bc_run_approval_group_bc2(self):
        ag, bc2, bc3 = self._execute_approval_init()
        bc2.run_approval()
        self._test_run_approval_meta(var=(ag, bc2, bc3,))

    def test_bc_run_approval_group_bc3(self):
        ag, bc2, bc3 = self._execute_approval_init()
        bc3.run_approval()
        self._test_run_approval_meta(var=(ag, bc2, bc3,))

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
