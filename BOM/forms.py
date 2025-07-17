from django import forms
from .models import BOMHeader, BOMItem, Component, ComponentSupplier, Document, Comment, ApprovalRequest

class BaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields automatically
        for field in self.fields:
            # Skip if already has widget attributes
            if 'class' not in self.fields[field].widget.attrs:
                if isinstance(self.fields[field].widget, (forms.CheckboxInput, forms.RadioSelect)):
                    self.fields[field].widget.attrs['class'] = 'form-check-input'
                elif isinstance(self.fields[field].widget, forms.FileInput):
                    self.fields[field].widget.attrs['class'] = 'form-control'
                else:
                    self.fields[field].widget.attrs['class'] = 'form-control'
            
            # Add placeholder if field has help text
            if self.fields[field].help_text and 'placeholder' not in self.fields[field].widget.attrs:
                self.fields[field].widget.attrs['placeholder'] = self.fields[field].help_text
            
            # Add form-label class to labels
            self.fields[field].label_attrs = {'class': 'form-label'}

class BOMHeaderForm(BaseForm):
    class Meta:
        model = BOMHeader
        fields = ['name', 'description', 'revision', 'parent_bom']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Enter BOM name',
                'class': 'form-control-lg'  # Make the name field larger
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Enter description (optional)',
                'class': 'form-control'
            }),
            'revision': forms.TextInput(attrs={
                'placeholder': 'e.g. A, B, 1.0, etc.'
            }),
            'parent_bom': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        help_texts = {
            'name': 'A unique name for this BOM',
            'revision': 'Revision identifier (letters or numbers)',
            'parent_bom': 'Optional parent BOM for hierarchical structures'
        }

class BOMItemForm(BaseForm):
    class Meta:
        model = BOMItem
        fields = ['component', 'quantity', 'reference_designators', 'notes']
        widgets = {
            'component': forms.HiddenInput(),
            'bom': forms.HiddenInput(),
            'quantity': forms.NumberInput(attrs={
                'min': '0.0001',
                'step': 'any',
                'class': 'form-control text-end'  # Right-align numbers
            }),
            'reference_designators': forms.TextInput(attrs={
                'placeholder': 'e.g. R1, R2, C5...'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Optional notes about this component in the BOM',
                'class': 'form-control'
            }),
        }
        help_texts = {
            'quantity': 'Required quantity per assembly',
            'reference_designators': 'Comma or space separated designators'
        }

class ComponentForm(BaseForm):
    UNIT_MEASURE_CHOICES = [
        ('', '-- Select Unit --'),  # Empty/default option
        ('ea', 'Each (ea)'),
        ('pc', 'Piece (pc)'),
        ('set', 'Set'),
        ('g', 'Gram (g)'),
        ('kg', 'Kilogram (kg)'),
        ('mm', 'Millimeter (mm)'),
        ('cm', 'Centimeter (cm)'),
        ('m', 'Meter (m)'),
        ('mL', 'Milliliter (mL)'),
        ('L', 'Liter (L)'),
        ('oz', 'Ounce (oz)'),
        ('lb', 'Pound (lb)'),
        ('in', 'Inch (in)'),
        ('ft', 'Foot (ft)'),
        ('m²', 'Square Meter (m²)'),
        ('mm²', 'Square Millimeter (mm²)'),
        ('cm²', 'Square Centimeter (cm²)'),
        ('in²', 'Square Inch (in²)'),
        ('ft²', 'Square Foot (ft²)'),
        ('m³', 'Cubic Meter (m³)'),
        ('mm³', 'Cubic Millimeter (mm³)'),
        ('cm³', 'Cubic Centimeter (cm³)'),
        ('in³', 'Cubic Inch (in³)'),
        ('ft³', 'Cubic Foot (ft³)'),
        ('deg', 'Degree (deg)'),
        ('rad', 'Radian (rad)'),
    ]

    unit_of_measure = forms.ChoiceField(
        choices=UNIT_MEASURE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    class Meta:
        model = Component
        fields = ['part_number', 'description', 'category', 'unit_of_measure', 
                  'material', 'tolerance', 'finish', 'weight', 'thumbnail']
        widgets = {
            'part_number': forms.TextInput(attrs={
                'class': 'form-control-lg font-monospace'  # Monospace for part numbers
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Detailed component description',
                'class': 'form-control'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'unit_of_measure': forms.Select(attrs={
                'class': 'form-select'
            }),
            'material': forms.TextInput(attrs={
                'placeholder': 'e.g. Aluminum, FR4, etc.'
            }),
            'tolerance': forms.TextInput(attrs={
                'placeholder': 'e.g. ±5%, ±0.1mm, etc.'
            }),
            'finish': forms.TextInput(attrs={
                'placeholder': 'e.g. Anodized, Gold Plated, etc.'
            }),
            'weight': forms.NumberInput(attrs={
                'min': '0',
                'step': 'any',
                'class': 'form-control text-end'
            }),
            'thumbnail': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
        help_texts = {
            'part_number': 'Unique identifier for this component',
            'unit_of_measure': 'Measurement unit for this component',
            'weight': 'Weight in grams (optional)'
        }

class ComponentSupplierForm(BaseForm):
    class Meta:
        model = ComponentSupplier
        fields = ['supplier', 'supplier_part_number', 'lead_time_days', 'cost', 'is_approved', 'notes']
        widgets = {
            'component': forms.HiddenInput(),
            'supplier': forms.Select(attrs={
                'class': 'form-select'
            }),
            'supplier_part_number': forms.TextInput(attrs={
                'class': 'font-monospace'
            }),
            'lead_time_days': forms.NumberInput(attrs={
                'min': '0',
                'class': 'form-control text-end'
            }),
            'cost': forms.NumberInput(attrs={
                'min': '0',
                'step': '0.0001',
                'class': 'form-control text-end'
            }),
            'is_approved': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Supplier-specific notes',
                'class': 'form-control'
            }),
        }
        help_texts = {
            'supplier_part_number': 'Part number used by this supplier',
            'lead_time_days': 'Typical delivery time in days',
            'cost': 'Cost per unit in base currency'
        }
        labels = {
            'is_approved': 'Approved for use?'
        }

class DocumentForm(BaseForm):
    class Meta:
        model = Document
        fields = ['name', 'document_type', 'file', 'description']
        widgets = {
            'bom': forms.HiddenInput(),
            'component': forms.HiddenInput(),
            'uploaded_by': forms.HiddenInput(),
            'name': forms.TextInput(attrs={
                'placeholder': 'Document title'
            }),
            'document_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Document description or notes',
                'class': 'form-control'
            }),
        }
        help_texts = {
            'file': 'Upload document file (PDF, image, etc.)'
        }

class CommentForm(BaseForm):
    class Meta:
        model = Comment
        fields = ['bom', 'author', 'text']
        widgets = {
            'bom': forms.HiddenInput(),
            'author': forms.HiddenInput(),
            'text': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Add your comment here...',
                'class': 'form-control'
            }),
        }

class ApprovalRequestForm(BaseForm):
    class Meta:
        model = ApprovalRequest
        fields = ['bom', 'requested_by', 'comments']
        widgets = {
            'bom': forms.HiddenInput(),
            'requested_by': forms.HiddenInput(),
            'comments': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Enter reason for approval request...',
                'class': 'form-control'
            }),
        }

class RejectionForm(forms.ModelForm):
    class Meta:
        model = ApprovalRequest
        fields = ['rejection_reason']
        widgets = {
            'rejection_reason': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Explain why you are rejecting this BOM...',
                'class': 'form-control'
            }),
        }