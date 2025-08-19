# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import *
from Account.models import CustomUser

# User Management Forms
class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address',
            'autocomplete': 'email'
        })
    )
    phone = forms.CharField(
        max_length=20, 
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter phone number',
            'autocomplete': 'tel'
        })
    )
    user_type = forms.ChoiceField(
        choices=CustomUser.USER_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'user_type_select'
        })
    )
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(), 
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'company_select'
        })
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(), 
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'group_select'
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'password1', 'password2', 'user_type', 'phone', 'company', 'group')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username',
                'autocomplete': 'username'
            }),
            'password1': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Create a password',
                'autocomplete': 'new-password'
            }),
            'password2': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Confirm password',
                'autocomplete': 'new-password'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set placeholders and help text
        self.fields['username'].help_text = 'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
        self.fields['password1'].help_text = '''
            <ul class="form-text">
                <li>Your password can\'t be too similar to your other personal information.</li>
                <li>Your password must contain at least 8 characters.</li>
                <li>Your password can\'t be a commonly used password.</li>
                <li>Your password can\'t be entirely numeric.</li>
            </ul>
        '''
        
        # Initially hide conditional fields
        self.fields['company'].widget.attrs.update({'class': 'form-select d-none'})
        self.fields['group'].widget.attrs.update({'class': 'form-select d-none'})
    
    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        company = cleaned_data.get('company')
        group = cleaned_data.get('group')
        
        if user_type == 'CORPORATE_TRAINEE' and not company:
            self.add_error('company', "Corporate trainees must select a company")
        if user_type == 'GROUP_TRAINEE' and not group:
            self.add_error('group', "Group trainees must select a group")
        
        return cleaned_data

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email or username',
            'autocomplete': 'username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password'
        })
    )
    
    error_messages = {
        'invalid_login': "Please enter a correct email/username and password.",
        'inactive': "This account is inactive.",
    }

class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'phone', 'profile_picture', 'dark_mode')
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email address'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your phone number'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'dark_mode': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add help text for image field
        self.fields['profile_picture'].help_text = 'Upload a profile picture (JPG, PNG, GIF)'

