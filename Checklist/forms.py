from django import forms
from .models import Checklist, ChecklistDocument
from django.core.validators import FileExtensionValidator

class ChecklistForm(forms.ModelForm):
    class Meta:
        model = Checklist
        fields = ['type', 'task', 'description', 'risk']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
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