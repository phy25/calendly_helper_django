# Generated by Django 2.2.4 on 2019-08-27 01:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0008_cancelledbooking'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='approval_protected',
            field=models.BooleanField(default=False),
        ),
    ]