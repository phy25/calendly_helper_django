from django.db import models, transaction
from bookings.models import Booking
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from constance import config


class ApprovalGroup(models.Model):
    name = models.CharField(max_length=128, unique=True)

    APPROVAL_TYPE_FIRST_BOOKED = 'FIRST_BOOKED'
    APPROVAL_TYPE_DECLINE = 'DECLINE'
    APPROVAL_TYPE_MANUAL = 'MANUAL'
    APPROVAL_TYPE_CHOICES = (
        (APPROVAL_TYPE_FIRST_BOOKED, 'First Booked'),
        (APPROVAL_TYPE_DECLINE, 'Decline'),
        (APPROVAL_TYPE_MANUAL, 'Manual'),
    )
    approval_type = models.CharField(default=APPROVAL_TYPE_FIRST_BOOKED, max_length=16,
        choices=APPROVAL_TYPE_CHOICES,)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_approval_executor(self, event_type_id):
        """
        @return QuerySet
        """
        # 1 - get related bookings by email
        invitees_email = [i.email for i in self.invitee_set.only('email').all()]
        bookings = Booking.objects.filter(
            event_type_id=event_type_id,
            email__in=invitees_email
            ).order_by('booked_at')

        # 2 - decide
        if self.approval_type == ApprovalGroup.APPROVAL_TYPE_MANUAL:
            bookings_approved = []
            bookings_declined = []
            self.update_approval_groups(bookings)
        else:
            bookings = list(bookings)
            # force getting all

        if self.approval_type == ApprovalGroup.APPROVAL_TYPE_DECLINE:
            bookings_approved = []
            bookings_declined = bookings
        if self.approval_type == ApprovalGroup.APPROVAL_TYPE_FIRST_BOOKED:
            bookings_approved = bookings[0:1] # keep first booked
            bookings_declined = bookings[1:]
        return bookings_approved, bookings_declined

    def update_approval_groups(self, qs):
        return qs.update(approval_group=self)

    def execute_approval(self, approved, declined, fake=False):
        content_type_id = ContentType.objects.get_for_model(Booking).pk
        changed = []

        # 3 - submit change
        # 4 - insert logs
        if fake:
            for b in approved:
                if b.approval_protected:
                    continue
                if b.approval_status != Booking.APPROVAL_STATUS_APPROVED:
                    b.approval_status = Booking.APPROVAL_STATUS_APPROVED
                    changed.append(b)
            for b in declined:
                if b.approval_protected:
                    continue
                if b.approval_status != Booking.APPROVAL_STATUS_DECLINED:
                    b.approval_status = Booking.APPROVAL_STATUS_DECLINED
                    changed.append(b)
        else:
            with transaction.atomic():
                for b in approved:
                    # check if it's protected or not
                    if b.approval_protected:
                        continue
                    b.calendly_data.approval_group = self
                    b.calendly_data.save()
                    if b.approval_status != Booking.APPROVAL_STATUS_APPROVED:
                        b.approval_status = Booking.APPROVAL_STATUS_APPROVED
                        b.save()
                        LogEntry.objects.log_action(
                                    user_id=config.APPROVAL_USER_ID,
                                    content_type_id=content_type_id,
                                    object_id=b.pk,
                                    object_repr=str(b),
                                    change_message="Approved",
                                    action_flag=CHANGE)
                        changed.append(b)

                for b in declined:
                    # check if it's protected or not
                    if b.approval_protected:
                        continue
                    b.calendly_data.approval_group = self
                    b.calendly_data.save()
                    if b.approval_status != Booking.APPROVAL_STATUS_DECLINED:
                        b.approval_status = Booking.APPROVAL_STATUS_DECLINED
                        b.save()
                        LogEntry.objects.log_action(
                                    user_id=config.APPROVAL_USER_ID,
                                    content_type_id=content_type_id,
                                    object_id=b.pk,
                                    object_repr=str(b),
                                    change_message="Declined",
                                    action_flag=CHANGE)
                        changed.append(b)

        return changed

class Invitee(models.Model):
    email = models.EmailField(unique=True)
    group = models.ForeignKey(ApprovalGroup, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email


class BookingCalendlyData(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='calendly_data')
    payload = JSONField()
    calendly_uuid = models.CharField(primary_key=True, max_length=32)
    approval_group = models.ForeignKey(ApprovalGroup, on_delete=models.PROTECT, null=True, blank=True, db_index=True)

    def __str__(self):
        return self.calendly_uuid

    def run_approval(self):
        # 1 - find group
        if not self.booking.email:
            return
        try:
            invitee = Invitee.objects.get(email=self.booking.email)
            # 2 - execute by group if it exists
            if invitee.group:
                approved, declined = invitee.group.get_approval_executor(self.booking.event_type_id)
                invitee.group.execute_approval(approved, declined)
        except ObjectDoesNotExist:
            # Assume no group
            if config.APPROVAL_NO_GROUP_ACTION == ApprovalGroup.APPROVAL_TYPE_DECLINE:
                if self.booking.approval_status != Booking.APPROVAL_STATUS_DECLINED:
                    self.booking.approval_status = Booking.APPROVAL_STATUS_DECLINED
                    self.booking.save()
                    LogEntry.objects.log_action(
                                    user_id=config.APPROVAL_USER_ID,
                                    content_type_id=ContentType.objects.get_for_model(self.booking).pk,
                                    object_id=self.booking.pk,
                                    object_repr=str(self.booking),
                                    change_message="Declined (no group)",
                                    action_flag=CHANGE)
