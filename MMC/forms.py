# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import *
import re
from datetime import date
from Account.models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email address'
    }))
    user_type = forms.ChoiceField(choices=CustomUser.USER_TYPES, widget=forms.Select(attrs={
        'class': 'form-select'
    }))
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2', 'user_type', 'phone', 
                 'first_name', 'last_name', 'department', 'designation', 'employee_id')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'}),
            'designation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Designation'}),
            'employee_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Employee ID'}),
        }
    
    def clean_mobile(self):
        phone = self.cleaned_data.get('phone')
        if phone and not re.match(r'^[6-9]\d{9}$', phone):
            raise ValidationError("Please enter a valid 10-digit phone number starting with 6-9")
        return phone

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Username or Email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Password'
    }))

class RMPRegistrationForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text="Format: YYYY-MM-DD"
    )
    cpd_cycle_start = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    cpd_cycle_end = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    class Meta:
        model = RMPProfile
        fields = [
            'prefix', 'full_name', 'father_name', 'mother_name', 'marital_status',
            'maiden_name', 'husband_name', 'date_of_birth', 'gender', 'blood_group', 'nationality',
            'category', 'email', 'mobile', 'communication_address', 'communication_city',
            'communication_district', 'communication_state', 'communication_pincode',
            'residential_address', 'clinic_address', 'clinic_phone', 'specialization',
            'sub_specialization', 'medical_council', 'year_of_graduation', 'college_name',
            'university', 'aadhaar_number', 'pan_number', 'emergency_contact', 'emergency_phone',
            'cpd_cycle_start', 'cpd_cycle_end'
        ]
        widgets = {
            'prefix': forms.Select(attrs={'class': 'form-select'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name as per documents'}),
            'father_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mother_name': forms.TextInput(attrs={'class': 'form-control'}),
            'marital_status': forms.Select(attrs={'class': 'form-select'}),
            'maiden_name': forms.TextInput(attrs={'class': 'form-control'}),
            'husband_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'blood_group': forms.Select(attrs={'class': 'form-select'}),
            'nationality': forms.TextInput(attrs={'class': 'form-control', 'value': 'Indian'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'pattern': '[6-9][0-9]{9}'}),
            'communication_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'communication_city': forms.TextInput(attrs={'class': 'form-control'}),
            'communication_district': forms.TextInput(attrs={'class': 'form-control'}),
            'communication_state': forms.TextInput(attrs={'class': 'form-control', 'value': 'Maharashtra'}),
            'communication_pincode': forms.TextInput(attrs={'class': 'form-control', 'pattern': '[0-9]{6}'}),
            'residential_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'clinic_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'clinic_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'specialization': forms.TextInput(attrs={'class': 'form-control'}),
            'sub_specialization': forms.TextInput(attrs={'class': 'form-control'}),
            'medical_council': forms.TextInput(attrs={'class': 'form-control'}),
            'year_of_graduation': forms.NumberInput(attrs={'class': 'form-control', 'min': '1950', 'max': '2030'}),
            'college_name': forms.TextInput(attrs={'class': 'form-control'}),
            'university': forms.TextInput(attrs={'class': 'form-control'}),
            'aadhaar_number': forms.TextInput(attrs={'class': 'form-control', 'pattern': '[0-9]{12}'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'pattern': '[A-Z]{5}[0-9]{4}[A-Z]{1}'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if mobile and not re.match(r'^[6-9]\d{9}$', mobile):
            raise ValidationError("Please enter a valid 10-digit mobile number starting with 6-9")
        return mobile
    
    def clean_communication_pincode(self):
        pincode = self.cleaned_data.get('communication_pincode')
        if pincode and not re.match(r'^\d{6}$', pincode):
            raise ValidationError("Please enter a valid 6-digit pincode")
        return pincode
    
    def clean_aadhaar_number(self):
        aadhaar = self.cleaned_data.get('aadhaar_number')
        if aadhaar and not re.match(r'^\d{12}$', aadhaar):
            raise ValidationError("Please enter a valid 12-digit Aadhaar number")
        return aadhaar
    
    def clean_pan_number(self):
        pan = self.cleaned_data.get('pan_number')
        if pan and not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan):
            raise ValidationError("Please enter a valid PAN number")
        return pan
    
    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob > timezone.now().date():
            raise ValidationError("Date of birth cannot be in the future")
        return dob

class MedicalQualificationForm(forms.ModelForm):
    class Meta:
        model = MedicalQualification
        fields = ['qualification_level', 'degree_name', 'specialization', 'college_name', 
                 'university', 'country', 'year_of_passing', 'duration', 'registration_number', 
                 'registration_council']
        widgets = {
            'qualification_level': forms.Select(attrs={'class': 'form-select'}),
            'degree_name': forms.TextInput(attrs={'class': 'form-control'}),
            'specialization': forms.TextInput(attrs={'class': 'form-control'}),
            'college_name': forms.TextInput(attrs={'class': 'form-control'}),
            'university': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'value': 'India'}),
            'year_of_passing': forms.NumberInput(attrs={'class': 'form-control', 'min': 1950, 'max': 2030}),
            'duration': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_council': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_year_of_passing(self):
        year = self.cleaned_data.get('year_of_passing')
        current_year = timezone.now().year
        if year and (year < 1950 or year > current_year):
            raise ValidationError(f"Year of passing must be between 1950 and {current_year}")
        return year

class PassportDetailsForm(forms.Form):
    passport_number = forms.CharField(
        max_length=20,
        help_text='Enter your passport number'
    )
    passport_issue_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Passport Issue Date'
    )
    passport_expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Passport Expiry Date'
    )
    passport_address = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        label='Address as on Passport'
    )
    visa_type = forms.CharField(max_length=50, required=False, label='Visa Type (if applicable)')
    visa_number = forms.CharField(max_length=50, required=False, label='Visa Number (if applicable)')
    first_departure_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label='First Departure Date from India'
    )
    last_return_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label='Last Return Date to India'
    )
    passport_change_loss = forms.ChoiceField(
        choices=[('', 'Select Option'), ('YES', 'Yes'), ('NO', 'No')],
        widget=forms.Select(attrs={'class': 'form-select', 'onchange': 'togglePassportChange(this.value)'}),
        label='Any Change/Loss in Passport?'
    )
    passport_change_details = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label='Details of Change/Loss'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        passport_issue_date = cleaned_data.get('passport_issue_date')
        passport_expiry_date = cleaned_data.get('passport_expiry_date')
        first_departure_date = cleaned_data.get('first_departure_date')
        last_return_date = cleaned_data.get('last_return_date')
        passport_change_loss = cleaned_data.get('passport_change_loss')
        passport_change_details = cleaned_data.get('passport_change_details')
        
        if passport_issue_date and passport_expiry_date:
            if passport_expiry_date <= passport_issue_date:
                self.add_error('passport_expiry_date', 'Passport expiry date must be after issue date.')
            if passport_expiry_date <= timezone.now().date():
                self.add_error('passport_expiry_date', 'Passport must be valid (not expired).')
        
        if first_departure_date and last_return_date:
            if last_return_date <= first_departure_date:
                self.add_error('last_return_date', 'Return date must be after departure date.')
        
        if passport_change_loss == 'YES' and not passport_change_details:
            self.add_error('passport_change_details', 'Please provide details of passport change/loss.')
        
        return cleaned_data

