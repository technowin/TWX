# Generated by Django 3.2.25 on 2025-07-15 10:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Workflow', '0026_workflow_master'),
    ]

    operations = [
        migrations.AddField(
            model_name='workflow_matrix',
            name='wf_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
