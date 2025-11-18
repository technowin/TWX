from django import forms
from django.core.validators import RegexValidator
from .models import AadharVerificationRequest

class AadharVerificationForm(forms.ModelForm):
    aadhaar_number = forms.CharField(
        max_length=12,
        min_length=12,
        validators=[
            RegexValidator(
                regex='^[0-9]{12}$',
                message='Aadhaar number must be exactly 12 digits'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 12-digit Aadhaar number',
            'pattern': '[0-9]{12}',
            'title': 'Please enter exactly 12 digits'
        })
    )
    
    consent = forms.BooleanField(
        required=True,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'required': 'required'
        })
    )
    
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Reason for verification (optional)',
            'rows': 3
        })
    )

    class Meta:
        model = AadharVerificationRequest
        fields = ['aadhaar_number', 'consent', 'reason']


class AadharOTPVerificationForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        validators=[
            RegexValidator(
                regex='^[0-9]{6}$',
                message='OTP must be exactly 6 digits'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 6-digit OTP',
            'pattern': '[0-9]{6}',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric'
        })
    )
    
    reference_id = forms.CharField(
        widget=forms.HiddenInput()
    )