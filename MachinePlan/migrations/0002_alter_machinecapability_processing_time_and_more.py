# Generated by Django 4.2.7 on 2025-07-24 07:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MachinePlan', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='machinecapability',
            name='processing_time',
            field=models.TimeField(help_text='Time required to process one unit'),
        ),
        migrations.AlterField(
            model_name='machinecapability',
            name='setup_time',
            field=models.TimeField(help_text='Time required to setup machine for this component'),
        ),
    ]
