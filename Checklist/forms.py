from django import forms
from .models import Checklist, ChecklistDocument
from django.core.validators import FileExtensionValidator

class ChecklistForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if field_name in ['risk', 'status']:
                # Special handling for select fields
                field.widget.attrs.update({
                    'class': 'form-select',
                    'data-bs-theme': 'auto'
                })
            elif isinstance(field.widget, forms.Textarea):
                # Textarea fields
                field.widget.attrs.update({
                    'class': 'form-control',
                    'data-bs-theme': 'auto',
                    'rows': 3,
                    'style': 'min-height: 100px;'
                })
            else:
                # Regular input fields
                field.widget.attrs.update({
                    'class': 'form-control',
                    'data-bs-theme': 'auto'
                })

    class Meta:
        model = Checklist
        fields = ['type', 'task', 'description', 'risk', 'observation', 'recommendation', 'status']
        widgets = {
            'description': forms.Textarea(),
            'observation': forms.Textarea(),
            'recommendation': forms.Textarea(),
        }
        labels = {
            'type': 'Checklist Type',
            'task': 'Task/Requirement',
            'description': 'Description',
            'risk': 'Risk Level',
            'observation': 'Observations',
            'recommendation': 'Recommendations',
            'status': 'Compliance Status'
        }
        help_texts = {
            'type': 'The category or type of compliance requirement',
            'risk': 'Select the appropriate risk level',
            'status': 'Current compliance status'
        }

class ChecklistDocumentForm(forms.ModelForm):
    class Meta:
        model = ChecklistDocument
        fields = ['checklist_type', 'doc_type', 'file']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically set checklist_type choices based on existing types
        type_choices = Checklist.objects.values_list('type', 'type').distinct()
        self.fields['checklist_type'].widget = forms.Select(choices=[('', '---------')] + list(type_choices))

class ChecklistBulkUploadForm(forms.Form):
    file = forms.FileField(
        label='CSV File',
        help_text='Upload a CSV file with columns: type,task,description,risk',
        validators=[FileExtensionValidator(allowed_extensions=['csv'])]
    )

class DocumentBulkUploadForm(forms.Form):
    file = forms.FileField(
        label='ZIP File',
        help_text='Upload a ZIP file containing documents. Naming convention: "type_doctype.ext" (e.g., "ISO9001_PDF.pdf")',
        validators=[FileExtensionValidator(allowed_extensions=['zip'])]
    )