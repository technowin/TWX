# Generated by Django 4.2.7 on 2025-07-30 12:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('MachinePlan', '0011_delete_machineschedule'),
    ]

    operations = [
        migrations.AddField(
            model_name='machineplanning',
            name='routing',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='MachinePlan.routing'),
        ),
    ]
