# Generated by Django 4.2.7 on 2025-07-30 12:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('MachinePlan', '0009_routing_production_order'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='machineschedule',
            name='component',
        ),
        migrations.RemoveField(
            model_name='machineschedule',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='machineschedule',
            name='machine',
        ),
    ]
