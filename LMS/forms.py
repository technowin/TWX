
# User Management System

# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import *
from Account.models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)
    user_type = forms.ChoiceField(choices=CustomUser.USER_TYPES)
    company = forms.ModelChoiceField(queryset=Company.objects.all(), required=False)
    group = forms.ModelChoiceField(queryset=Group.objects.all(), required=False)
    
    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'password1', 'password2', 'user_type', 'phone', 'company', 'group')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = Company.objects.all()
        self.fields['group'].queryset = Group.objects.all()
        
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
    
    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        company = cleaned_data.get('company')
        group = cleaned_data.get('group')
        
        if user_type == 'CORPORATE_TRAINEE' and not company:
            raise forms.ValidationError("Corporate trainees must select a company")
        if user_type == 'GROUP_TRAINEE' and not group:
            raise forms.ValidationError("Group trainees must select a group")
        
        return cleaned_data

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'phone', 'profile_picture', 'dark_mode')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.fields['profile_picture'].widget.attrs.update({'class': 'form-control-file'})


# Course Management

# forms.py
class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'slug', 'description', 'short_description', 'instructor', 'category', 
                 'level', 'duration', 'price', 'discount_price', 'thumbnail', 'is_featured', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'short_description': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.fields['thumbnail'].widget.attrs.update({'class': 'form-control-file'})
        self.fields['instructor'].queryset = CustomUser.objects.filter(is_staff=True)

class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['title', 'description', 'order', 'is_free']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'description', 'video_url', 'video_file', 'duration', 'order', 'is_free']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.fields['video_file'].widget.attrs.update({'class': 'form-control-file'})
    
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.fields['file'].widget.attrs.update({'class': 'form-control-file'})


# Enrollment & Access Control

# forms.py
class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['user', 'course', 'status', 'is_paid', 'payment_amount', 'payment_method', 'transaction_id']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class CorporateEnrollmentForm(forms.ModelForm):
    class Meta:
        model = CorporateEnrollment
        fields = ['company', 'course', 'purchased_seats', 'payment_amount', 'payment_method', 'transaction_id', 'access_expiry']
        widgets = {
            'access_expiry': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class CorporateEnrollmentRequestForm(forms.ModelForm):
    class Meta:
        model = CorporateEnrollmentRequest
        fields = ['corporate_enrollment', 'user', 'comments']
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if company:
            self.fields['corporate_enrollment'].queryset = CorporateEnrollment.objects.filter(company=company)
            self.fields['user'].queryset = CustomUser.objects.filter(company=company, user_type='CORPORATE_TRAINEE')
        
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})


# Learning Experience

# forms.py
class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['content', 'is_private']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class BookmarkForm(forms.ModelForm):
    class Meta:
        model = Bookmark
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['notes'].widget.attrs.update({'class': 'form-control'})

class DiscussionForm(forms.ModelForm):
    class Meta:
        model = Discussion
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ask a question or share your thoughts...'
        })

class ReplyForm(forms.ModelForm):
    class Meta:
        model = Discussion
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Write your reply...'
        })


# forms.py
class UserEditForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone', 'profile_picture', 
                 'user_type', 'company', 'group', 'is_active']
        widgets = {
            'user_type': forms.Select(attrs={'class': 'form-control'}),
            'company': forms.Select(attrs={'class': 'form-control'}),
            'group': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.fields['profile_picture'].widget.attrs.update({'class': 'form-control-file'})
        
        # Make company and group fields conditional
        self.fields['company'].queryset = Company.objects.all()
        self.fields['group'].queryset = Group.objects.all()
        
        if 'instance' in kwargs:
            user = kwargs['instance']
            if user.user_type not in ['CORPORATE_TRAINEE', 'CORPORATE_APPROVER']:
                self.fields['company'].widget = forms.HiddenInput()
            if user.user_type != 'GROUP_TRAINEE':
                self.fields['group'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        
        if user_type in ['CORPORATE_TRAINEE', 'CORPORATE_APPROVER'] and not cleaned_data.get('company'):
            raise forms.ValidationError("Corporate users must have a company assigned")
        
        if user_type == 'GROUP_TRAINEE' and not cleaned_data.get('group'):
            raise forms.ValidationError("Group trainees must have a group assigned")
        
        return cleaned_data
    

# forms.py
class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'address', 'billing_details', 'contact_person', 
                 'contact_email', 'contact_phone', 'is_active']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'billing_details': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class CompanyUserForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone', 'user_type']
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        # Limit user_type choices for company users
        self.fields['user_type'].choices = [
            ('CORPORATE_TRAINEE', 'Corporate Trainee'),
            ('CORPORATE_APPROVER', 'Corporate Approver'),
        ]
        
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        if company:
            self.fields['company'] = forms.ModelChoiceField(
                queryset=Company.objects.filter(id=company.id),
                initial=company,
                widget=forms.HiddenInput()
            )

# forms.py
class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['rating', 'comment', 'is_public']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Share your experience with this course...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.fields['is_public'].widget.attrs.update({'class': 'form-check-input'})