class ScreeningTestForm(forms.Form):
    screening_test_taken = forms.ChoiceField(
        choices=[('', 'Select Option'), ('YES', 'Yes'), ('NO', 'No')],
        widget=forms.Select(attrs={'class': 'form-select', 'onchange': 'toggleScreeningTest(this.value)'}),
        label='Screening Test Taken?'
    )
    screening_board = forms.CharField(max_length=200, required=False, label='Conducting Board Name')
    screening_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label='Screening Test Date'
    )
    screening_roll_no = forms.CharField(max_length=50, required=False, label='Roll Number')
    screening_marks = forms.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        required=False, 
        label='Marks/Percentage',
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    screening_certificate = forms.FileField(
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])],
        required=False,
        label='Screening Test Certificate/Result',
        help_text='Upload screening test result certificate (PDF, JPG, PNG, max 2MB)'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        screening_test_taken = cleaned_data.get('screening_test_taken')
        
        if screening_test_taken == 'YES':
            required_fields = ['screening_board', 'screening_date', 'screening_roll_no', 'screening_marks']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, 'This field is required when screening test was taken.')
            
            if not cleaned_data.get('screening_certificate'):
                self.add_error('screening_certificate', 'Screening test certificate is required.')
        
        return cleaned_data


class InternshipTrainingForm(forms.Form):
    internship_institute = forms.CharField(max_length=200, label='Institute/Hospital Name')
    internship_address = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        label='Institute Address'
    )
    internship_state = forms.CharField(max_length=50, label='State')
    mci_recognized = forms.ChoiceField(
        choices=[('', 'Select Option'), ('YES', 'Yes'), ('NO', 'No')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='MCI/NMC Recognized?'
    )
    internship_duration = forms.CharField(
        max_length=100, 
        label='Duration (Months)',
        help_text='e.g., 12 months, 1 year'
    )
    days_present = forms.IntegerField(
        label='Total Days Present',
        validators=[MinValueValidator(1)],
        help_text='Total number of days attended during internship'
    )
    internship_certificate = forms.FileField(
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])],
        label='Internship Completion Certificate',
        help_text='Upload internship completion certificate (PDF, JPG, PNG, max 2MB)'
    )
    
    def clean_days_present(self):
        days_present = self.cleaned_data.get('days_present')
        if days_present and days_present > 365 * 2:  # Assuming max 2 years internship
            raise ValidationError('Days present seems unusually high. Please verify.')
        return days_present

