# machineplan/forms.py
from django import forms
from .models import Machine, MachineType, MachineCapability, MachineSchedule, MaintenanceSchedule
from BOM.models import BOMHeader, Component
from django.contrib.auth import get_user_model

class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-control'
            if field.required:
                field.widget.attrs['required'] = 'required'
            if 'placeholder' not in field.widget.attrs:
                field.widget.attrs['placeholder'] = field.label

class MachineTypeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = MachineType
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter machine type name'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Enter description'
            }),
        }

class MachineForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Machine
        fields = [
            'machine_id', 'name', 'machine_type', 'status', 
            'manufacturer', 'model_number', 'serial_number',
            'installation_date', 'capacity', 'operational_hours_per_day', 'notes'
        ]
        widgets = {
            'machine_id': forms.TextInput(attrs={'placeholder': 'Enter machine ID'}),
            'name': forms.TextInput(attrs={'placeholder': 'Enter machine name'}),
            'machine_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'manufacturer': forms.TextInput(attrs={'placeholder': 'Enter manufacturer'}),
            'model_number': forms.TextInput(attrs={'placeholder': 'Enter model number'}),
            'serial_number': forms.TextInput(attrs={'placeholder': 'Enter serial number'}),
            'installation_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control datepicker'
            }),
            'capacity': forms.NumberInput(attrs={'placeholder': 'Enter capacity'}),
            'operational_hours_per_day': forms.NumberInput(attrs={
                'placeholder': 'Enter operational hours per day',
                'step': '0.5',
                'min': '0',
                'max': '24'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Enter any additional notes'
            }),
        }

class MachineCapabilityForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = MachineCapability
        fields = ['machine', 'component', 'setup_time', 'processing_time', 'notes']
        widgets = {
            'machine': forms.Select(attrs={'class': 'form-select'}),
            'component': forms.Select(attrs={'class': 'form-select'}),
            'setup_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control timepicker'
            }),
            'processing_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control timepicker'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Enter any additional notes'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['machine'].queryset = Machine.objects.filter(status='OP')
        self.fields['component'].queryset = BOMHeader.objects.all()

class MachineScheduleForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = MachineSchedule
        fields = [
            'machine', 'component', 'quantity', 
            'start_time', 'end_time', 'status', 'notes'
        ]
        widgets = {
            'machine': forms.Select(attrs={'class': 'form-select'}),
            'component': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={
                'placeholder': 'Enter quantity',
                'min': '1'
            }),
            'start_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control datetimepicker'
            }),
            'end_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control datetimepicker'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Enter any additional notes'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['machine'].queryset = Machine.objects.filter(status='OP')
        self.fields['component'].queryset = Component.objects.all()

class MaintenanceScheduleForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = MaintenanceSchedule
        fields = [
            'machine', 'maintenance_type', 'scheduled_date', 
            'actual_date', 'completed', 'technician', 
            'description', 'notes'
        ]
        widgets = {
            'machine': forms.Select(attrs={'class': 'form-select'}),
            'maintenance_type': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control datepicker'
            }),
            'actual_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control datepicker'
            }),
            'completed': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'technician': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Enter maintenance description'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Enter any additional notes'
            }),
        }