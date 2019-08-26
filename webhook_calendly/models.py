from django.db import models
from bookings.models import Booking
from django.contrib.postgres.fields import JSONField


class ApprovalGroup(models.Model):
    name = models.CharField(max_length=128, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def run_approval(self):
        pass


class Invitee(models.Model):
    email = models.EmailField()
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