class ForeignTrainingForm(forms.Form):
    medical_degree_name = forms.CharField(max_length=200, label='Medical Degree/Diploma Name')
    practical_training_details = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        label='Practical Training Details',
        help_text='Describe the practical/hands-on training received'
    )
    indian_college_attendance = forms.ChoiceField(
        choices=[('', 'Select Option'), ('YES', 'Yes'), ('NO', 'No')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Attended Indian Medical College?'
    )
    language_study = forms.CharField(
        max_length=100, 
        label='Language of Study',
        help_text='e.g., English, French, German, etc.'
    )
    foreign_registration_number = forms.CharField(
        max_length=100, 
        required=False, 
        label='Foreign Medical Council Registration Number'
    )
    foreign_registration_country = forms.CharField(
        max_length=100, 
        required=False, 
        label='Country of Registration'
    )
    foreign_registration_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label='Foreign Registration Date'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        foreign_registration_number = cleaned_data.get('foreign_registration_number')
        foreign_registration_country = cleaned_data.get('foreign_registration_country')
        foreign_registration_date = cleaned_data.get('foreign_registration_date')
        
        # If any foreign registration field is filled, all should be filled
        foreign_fields = [foreign_registration_number, foreign_registration_country, foreign_registration_date]
        if any(foreign_fields) and not all(foreign_fields):
            if not foreign_registration_number:
                self.add_error('foreign_registration_number', 'Required if registered in foreign country.')
            if not foreign_registration_country:
                self.add_error('foreign_registration_country', 'Required if registered in foreign country.')
            if not foreign_registration_date:
                self.add_error('foreign_registration_date', 'Required if registered in foreign country.')
        
        return cleaned_data

class DeclarationForm(forms.Form):
    declaration_agree = forms.BooleanField(
        required=True,
        label='I hereby declare that all information provided in this application is true, complete and correct to the best of my knowledge and belief.',
        error_messages={'required': 'You must agree to the declaration to proceed.'}
    )
    imc_code_pledge = forms.BooleanField(
        required=True,
        label='I pledge to abide by the Indian Medical Council (Professional Conduct, Etiquette and Ethics) Regulations and maintain the dignity and honor of the medical profession.',
        error_messages={'required': 'You must pledge to abide by the IMC code of ethics.'}
    )
    undertaking_agree = forms.BooleanField(
        required=True,
        label='I undertake to inform the Maharashtra Medical Council about any change in my address, qualifications, or employment within 30 days of such change.',
        error_messages={'required': 'You must agree to the undertaking.'}
    )

class ExperienceForm(forms.ModelForm):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    class Meta:
        model = Experience
        fields = ['organization', 'designation', 'start_date', 'end_date', 'currently_working', 
                 'description', 'address', 'city', 'country']
        widgets = {
            'organization': forms.TextInput(attrs={'class': 'form-control'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'value': 'India'}),
            'currently_working': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        currently_working = cleaned_data.get('currently_working')
        
        if start_date and start_date > timezone.now().date():
            raise ValidationError("Start date cannot be in the future")
        
        if end_date and not currently_working:
            if end_date < start_date:
                raise ValidationError("End date cannot be before start date")
            if end_date > timezone.now().date():
                raise ValidationError("End date cannot be in the future")
        
        if currently_working and end_date:
            raise ValidationError("End date should not be provided if currently working")
        
        return cleaned_data

class PublicationForm(forms.ModelForm):
    publication_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    
    class Meta:
        model = Publication
        fields = ['publication_type', 'title', 'authors', 'journal_name', 'volume', 'issue', 
                 'pages', 'publisher', 'publication_date', 'doi', 'url', 'description']
        widgets = {
            'publication_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'authors': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'journal_name': forms.TextInput(attrs={'class': 'form-control'}),
            'volume': forms.TextInput(attrs={'class': 'form-control'}),
            'issue': forms.TextInput(attrs={'class': 'form-control'}),
            'pages': forms.TextInput(attrs={'class': 'form-control'}),
            'publisher': forms.TextInput(attrs={'class': 'form-control'}),
            'doi': forms.TextInput(attrs={'class': 'form-control'}),
            'url': forms.URLInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean_publication_date(self):
        pub_date = self.cleaned_data.get('publication_date')
        if pub_date and pub_date > timezone.now().date():
            raise ValidationError("Publication date cannot be in the future")
        return pub_date

class AwardForm(forms.ModelForm):
    class Meta:
        model = Award
        fields = ['award_name', 'awarding_organization', 'year', 'description', 'certificate_file']
        widgets = {
            'award_name': forms.TextInput(attrs={'class': 'form-control'}),
            'awarding_organization': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': 1950, 'max': 2030}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'certificate_file': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_year(self):
        year = self.cleaned_data.get('year')
        current_year = timezone.now().year
        if year and (year < 1950 or year > current_year):
            raise ValidationError(f"Year must be between 1950 and {current_year}")
        return year

class EducationalQualificationForm(forms.ModelForm):
    class Meta:
        model = EducationalQualification
        fields = ['qualification_type', 'institution_name', 'board_university', 
                 'roll_number', 'year_of_passing', 'percentage', 'marksheet']
        widgets = {
            'qualification_type': forms.Select(attrs={'class': 'form-select'}),
            'institution_name': forms.TextInput(attrs={'class': 'form-control'}),
            'board_university': forms.TextInput(attrs={'class': 'form-control'}),
            'roll_number': forms.TextInput(attrs={'class': 'form-control'}),
            'year_of_passing': forms.NumberInput(attrs={'class': 'form-control', 'min': 1950, 'max': 2030}),
            'percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'marksheet': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_percentage(self):
        percentage = self.cleaned_data.get('percentage')
        if percentage and (percentage < 0 or percentage > 100):
            raise ValidationError("Percentage must be between 0 and 100")
        return percentage

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['subject_name', 'maximum_marks', 'obtained_marks', 'percentage', 'result']
        widgets = {
            'subject_name': forms.TextInput(attrs={'class': 'form-control'}),
            'maximum_marks': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'obtained_marks': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'result': forms.Select(attrs={'class': 'form-select'}),
        }

SubjectFormSet = forms.inlineformset_factory(
    EducationalQualification, Subject, form=SubjectForm, 
    extra=1, can_delete=True, min_num=1, validate_min=True
)

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['application_type', 'priority']
        widgets = {
            'application_type': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }

class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['document_type', 'document_file']
        widgets = {
            'document_file': forms.FileInput(attrs={'class': 'form-control'}),
            'document_type': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_document_file(self):
        document_file = self.cleaned_data.get('document_file')
        if document_file:
            # Check file size (5MB limit)
            if document_file.size > 5 * 1024 * 1024:
                raise ValidationError("File size must be less than 5MB")
            
            # Check file extension
            allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx']
            file_extension = document_file.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                raise ValidationError(f"Allowed file types: {', '.join(allowed_extensions)}")
        
        return document_file

class DocumentVerificationForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['is_verified', 'verification_notes']
        widgets = {
            'verification_notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter verification notes or reasons for rejection...'}),
        }

class CertificateRequestForm(forms.Form):
    CERTIFICATE_TYPES = (
        ('DUPLICATE', 'Duplicate Registration Certificate'),
        ('GOOD_STANDING', 'Good Standing Certificate'),
        ('NOC', 'No Objection Certificate'),
        ('CPD_COMPLETION', 'CPD Completion Certificate'),
    )
    
    certificate_type = forms.ChoiceField(
        choices=CERTIFICATE_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    purpose = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Explain why you need this certificate'
    )
    delivery_method = forms.ChoiceField(
        choices=[('DIGITAL', 'Digital Copy Only'), ('PHYSICAL', 'Physical Copy Required')],
        widget=forms.RadioSelect
    )
    urgent_processing = forms.BooleanField(
        required=False,
        label='Urgent Processing',
        help_text='Expedited processing (additional charges may apply)'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        certificate_type = cleaned_data.get('certificate_type')
        
        # Additional validation based on certificate type
        if certificate_type == 'GOOD_STANDING':
            # Check if user has active registration
            pass
        
        return cleaned_data

class GoodStandingRequestForm(forms.ModelForm):
    purpose = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Explain the purpose for requesting Good Standing Certificate...'}),
        help_text='Detailed purpose of requesting the certificate'
    )
    delivery_method = forms.ChoiceField(
        choices=[('EMAIL', 'Email (Digital Copy)'), ('POST', 'Postal (Physical Copy)')],
        widget=forms.RadioSelect,
        initial='EMAIL'
    )
    
    class Meta:
        model = GoodStandingRequest
        fields = ['purpose', 'country', 'receiving_authority', 'authority_address', 'delivery_method']
        widgets = {
            'authority_address': forms.Textarea(attrs={'rows': 3}),
            'country': forms.TextInput(attrs={'placeholder': 'Country where certificate will be used'}),
            'receiving_authority': forms.TextInput(attrs={'placeholder': 'Name of receiving organization/authority'}),
        }

class NOCRequestForm(forms.ModelForm):
    expected_departure_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Expected date of departure from Maharashtra'
    )
    
    class Meta:
        model = NOCRequest
        fields = ['destination_state', 'destination_council', 'reason_for_transfer', 'expected_departure_date']
        widgets = {
            'reason_for_transfer': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Explain the reason for transferring to another state...'}),
            'destination_council': forms.TextInput(attrs={'placeholder': 'Name of the State Medical Council'}),
        }

class ChangeRequestForm(forms.ModelForm):
    class Meta:
        model = ChangeRequest
        fields = ['change_type', 'old_value', 'new_value', 'supporting_documents']
        widgets = {
            'old_value': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Current value as per records...'}),
            'new_value': forms.Textarea(attrs={'rows': 3, 'placeholder': 'New value to be updated...'}),
            'change_type': forms.Select(attrs={'class': 'form-select'}),
        }
        help_texts = {
            'supporting_documents': 'Upload supporting documents for the change (e.g., marriage certificate, address proof, degree certificate)',
        }

class TerminationRequestForm(forms.ModelForm):
    termination_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Effective date of termination'
    )
    
    class Meta:
        model = TerminationRequest
        fields = ['termination_reason', 'termination_date', 'supporting_documents']
        widgets = {
            'termination_reason': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Provide detailed reason for termination request...'}),
        }
        help_texts = {
            'supporting_documents': 'Upload supporting documents (e.g., retirement letter, resignation acceptance, etc.)',
        }

class VerificationTaskForm(forms.ModelForm):
    assigned_to = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(user_type__in=['ADMIN', 'VERIFIER'], is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    due_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        help_text='Set deadline for task completion'
    )
    priority = forms.ChoiceField(
        choices=VerificationTask.TASK_STATUS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    task_type = forms.ChoiceField(
        choices=VerificationTask.TASK_STATUS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = VerificationTask
        fields = ['assigned_to', 'due_date', 'priority', 'task_type', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class CPDProgramForm(forms.ModelForm):
    start_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'})
    )
    end_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'})
    )
    
    class Meta:
        model = CPDProgram
        fields = '__all__'
        exclude = ['created_by', 'created_date', 'updated_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'program_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'detailed_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'organizer': forms.TextInput(attrs={'class': 'form-control'}),
            'co_organizers': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'venue': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'max_participants': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'cpd_points': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'registration_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'is_online': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'target_audience': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'learning_objectives': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'prerequisites': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise ValidationError("End date must be after start date")
        
        return cleaned_data

class AccreditationForm(forms.ModelForm):
    issue_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    expiry_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    
    class Meta:
        model = Accreditation
        fields = '__all__'
        exclude = ['created_by', 'created_date', 'updated_date', 'accreditation_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'accreditation_type': forms.Select(attrs={'class': 'form-select'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'specialties': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'review_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        issue_date = cleaned_data.get('issue_date')
        expiry_date = cleaned_data.get('expiry_date')
        
        if issue_date and expiry_date and issue_date >= expiry_date:
            raise ValidationError("Expiry date must be after issue date")
        
        return cleaned_data

class PaymentForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        disabled=True,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    payment_method = forms.ChoiceField(
        choices=Payment.PAYMENT_METHODS,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        application_type = kwargs.pop('application_type', None)
        super().__init__(*args, **kwargs)
        
        # Set amount based on application type
        if application_type:
            fee_amount = self.get_fee_amount(application_type)
            self.fields['amount'].initial = fee_amount
    
    def get_fee_amount(self, application_type):
        fee_structure = {
            'provisional': 1500,
            'permanent': 2500,
            'renewal': 1000,
            'additional_qualification': 500,
            'good_standing_mmc': 1000,
            'good_standing_nmc': 1500,
            'good_standing_nri': 2000,
            'duplicate': 500,
            'verification': 300,
            'address_change': 200,
            'name_change': 500,
            'noc_state': 1000,
            'foreign_verification': 1500,
        }
        return fee_structure.get(application_type, 1000)

class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['against_rmp', 'complaint_text', 'severity', 'category', 'sub_category']
        widgets = {
            'against_rmp': forms.Select(attrs={'class': 'form-select'}),
            'complaint_text': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 5, 
                'placeholder': 'Describe your complaint in detail...'
            }),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'sub_category': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ApplicationReviewForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['status', 'review_notes', 'assigned_to', 'rejection_reason', 'sla_days']
        widgets = {
            'review_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'rejection_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'sla_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 30}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        rejection_reason = cleaned_data.get('rejection_reason')
        
        if status == 'rejected' and not rejection_reason:
            raise ValidationError("Rejection reason is required when rejecting an application")
        
        return cleaned_data

class BulkActionForm(forms.Form):
    ACTION_CHOICES = (
        ('ASSIGN_VERIFIER', 'Assign to Verifier'),
        ('BULK_APPROVE', 'Bulk Approve'),
        ('BULK_REJECT', 'Bulk Reject'),
        ('SEND_REMINDER', 'Send Reminder'),
        ('MARK_URGENT', 'Mark as Urgent'),
    )
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-select', 'onchange': 'toggleBulkActionFields(this.value)'})
    )
    applications = forms.ModelMultipleChoiceField(
        queryset=Application.objects.all(),
        widget=forms.MultipleHiddenInput
    )
    verifier = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(user_type__in=['ADMIN', 'VERIFIER']),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter notes or reason for action...'}),
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        verifier = cleaned_data.get('verifier')
        
        if action == 'ASSIGN_VERIFIER' and not verifier:
            self.add_error('verifier', 'Please select a verifier for assignment.')
        
        return cleaned_data

class AIPerformanceFilterForm(forms.Form):
    SPECIALIZATION_CHOICES = (
        ('', 'All Specializations'),
        ('cardiology', 'Cardiology'),
        ('neurology', 'Neurology'),
        ('pediatrics', 'Pediatrics'),
        ('surgery', 'Surgery'),
        ('gynecology', 'Gynecology'),
        ('orthopedics', 'Orthopedics'),
        ('general', 'General Medicine'),
    )
    
    specialization = forms.ChoiceField(
        choices=SPECIALIZATION_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    score_range = forms.ChoiceField(
        choices=(
            ('', 'All Scores'),
            ('90-100', 'Excellent (90-100)'),
            ('75-89', 'Good (75-89)'),
            ('60-74', 'Average (60-74)'),
            ('0-59', 'Needs Improvement (0-59)'),
        ),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    show_insights = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

class SystemConfigForm(forms.ModelForm):
    class Meta:
        model = SystemConfig
        fields = ['key', 'value', 'description', 'data_type', 'is_active']
        widgets = {
            'key': forms.TextInput(attrs={'class': 'form-control'}),
            'value': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'data_type': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class AuditLogFilterForm(forms.Form):
    ACTION_CHOICES = (
        ('', 'All Actions'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
    )
    
    action_type = forms.ChoiceField(
        choices=ACTION_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    user = forms.ModelChoiceField(
        queryset=CustomUser.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

# Bulk upload forms
class BulkUploadForm(forms.Form):
    UPLOAD_TYPE_CHOICES = (
        ('cpd_programs', 'CPD Programs'),
        ('rmp_data', 'RMP Data'),
        ('accreditations', 'Accreditations'),
    )
    
    upload_type = forms.ChoiceField(
        choices=UPLOAD_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    csv_file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'})
    )
    description = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional description'})
    )

class EmailTemplateForm(forms.Form):
    TEMPLATE_CHOICES = (
        ('application_submitted', 'Application Submitted'),
        ('payment_success', 'Payment Success'),
        ('registration_approved', 'Registration Approved'),
        ('cpd_reminder', 'CPD Reminder'),
        ('renewal_reminder', 'Renewal Reminder'),
    )
    
    template_type = forms.ChoiceField(
        choices=TEMPLATE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    subject = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 8})
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

# forms.py - Reports Module Forms
class ReportFilterForm(forms.Form):
    DATE_RANGE_CHOICES = (
        ('TODAY', 'Today'),
        ('YESTERDAY', 'Yesterday'),
        ('THIS_WEEK', 'This Week'),
        ('THIS_MONTH', 'This Month'),
        ('LAST_MONTH', 'Last Month'),
        ('CUSTOM', 'Custom Date Range'),
    )

    APPLICATION_TYPES = (
        ('', 'All Types'),
        ('provisional', 'Provisional Registration'),
        ('permanent', 'Permanent Registration'),
        ('foreign_provisional', 'Foreign Provisional Registration'),
        ('additional_qualification', 'Additional Qualification'),
        ('renewal', 'Renewal of Registration'),
        ('manual_verification', 'Manual Document Verification'),
    )

    PAYMENT_STATUS = (
        ('', 'All Status'),
        ('success', 'Success'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
    )

    PAYMENT_METHODS = (
        ('', 'All Methods'),
        ('online', 'Online Payment'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
    )

    COMPLAINT_SEVERITY = (
        ('', 'All Severity'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )

    date_range = forms.ChoiceField(
        choices=DATE_RANGE_CHOICES,
        required=False,
        initial='THIS_MONTH',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'date_range_f',
            'onchange': 'toggleCustomDate()'
        })
    )

    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'id': 'start_date_f',
            'type': 'date',
            'placeholder': 'Start Date',
            'style': 'display: none;'
        })
    )

    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'id': 'end_date_f',
            'type': 'date',
            'placeholder': 'End Date',
            'style': 'display: none;'
        })
    )

    application_type = forms.ChoiceField(
        choices=APPLICATION_TYPES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'application_type_f'
        })
    )

    status = forms.ChoiceField(
        choices=(
            ('', 'All Status'),
            ('submitted', 'Submitted'),
            ('under_review', 'Under Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'status_f'
        })
    )

    payment_status = forms.ChoiceField(
        choices=PAYMENT_STATUS,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'payment_status_f'
        })
    )

    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHODS,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'payment_method_f'
        })
    )

    severity = forms.ChoiceField(
        choices=COMPLAINT_SEVERITY,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'severity_f'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        date_range = cleaned_data.get('date_range')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if date_range == 'CUSTOM' and (not start_date or not end_date):
            raise forms.ValidationError("Please select both start and end dates for custom range.")

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Start date cannot be after end date.")

        return cleaned_data

class ReportGenerationForm(forms.Form):
    REPORT_TYPES = (
        ('payment_summary', 'Payment Summary Report'),
        ('application_status', 'Application Status Report'),
        ('cpd_participation', 'CPD Participation Report'),
        ('staff_performance', 'Staff Performance Report'),
        ('complaint_analysis', 'Complaint Analysis Report'),
        ('manual_verification', 'Manual Verification Report'),
        ('revenue_analysis', 'Revenue Analysis Report'),
        ('registration_trends', 'Registration Trends Report'),
    )
    
    FORMAT_CHOICES = (
        ('excel', 'Excel (.xls)'),
        ('pdf', 'PDF (.pdf)'),
        ('csv', 'CSV (.csv)'),
    )
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        initial='excel',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("Start date cannot be after end date.")
        
        return cleaned_data

class DateRangeForm(forms.Form):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Start date cannot be after end date.")
        
        return cleaned_data

class AISettingsForm(forms.Form):
    enable_predictive_analytics = forms.BooleanField(
        required=False, 
        initial=True,
        label='Enable Predictive Analytics',
        help_text='Use AI to predict application risks and compliance issues'
    )
    enable_compliance_alerts = forms.BooleanField(
        required=False, 
        initial=True,
        label='Enable Compliance Alerts',
        help_text='Generate automatic alerts for CPD and renewal compliance'
    )
    enable_performance_insights = forms.BooleanField(
        required=False, 
        initial=True,
        label='Enable Performance Insights',
        help_text='Provide AI-powered performance insights for RMPs'
    )
    risk_threshold = forms.IntegerField(
        min_value=1, 
        max_value=100, 
        initial=70,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text='Risk score threshold for flagging applications (1-100)'
    )
    update_frequency = forms.ChoiceField(
        choices=[('DAILY', 'Daily'), ('WEEKLY', 'Weekly'), ('MONTHLY', 'Monthly')],
        initial='WEEKLY',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='How often to regenerate AI insights'
    )

class ServiceSelectionForm(forms.Form):
    SERVICE_CATEGORIES = [
        ('registration', 'Registration Services'),
        ('verification', 'Verification Services'),
        ('modification', 'Modification Services'),
        ('certificate', 'Certificate Services'),
        ('special', 'Special Services'),
    ]
    
    category = forms.ChoiceField(
        choices=SERVICE_CATEGORIES,
        widget=forms.Select(attrs={'class': 'form-select', 'onchange': 'filterServices(this.value)'})
    )
    service_type = forms.ChoiceField(
        choices=Application.APPLICATION_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class BulkVerificationForm(forms.Form):
    applications = forms.ModelMultipleChoiceField(
        queryset=Application.objects.filter(status__in=['SUBMITTED', 'UNDER_REVIEW']),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '10'})
    )
    action = forms.ChoiceField(
        choices=[
            ('assign', 'Assign to Verifier'),
            ('approve', 'Bulk Approve'),
            ('reject', 'Bulk Reject'),
            ('request_info', 'Request Additional Information')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    verifier = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(user_type__in=['ADMIN', 'VERIFIER']),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter notes for bulk action...'}),
        required=False
    )

class CPDCreditUpdateForm(forms.Form):
    CREDIT_TYPES = [
        ('national', 'National CPD Points'),
        ('international', 'International CPD Points'),
        ('teacher', 'Teacher CPD Points'),
        ('pg_student', 'PG Student CPD Points'),
        ('covid', 'COVID-19 Points'),
    ]
    
    user = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(user_type='RMP'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    credit_type = forms.ChoiceField(
        choices=CREDIT_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    points = forms.IntegerField(
        min_value=1,
        max_value=100,
        help_text='Number of CPD points to add'
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Description of the CPD activity'
    )
    evidence = forms.FileField(
        required=False,
        help_text='Supporting evidence (if any)'
    )
    date_earned = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Date when points were earned'
    )

class SystemMaintenanceForm(forms.Form):
    MAINTENANCE_TYPES = [
        ('backup', 'Database Backup'),
        ('cleanup', 'System Cleanup'),
        ('update', 'System Update'),
        ('report', 'Generate System Report'),
    ]
    
    maintenance_type = forms.ChoiceField(
        choices=MAINTENANCE_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    schedule_time = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        help_text='Schedule maintenance for specific time (optional)'
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Description of maintenance activity'
    )
    send_notification = forms.BooleanField(
        required=False,
        initial=True,
        help_text='Send notification to users about maintenance'
    )

class AIPredictionSettingsForm(forms.Form):
    ENABLE_PREDICTIONS = [
        (True, 'Enable AI Predictions'),
        (False, 'Disable AI Predictions'),
    ]
    
    enable_predictions = forms.ChoiceField(
        choices=ENABLE_PREDICTIONS,
        widget=forms.RadioSelect,
        initial=True
    )
    risk_threshold = forms.IntegerField(
        min_value=0,
        max_value=100,
        initial=70,
        help_text='Risk score threshold for alerts (0-100)'
    )
    prediction_interval = forms.ChoiceField(
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly')
        ],
        initial='weekly',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    alert_channels = forms.MultipleChoiceField(
        choices=[
            ('dashboard', 'Dashboard'),
            ('email', 'Email'),
            ('sms', 'SMS'),
            ('push', 'Push Notification')
        ],
        widget=forms.CheckboxSelectMultiple,
        initial=['dashboard', 'email']
    )

class DocumentBulkVerificationForm(forms.Form):
    documents = forms.ModelMultipleChoiceField(
        queryset=Document.objects.filter(is_verified=False),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '8'})
    )
    verification_status = forms.ChoiceField(
        choices=[
            ('approve', 'Approve All'),
            ('reject', 'Reject All'),
            ('request', 'Request Re-upload')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text='Common notes for all selected documents'
    )

class CPDTextFileGenerationForm(forms.Form):
    PERIOD_CHOICES = [
        ('current_month', 'Current Month'),
        ('last_month', 'Last Month'),
        ('current_quarter', 'Current Quarter'),
        ('last_quarter', 'Last Quarter'),
        ('custom', 'Custom Period')
    ]
    
    period = forms.ChoiceField(
        choices=PERIOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    include_details = forms.BooleanField(
        required=False,
        initial=True,
        help_text='Include detailed participant information'
    )
    format = forms.ChoiceField(
        choices=[
            ('csv', 'CSV Format'),
            ('excel', 'Excel Format'),
            ('pdf', 'PDF Format')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )