from django.db import models, transaction
from bookings.models import Booking
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from constance import config


class ApprovalGroup(models.Model):
    name = models.CharField(max_length=128, unique=True)

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
        bookings = list(Booking.objects.filter(
            event_type_id=event_type_id,
            email__in=invitees_email
            ).order_by('booked_at'))
            # force getting all

        # 2 - decide
        bookings_approved = bookings[0:1] # keep first booked
        bookings_declined = bookings[1:]
        return bookings_approved, bookings_declined

    def execute_approval_qs(self, approved, declined):
        content_type_id = ContentType.objects.get_for_model(Booking).pk

        # 3 - submit change
        # 4 - insert logs
        with transaction.atomic():
            for b in approved:
                b.approval_status = Booking.APPROVAL_STATUS_APPROVED
                b.calendly_data.approval_group = self
                b.calendly_data.save()
                b.save()
                LogEntry.objects.log_action(
                            user_id=config.APPROVAL_USER_ID,
                            content_type_id=content_type_id,
                            object_id=b.pk,
                            object_repr=str(b),
                            change_message="Approved",
                            action_flag=CHANGE)

            for b in declined:
                b.approval_status = Booking.APPROVAL_STATUS_DECLINED
                b.calendly_data.approval_group = self
                b.calendly_data.save()
                b.save()

                LogEntry.objects.log_action(
                            user_id=config.APPROVAL_USER_ID,
                            content_type_id=content_type_id,
                            object_id=b.pk,
                            object_repr=str(b),
                            change_message="Declined",
                            action_flag=CHANGE)


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
                approved_qs, declined_qs = invitee.group.get_approval_executor(self.booking.event_type_id)
                invitee.group.execute_approval_qs(approved_qs, declined_qs)
        except ObjectDoesNotExist:
            # Assume no group, decline
            self.booking.approval_status = Booking.APPROVAL_STATUS_DECLINED
            self.booking.save()
            LogEntry.objects.log_action(
                            user_id=config.APPROVAL_USER_ID,
                            content_type_id=ContentType.objects.get_for_model(self).pk,
                            object_id=self.pk,
                            object_repr=str(self),
                            change_message="Declined (no group)",
                            action_flag=CHANGE)