# Course Management Forms
class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'slug', 'description', 'short_description', 'instructor', 'category', 
                 'level', 'duration', 'price', 'discount_price', 'thumbnail', 'is_featured', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter course title'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'course-title-url'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Detailed course description'
            }),
            'short_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Brief course summary (max 300 characters)'
            }),
            'instructor': forms.Select(attrs={
                'class': 'form-select'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'level': forms.Select(attrs={
                'class': 'form-select'
            }),
            'duration': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Duration in hours',
                'min': 1
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'discount_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'thumbnail': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['instructor'].queryset = CustomUser.objects.filter(is_staff=True)
        self.fields['discount_price'].required = False
        self.fields['thumbnail'].help_text = 'Recommended size: 800x450 pixels'

class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['title', 'description', 'order', 'is_free']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Module title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Module description'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'is_free': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'description', 'video_url', 'video_file', 'duration', 'order', 'is_free']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Lesson title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Lesson description'
            }),
            'video_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com/video.mp4'
            }),
            'video_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'video/*'
            }),
            'duration': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'Duration in minutes'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'is_free': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        video_url = cleaned_data.get('video_url')
        video_file = cleaned_data.get('video_file')
        
        if not video_url and not video_file:
            raise forms.ValidationError("Either video URL or video file must be provided.")
        
        return cleaned_data

class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ['title', 'file', 'resource_type', 'is_free']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Resource title'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'resource_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_free': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

# Enrollment & Access Control Forms
class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['user', 'course', 'status', 'is_paid', 'payment_amount', 'payment_method', 'transaction_id']
        widgets = {
            'user': forms.Select(attrs={
                'class': 'form-select'
            }),
            'course': forms.Select(attrs={
                'class': 'form-select'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_paid': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'payment_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'payment_method': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'transaction_id': forms.TextInput(attrs={
                'class': 'form-control'
            }),
        }

class CorporateEnrollmentForm(forms.ModelForm):
    class Meta:
        model = CorporateEnrollment
        fields = ['company', 'course', 'purchased_seats', 'payment_amount', 'payment_method', 'transaction_id', 'access_expiry']
        widgets = {
            'company': forms.Select(attrs={
                'class': 'form-select'
            }),
            'course': forms.Select(attrs={
                'class': 'form-select'
            }),
            'purchased_seats': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'payment_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'payment_method': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'transaction_id': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'access_expiry': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }

class CorporateEnrollmentRequestForm(forms.ModelForm):
    class Meta:
        model = CorporateEnrollmentRequest
        fields = ['corporate_enrollment', 'user', 'comments']
        widgets = {
            'corporate_enrollment': forms.Select(attrs={
                'class': 'form-select'
            }),
            'user': forms.Select(attrs={
                'class': 'form-select'
            }),
            'comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional comments or requests'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if company:
            self.fields['corporate_enrollment'].queryset = CorporateEnrollment.objects.filter(company=company)
            self.fields['user'].queryset = CustomUser.objects.filter(company=company, user_type='CORPORATE_TRAINEE')

# Learning Experience Forms
class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['content', 'is_private']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Write your notes here...'
            }),
            'is_private': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

class BookmarkForm(forms.ModelForm):
    class Meta:
        model = Bookmark
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add notes about this bookmark...'
            }),
        }

class DiscussionForm(forms.ModelForm):
    class Meta:
        model = Discussion
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Ask a question or share your thoughts...'
            }),
        }

class ReplyForm(forms.ModelForm):
    class Meta:
        model = Discussion
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Write your reply...'
            }),
        }

# User Management Forms
class UserEditForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone', 'profile_picture', 
                 'user_type', 'company', 'group', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'user_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'user_type_edit'
            }),
            'company': forms.Select(attrs={
                'class': 'form-select',
                'id': 'company_edit'
            }),
            'group': forms.Select(attrs={
                'class': 'form-select',
                'id': 'group_edit'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['profile_picture'].required = False
        
        # Conditionally hide company and group fields based on user type
        if self.instance:
            if self.instance.user_type not in ['CORPORATE_TRAINEE', 'CORPORATE_APPROVER']:
                self.fields['company'].widget = forms.HiddenInput()
            if self.instance.user_type != 'GROUP_TRAINEE':
                self.fields['group'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        
        if user_type in ['CORPORATE_TRAINEE', 'CORPORATE_APPROVER'] and not cleaned_data.get('company'):
            self.add_error('company', "Corporate users must have a company assigned")
        
        if user_type == 'GROUP_TRAINEE' and not cleaned_data.get('group'):
            self.add_error('group', "Group trainees must have a group assigned")
        
        return cleaned_data

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'address', 'billing_details', 'contact_person', 
                 'contact_email', 'contact_phone', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Company name'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Company address'
            }),
            'billing_details': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Billing information'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contact person name'
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contact@company.com'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contact phone number'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

class CompanyUserForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone', 'user_type']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'user_type': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        # Limit user_type choices for company users
        self.fields['user_type'].choices = [
            ('CORPORATE_TRAINEE', 'Corporate Trainee'),
            ('CORPORATE_APPROVER', 'Corporate Approver'),
        ]
        
        if company:
            self.fields['company'] = forms.ModelChoiceField(
                queryset=Company.objects.filter(id=company.id),
                initial=company,
                widget=forms.HiddenInput()
            )

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['rating', 'comment', 'is_public']
        widgets = {
            'rating': forms.Select(attrs={
                'class': 'form-select'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Share your experience with this course...'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize rating choices display
        self.fields['rating'].choices = [
            (5, '★★★★★ - Excellent'),
            (4, '★★★★ - Very Good'),
            (3, '★★★ - Good'),
            (2, '★★ - Fair'),
            (1, '★ - Poor'),
        ]