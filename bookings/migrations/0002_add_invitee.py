# Generated by Django 2.2.4 on 2019-08-23 22:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='group',
            name='emails',
        ),
        migrations.AlterField(
            model_name='group',
            name='name',
            field=models.CharField(max_length=128, unique=True),
        ),
        migrations.CreateModel(
            name='Invitee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254)),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='bookings.Group')),
            ],
        ),
    ]