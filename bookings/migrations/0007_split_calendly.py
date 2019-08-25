# Generated by Django 2.2.4 on 2019-08-25 18:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0006_booking_calendly_event_type_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='invitee',
            name='group',
        ),
        migrations.RenameField(
            model_name='booking',
            old_name='calendly_event_type_id',
            new_name='event_type_id',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='approved_for_group',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='calendly_data',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='calendly_uuid',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='is_approved',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='is_cancelled',
        ),
        migrations.AddField(
            model_name='booking',
            name='approval_status',
            field=models.CharField(choices=[('NEW', 'New'), ('APPROVED', 'Approved'), ('DECLINED', 'Declined')], default='NEW', max_length=16),
        ),
        migrations.AddField(
            model_name='booking',
            name='cancelled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.DeleteModel(
            name='Group',
        ),
        migrations.DeleteModel(
            name='Invitee',
        ),
    ]
