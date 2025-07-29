from django import forms
from .models import BookMetadata

class BookMetadataForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add form-control class to all fields automatically
        for field_name, field in self.fields.items():
            if field.widget.attrs.get('class'):
                field.widget.attrs['class'] += ' form-control'
            else:
                field.widget.attrs['class'] = 'form-control'
            
            # Add form-select class to select fields
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-select'
            
            # Add placeholder if not already set
            if not field.widget.attrs.get('placeholder'):
                field.widget.attrs['placeholder'] = field.label

    class Meta:
        model = BookMetadata
        fields = '__all__'
        widgets = {
            'language': forms.Select(attrs={
                'class': 'form-select',
            }),
            'title': forms.TextInput(attrs={
                'placeholder': 'Enter book title',
            }),
            'author': forms.TextInput(attrs={
                'placeholder': 'Enter author name(s)',
            }),
            'publisher_name': forms.TextInput(attrs={
                'placeholder': 'Enter publisher name',
            }),
            'publisher_place': forms.TextInput(attrs={
                'placeholder': 'Enter publisher location ',
            }),
            'year_of_publication': forms.NumberInput(attrs={
                'placeholder': 'YYYY',
                'min': '1000',
                'max': '2100',
            }),
             'edition': forms.TextInput(attrs={
                'placeholder': 'Enter edition no name',
            }),
             'accession_no': forms.TextInput(attrs={
                'placeholder': 'Enter accession no name',
            }),
             'class_no': forms.TextInput(attrs={
                'placeholder': 'Enter class no name',
            }),
             'book_no': forms.TextInput(attrs={
                'placeholder': 'Enter book no name',
            }),
            'pagination': forms.TextInput(attrs={
                'placeholder': 'e.g., 250 or xii+250',
            }),
            'isbn_no': forms.TextInput(attrs={
                'placeholder': 'Enter ISBN (10 or 13 digits)',
            }),
            'is_auto_generated': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
    
    def clean_year_of_publication(self):
        year = self.cleaned_data.get('year_of_publication')
        if year and (year < 1000 or year > 2100):
            raise forms.ValidationError("Please enter a valid year between 1000 and 2100")
        return year

class BookUploadForm(forms.Form):
    pdf_file = forms.FileField(
        label='Upload Scanned PDF',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'application/pdf',
        }),
        help_text='Upload a scanned PDF to extract metadata automatically (Max 20MB)'
    )
    process_pages = forms.IntegerField(
        label='Pages to Process',
        initial=3,
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Number of pages to analyze',
        }),
        help_text='Number of pages to analyze (first pages usually contain metadata)'
    )

    def clean_pdf_file(self):
        pdf_file = self.cleaned_data.get('pdf_file')
        if pdf_file:
            if pdf_file.size > 20 * 1024 * 1024:  # 20MB limit
                raise forms.ValidationError("File too large (max 20MB)")
            if not pdf_file.name.lower().endswith('.pdf'):
                raise forms.ValidationError("Only PDF files are accepted")
        return pdf_file