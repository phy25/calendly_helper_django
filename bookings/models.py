from django.db import models
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from django.utils.translation import ugettext as translate

# Create your models here.

class Group(models.Model):
    name = models.CharField(max_length=128, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Invitee(models.Model):
    email = models.EmailField()
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email


class Booking(models.Model):
    email = models.EmailField(null=False, blank=True)
    spot_start = models.DateTimeField()
    spot_end = models.DateTimeField()
    booked_at = models.DateTimeField(default=timezone.now)
    is_approved = models.BooleanField(default=False)
    approved_for_group = models.ForeignKey(Group, on_delete=models.PROTECT, null=True, blank=True, db_index=True)
    is_cancelled = models.BooleanField(default=False)
    calendly_data = JSONField()
    calendly_uuid = models.CharField(max_length=32, default='', unique=True)

    created_at = models.DateTimeField(
        verbose_name=translate('Created at'),
        unique=False,
        null=True,
        blank=True,
        db_index=True,
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        verbose_name=translate('Updated at'),
        unique=False,
        null=True,
        blank=True,
        db_index=True,
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.calendly_uuid if self.calendly_uuid else str(self.spot_start)