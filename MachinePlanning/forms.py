# machineplan/forms.py
from datetime import timezone
from django import forms
from .models import *
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
            'machine_id', 'name', 'machine_type','work_center','status', 
            'manufacturer', 'model_number', 'serial_number',
            'installation_date', 'capacity', 'operational_hours_per_day', 'notes'
        ]
        widgets = {
            'machine_id': forms.TextInput(attrs={'placeholder': 'Enter machine ID'}),
            'name': forms.TextInput(attrs={'placeholder': 'Enter machine name'}),
            'machine_type': forms.Select(attrs={'class': 'form-select'}),
            'work_center': forms.Select(attrs={'class': 'form-select','required': 'required','data-placeholder': 'Select work center'}),
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

# class RoutingForm(forms.ModelForm):
#     class Meta:
#         model = Routing
#         fields = [
#             'name','component','sequence','operation','work_center','setup_time','run_time_per_unit',
#             'skill','employees_needed', 'min_proficiency','notes',
#         ]
#         widgets = {
#             'name': forms.TextInput(attrs={
#                 'class': 'form-control',
#                 'placeholder': 'Enter routing name'
#             }),
#             'component': forms.Select(attrs={'class': 'form-select'}),
#             'operation': forms.Select(attrs={'class': 'form-select'}),
#             'work_center': forms.Select(attrs={'class': 'form-select'}),
#             'sequence': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'min': 1
#             }),
#             'setup_time': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'min': 0,
#                 'step': 1
#             }),
#             'run_time_per_unit': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'min': 0,
#                 'step': 1
#             }),
#             'skill': forms.Select(attrs={'class': 'form-select'}),
#             'employees_needed': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'min': 1,
#                 'step': 1
#             }),
#             'min_proficiency': forms.Select(attrs={'class': 'form-select'}),
#             'notes': forms.Textarea(attrs={
#                 'class': 'form-control',
#                 'rows': 3,
#                 'placeholder': 'Enter any additional notes...'
#             }),
#         }
#         labels = {
#             'run_time_per_unit': 'Run Time (min/unit)',
#             'employees_needed': 'Employees Needed',
#             'skill': 'Required Skill',
#             'min_proficiency': 'Minimum Proficiency',
#         }

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)


class MachinePlanningForm(forms.ModelForm):
    class Meta:
        model = MachinePlanning
        fields = '__all__'
        widgets = {
            'production_order': forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': 'Select Production Order'
            }),
            'component': forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': 'Select BOM Component'
            }),
            'operation': forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': 'Select Operation'
            }),
            'machine': forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': 'Select Machine'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'scheduled_start': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control datetimepicker'
            }),
            'scheduled_end': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control datetimepicker'
            }),
            'actual_start': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control datetimepicker'
            }),
            'actual_end': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control datetimepicker'
            }),
        }
        labels = {
            'component': 'BOM Component'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial datetime values
        if not self.instance.pk:
            now = timezone.now()
            self.initial['scheduled_start'] = now.strftime('%Y-%m-%dT%H:%M')
            self.initial['scheduled_end'] = (now + timezone.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
        
        # Add form-control class to all fields
        for field in self.fields:
            if 'class' not in self.fields[field].widget.attrs:
                self.fields[field].widget.attrs['class'] = 'form-control'


class OperationForm(forms.ModelForm):
    class Meta:
        model = Operation
        fields = ['code', 'name', 'description']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter operation code'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter operation name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter description...'
            }),
        }

class WorkCenterForm(forms.ModelForm):
    class Meta:
        model = WorkCenters
        fields = ['code', 'name', 'description']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter work center code'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter work center name'
            }),
            # 'workstation': forms.Select(attrs={
            #     'class': 'form-select',
            #     'id': 'workstation-select'  # Add ID for easy targeting
            # }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter description...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # You can customize the queryset for workstation if needed
        # self.fields['workstation'].queryset = WorkStation.objects.all()

