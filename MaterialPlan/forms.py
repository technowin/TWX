# forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    MaterialPlan, MaterialPlanItem, PurchaseRequisition,
    ProductionOrder, MaterialShortageAlert
)
from BOM.models import BOMHeader, Component

class BootstrapFormMixin:
    """Mixin to add Bootstrap 5 styling to form fields"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-control'
                
            if field.help_text:
                field.widget.attrs['class'] += ' form-help'
                field.widget.attrs['data-bs-toggle'] = 'tooltip'
                field.widget.attrs['data-bs-placement'] = 'top'
                field.widget.attrs['title'] = field.help_text
                
            if field.required:
                field.widget.attrs['required'] = 'required'
                field.label = f'{field.label} *'

class MaterialPlanForm(BootstrapFormMixin, forms.ModelForm):
    bom = forms.ModelChoiceField(
        queryset=BOMHeader.objects.filter(status='approved'),
        label="BOM Version",
        help_text="Select an approved Bill of Materials version for this plan"
    )
    
    class Meta:
        model = MaterialPlan
        fields = [
            'name', 'description', 'sales_order_reference',
            'bom', 'quantity', 'due_date'
        ]
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'name': forms.TextInput(attrs={'placeholder': 'Enter plan name'}),
            'quantity': forms.NumberInput(attrs={'min': 1}),
        }
        help_texts = {
            'name': 'A descriptive name for this material plan',
            'description': 'Optional details about this material plan',
            'sales_order_reference': 'Reference to related sales order if applicable',
            'quantity': 'Total quantity of products to be manufactured',
            'due_date': 'When the materials are needed for production',
        }
    
    def clean_due_date(self):
        due_date = self.cleaned_data['due_date']
        if due_date < timezone.now().date():
            raise ValidationError("Due date cannot be in the past.")
        if due_date > timezone.now().date() + timezone.timedelta(days=365):
            raise ValidationError("Due date cannot be more than 1 year in the future.")
        return due_date
    
    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        return quantity


class MaterialPlanItemForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = MaterialPlanItem
        fields = [
            'quantity_to_purchase', 'quantity_to_produce',
            'required_date', 'supplier', 'notes'
        ]
        widgets = {
            'required_date': forms.DateInput(attrs={'type': 'date'}),
            'quantity_to_purchase': forms.NumberInput(attrs={'min': 0}),
            'quantity_to_produce': forms.NumberInput(attrs={'min': 0}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Additional notes'}),
        }
        help_texts = {
            'quantity_to_purchase': 'Amount of this material to purchase',
            'quantity_to_produce': 'Amount of this material to produce internally',
            'required_date': 'When this specific material is needed',
            'supplier': 'Preferred supplier for this material',
            'notes': 'Any special instructions for this material',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        quantity_to_purchase = cleaned_data.get('quantity_to_purchase', 0)
        quantity_to_produce = cleaned_data.get('quantity_to_produce', 0)
        
        if quantity_to_purchase <= 0 and quantity_to_produce <= 0:
            raise ValidationError(
                "You must specify either quantity to purchase or produce."
            )
        return cleaned_data


class PurchaseRequisitionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = PurchaseRequisition
        fields = [
            'supplier', 'quantity', 'unit_cost',
            'required_by_date', 'expected_delivery_date', 'notes'
        ]
        widgets = {
            'required_by_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'unit_cost': forms.NumberInput(attrs={'step': '0.0001', 'min': 0}),
            'quantity': forms.NumberInput(attrs={'min': 1}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'supplier': 'Vendor supplying the materials',
            'quantity': 'Amount of material to purchase',
            'unit_cost': 'Cost per unit of material',
            'required_by_date': 'When the material is absolutely needed',
            'expected_delivery_date': 'When supplier promises delivery',
            'notes': 'Special instructions or terms',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        required_by_date = cleaned_data.get('required_by_date')
        expected_delivery_date = cleaned_data.get('expected_delivery_date')
        
        if required_by_date and expected_delivery_date:
            if expected_delivery_date > required_by_date:
                self.add_error(
                    'expected_delivery_date',
                    "Expected delivery date must be before required by date."
                )
        
        unit_cost = cleaned_data.get('unit_cost')
        if unit_cost is not None and unit_cost <= 0:
            self.add_error('unit_cost', "Unit cost must be greater than zero.")
        
        return cleaned_data


class ProductionOrderForm(BootstrapFormMixin, forms.ModelForm):
    bom = forms.ModelChoiceField(
        queryset=BOMHeader.objects.filter(status='approved'),
        label="BOM Version",
        help_text="Select the approved Bill of Materials for this production"
    )
    
    class Meta:
        model = ProductionOrder
        fields = [
            'order_number', 'bom', 'quantity',
            'start_date', 'end_date', 'notes'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'order_number': forms.TextInput(attrs={'placeholder': 'PO-XXXX'}),
            'quantity': forms.NumberInput(attrs={'min': 1}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'order_number': 'Unique identifier for this production order',
            'quantity': 'Number of items to produce',
            'start_date': 'When production should begin',
            'end_date': 'When production should be completed',
            'notes': 'Special instructions for production',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if end_date < start_date:
                self.add_error('end_date', "End date must be after start date.")
            
            if start_date < timezone.now().date():
                self.add_error('start_date', "Start date cannot be in the past.")
        
        quantity = cleaned_data.get('quantity')
        if quantity and quantity <= 0:
            self.add_error('quantity', "Quantity must be greater than zero.")
        
        return cleaned_data


class MaterialShortageResolutionForm(BootstrapFormMixin, forms.ModelForm):
    resolution_action = forms.ChoiceField(
        choices=[
            ('purchase', 'Purchase Additional Materials'),
            ('substitute', 'Use Substitute Materials'),
            ('reschedule', 'Reschedule Production'),
            ('other', 'Other Action'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text="Select the action taken to resolve this shortage"
    )
    
    class Meta:
        model = MaterialShortageAlert
        fields = ['resolution_action', 'resolution_notes']
        widgets = {
            'resolution_notes': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe how the shortage was resolved...'
            }),
        }
        help_texts = {
            'resolution_notes': 'Detailed explanation of the resolution',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to radio select options
        self.fields['resolution_action'].widget.attrs.update({'class': ''})
        for choice in self.fields['resolution_action'].widget.choices:
            self.fields['resolution_action'].widget.attrs.update({
                f'class_{choice[0]}': 'form-check-label'
            })