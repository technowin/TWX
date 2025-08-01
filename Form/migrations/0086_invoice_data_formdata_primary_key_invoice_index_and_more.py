# Generated by Django 4.2.7 on 2025-07-17 06:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Form', '0085_modulemaster_form_module_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='invoice_data',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.TextField(blank=True, null=True)),
                ('file_ref', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('created_by', models.TextField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('updated_by', models.TextField(blank=True, null=True)),
                ('field', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='field_invoice_value_id', to='Form.formfield')),
                ('form', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='form_invoice_data', to='Form.form')),
            ],
            options={
                'db_table': 'invoice_data',
            },
        ),
        migrations.AddField(
            model_name='formdata',
            name='primary_key',
            field=models.TextField(null=True),
        ),
        migrations.CreateModel(
            name='invoice_index',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('primary_key', models.TextField(null=True)),
                ('req_no', models.TextField(blank=True, null=True)),
                ('file_ref', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('created_by', models.TextField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('updated_by', models.TextField(blank=True, null=True)),
                ('action', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='form_invoice_action_id', to='Form.formaction')),
                ('form', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='form_invoice_data_id', to='Form.form')),
            ],
            options={
                'db_table': 'invoice_index',
            },
        ),
        migrations.CreateModel(
            name='invoice_file',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_name', models.TextField(blank=True, null=True)),
                ('uploaded_name', models.TextField(blank=True, null=True)),
                ('file_path', models.TextField(blank=True, null=True)),
                ('file_size', models.TextField(blank=True, null=True)),
                ('num_pages', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('created_by', models.TextField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('updated_by', models.TextField(blank=True, null=True)),
                ('field', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='field_invoice_file_id', to='Form.formfield')),
                ('file', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='file_invoice_id', to='Form.invoice_data')),
                ('form', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='form_invoice_filr_id', to='Form.form')),
                ('form_data', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='form_invoice_data_id', to='Form.invoice_index')),
            ],
            options={
                'db_table': 'invoice_file',
            },
        ),
        migrations.AddField(
            model_name='invoice_data',
            name='form_data',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='form_invoice_value_id', to='Form.invoice_index'),
        ),
        migrations.CreateModel(
            name='invoice_action',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.TextField(blank=True, null=True)),
                ('step_id', models.IntegerField(blank=True, null=True)),
                ('version', models.FloatField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('created_by', models.TextField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('updated_by', models.TextField(blank=True, null=True)),
                ('field', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='action_invoice_field_id', to='Form.formactionfield')),
                ('form_data', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='action_invoice_data_id', to='Form.invoice_index')),
            ],
            options={
                'db_table': 'invoice_action',
            },
        ),
    ]