class MachineSchedulingForm(forms.ModelForm):
    class Meta:
        model = MachineScheduling
        fields = ['production_order', 'component', 'routing', 'machine', 
                 'scheduled_start', 'scheduled_end', 'status', 'notes', 'seq']
        widgets = {
            'scheduled_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'scheduled_end': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'seq': forms.HiddenInput(), 
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set classes for all fields
        for field_name, field in self.fields.items():
            if field_name not in self.Meta.widgets:
                field.widget.attrs.update({'class': 'form-control'})
        
        # Filter routings based on selected component
        if 'component' in self.data:
            try:
                component_id = int(self.data.get('component'))
                self.fields['routing'].queryset = RoutingMaster.objects.filter(component_id=component_id).order_by('sequence')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['routing'].queryset = self.instance.component.routing_set.order_by('sequence')
        else:
            self.fields['routing'].queryset = RoutingMaster.objects.none()
        
        # Filter machines based on work center from routing
        if 'routing' in self.data:
            try:
                routing_id = int(self.data.get('routing'))
                routing = RoutingMaster.objects.get(id=routing_id)
                self.fields['machine'].queryset = Machine.objects.filter(
                    work_center=routing.work_center
                )
            except (ValueError, TypeError, RoutingMaster.DoesNotExist):
                pass
        elif self.instance.pk and self.instance.routing:
            self.fields['machine'].queryset = Machine.objects.filter(
                work_center=self.instance.routing.work_center
            )
        else:
            self.fields['machine'].queryset = Machine.objects.none()

class MachineTrackingForm(forms.ModelForm):
    class Meta:
        model = MachineScheduling
        fields = ['production_order', 'component', 'routing', 'machine', 
                 'scheduled_start', 'scheduled_end', 'status','actual_start','actual_end','notes']
        widgets = {
            'scheduled_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'scheduled_end': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'actual_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'actual_end': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set classes for all fields
        for field_name, field in self.fields.items():
            if field_name not in self.Meta.widgets:
                field.widget.attrs.update({'class': 'form-control'})
        
        # Filter routings based on selected component
        if 'component' in self.data:
            try:
                component_id = int(self.data.get('component'))
                self.fields['routing'].queryset = RoutingMaster.objects.filter(component_id=component_id).order_by('sequence')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['routing'].queryset = self.instance.component.routing_set.order_by('sequence')
        else:
            self.fields['routing'].queryset = RoutingMaster.objects.none()
        
        # Filter machines based on work center from routing
        if 'routing' in self.data:
            try:
                routing_id = int(self.data.get('routing'))
                routing = RoutingMaster.objects.get(id=routing_id)
                self.fields['machine'].queryset = Machine.objects.filter(
                    work_center=routing.work_center
                )
            except (ValueError, TypeError, RoutingMaster.DoesNotExist):
                pass
        elif self.instance.pk and self.instance.routing:
            self.fields['machine'].queryset = Machine.objects.filter(
                work_center=self.instance.routing.work_center
            )
        else:
            self.fields['machine'].queryset = Machine.objects.none()

class MachineScheduleForm(forms.ModelForm):
    class Meta:
        model = MachineSchedule
        fields = [
            'name',
            'production_order',
            'component',
            'scheduled_start',
            'scheduled_end',
            'actual_start',
            'actual_end',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Schedule Name'}),
            'production_order': forms.Select(attrs={'class': 'form-select'}),
            'component': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_start': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'scheduled_end': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'actual_start': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'actual_end': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }


# --- Detail Form ---
class MachineScheduleDetailForm(forms.ModelForm):
    class Meta:
        model = MachineScheduleDetail
        fields = [
            'seq',
            'routing',
            'machine',
            'work_center',
            'employee',
            'shift',
            'hours_allocated',
            'scheduled_start',
            'scheduled_end',
            'actual_start',
            'actual_end',
            'status',
            'notes',
        ]
        widgets = {
            'seq': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Sequence'}),
            'routing': forms.Select(attrs={'class': 'form-select'}),
            'machine': forms.Select(attrs={'class': 'form-select'}),
            'work_center': forms.Select(attrs={'class': 'form-select'}),
            'employee': forms.Select(attrs={'class': 'form-select'}),   # dropdown looks better
            'shift': forms.Select(attrs={'class': 'form-select'}),
            'hours_allocated': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Hours'}),
            'scheduled_start': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'scheduled_end': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'actual_start': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'actual_end': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Add notes...'}),
        }


# --- Inline Formset for Detail Rows ---
MachineScheduleDetailFormSet = forms.inlineformset_factory(
    MachineSchedule,
    MachineScheduleDetail,
    form=MachineScheduleDetailForm,
    extra=1,
    can_delete=True
)

# class WorkStationForm(forms.ModelForm):
#     class Meta:
#         model = WorkStation
#         fields = ['name', 'machine', 'employee']
#         widgets = {'name': forms.TextInput(attrs={'class': 'form-control','placeholder': 'Enter workstation name'}),
#                    'machine': forms.Select(attrs={'class': 'form-select'}),
#                    'employee': forms.Select(attrs={'class': 'form-select'}),
#         }
#         labels = {
#             'name': 'WorkStation Name',
#             'machine': 'Machine',
#             'employee': 'Assigned Employee',
#         }

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
        
#         # Add form-control class to all fields automatically
#         for field_name, field in self.fields.items():
#             if field.widget.attrs.get('class'):
#                 field.widget.attrs['class'] += ' form-control'
#             else:
#                 field.widget.attrs['class'] = 'form-control'
            
#             # Add placeholder for text fields
#             if isinstance(field.widget, forms.TextInput):
#                 field.widget.attrs['placeholder'] = f'Enter {field.label.lower()}'

#     def clean(self):
#         cleaned_data = super().clean()
#         machine = cleaned_data.get('machine')
#         employee = cleaned_data.get('employee')

#         # Check for unique_together constraint
#         if machine and employee:
#             existing = WorkStation.objects.filter(
#                 machine=machine, 
#                 employee=employee
#             )
            
#             # If updating, exclude current instance
#             if self.instance.pk:
#                 existing = existing.exclude(pk=self.instance.pk)
            
#             if existing.exists():
#                 raise forms.ValidationError(
#                     'This employee is already assigned to this machine.'
#                 )
        
#         return cleaned_data