from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext as translate


class BookingSoftDeletionManager(models.Manager):
    def __init__(self, *args, **kwargs):
        self.active_only = kwargs.pop('active_only', True)
        self.cancelled_only = kwargs.pop('cancelled_only', False)
        super(BookingSoftDeletionManager, self).__init__(*args, **kwargs)

    def get_queryset(self):
        if self.active_only:
            return BookingSoftDeletionQuerySet(self.model).filter(cancelled_at=None)
        if self.cancelled_only:
            return models.QuerySet(self.model).exclude(cancelled_at=None)
        return BookingSoftDeletionQuerySet(self.model)

    def hard_delete(self):
        return self.get_queryset().hard_delete()


class BookingSoftDeletionQuerySet(models.QuerySet):
    def delete(self):
        return super(BookingSoftDeletionQuerySet, self).update(cancelled_at=timezone.now())

    def hard_delete(self):
        return super(BookingSoftDeletionQuerySet, self).delete()

    def active(self):
        return self.filter(cancelled_at=None)

    def cancelled(self):
        return self.filter(~models.Q(cancelled_at=None))


class Booking(models.Model):
    objects = BookingSoftDeletionManager.from_queryset(BookingSoftDeletionQuerySet)()
    all_objects = BookingSoftDeletionManager.from_queryset(BookingSoftDeletionQuerySet)(active_only=False)

    event_type_id = models.CharField(max_length=32, default='', db_index=True)
    email = models.EmailField(null=False, blank=True)
    spot_start = models.DateTimeField()
    spot_end = models.DateTimeField()
    booked_at = models.DateTimeField(default=timezone.now)

    APPROVAL_STATUS_NEW = 'NEW'
    APPROVAL_STATUS_APPROVED = 'APPROVED'
    APPROVAL_STATUS_DECLINED = 'DECLINED'
    APPROVAL_STATUS_CHOICES = (
        (APPROVAL_STATUS_NEW, 'New'),
        (APPROVAL_STATUS_APPROVED, 'Approved'),
        (APPROVAL_STATUS_DECLINED, 'Declined'),
    )
    approval_status = models.CharField(default=APPROVAL_STATUS_NEW, max_length=16,
        choices=APPROVAL_STATUS_CHOICES,)
    approval_protected = models.BooleanField(default=False)

    cancelled_at = models.DateTimeField(blank=True, null=True)

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

    def delete(self):
        self.cancelled_at = timezone.now()
        self.save()

    def hard_delete(self):
        super(Booking, self).delete()

    def __str__(self):
        return 'Booking #'+str(self.id)

class CancelledBooking(Booking):
    objects = BookingSoftDeletionManager(active_only=False, cancelled_only=True)

    class Meta:
        proxy = True
        verbose_name = 'Cancelled Booking'
        verbose_name_plural = 'Cancelled Bookings'

    def delete(self):
        super(CancelledBooking, self).hard_delete()
