
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from LMS.models import Company,Group

class CustomUserManager(BaseUserManager):
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)
        
class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    full_name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    password1 = models.CharField(max_length=255, null=True, blank=True)
    password2 = models.CharField(max_length=255, null=True, blank=True)
    first_time_login = models.IntegerField(default=1)  # 1 for True, 0 for False
    last_login = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    role_id = models.BigIntegerField(null=True, blank=True)
    device_token = models.CharField(max_length=255, null=True, blank=True)
    file_category = models.TextField(null=True, blank=True)
    module = models.TextField(null=True, blank=True)

    USER_TYPES = (
        ('rmp', 'Registered Medical Practitioner'),
        ('staff', 'MMC Staff'),
        ('cpd_provider', 'CPD Provider'),
        ('INDIVIDUAL', 'Individual Learner'),
        ('GROUP_LEADER', 'Group Leader'),
        ('GROUP_TRAINEE', 'Group Trainee'),
        ('CORPORATE_TRAINEE', 'Corporate Trainee'),
        ('CORPORATE_APPROVER', 'Corporate Approver'),
        ('ADMIN', 'Admin'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='INDIVIDUAL')
    company = models.ForeignKey('LMS.Company', on_delete=models.SET_NULL, null=True, blank=True)
    group = models.ForeignKey('LMS.Group', on_delete=models.SET_NULL, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    dark_mode = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    last_activity = models.DateTimeField(auto_now=True)
    date_joined = models.DateTimeField(auto_now=True)
    # MMC Fields
    mmc_registration_number = models.CharField(max_length=200, blank=True, null=True, unique=True)
    specialization = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    district = models.CharField(max_length=50, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    
    # CPD Related
    total_cpd_points = models.IntegerField(default=0)
    cpd_points_required = models.IntegerField(default=30)

    # Status
    is_verified = models.BooleanField(default=False)
    registration_status = models.CharField(
        max_length=20,
        choices=(
            ('PROVISIONAL', 'Provisional'),
            ('PERMANENT', 'Permanent'),
            ('EXPIRED', 'Expired'),
            ('SUSPENDED', 'Suspended'),
        ),
        default='PROVISIONAL'
    )

    # Additional fields for staff/admin
    department = models.CharField(max_length=200, null=True, blank=True)
    designation = models.CharField(max_length=200, null=True, blank=True)
    employee_id = models.CharField(max_length=200, null=True, blank=True)

    objects = CustomUserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone']  # Add any additional required fields
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['user_type']),
            models.Index(fields=['is_verified']),
        ]

    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return f"{self.full_name}".strip()
    
    @property
    def profile_picture_url(self):
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        return '/static/images/user.png'

class roles(models.Model):
    id = models.AutoField(primary_key=True)
    role_name = models.TextField(null=True, blank=True)
    role_disc = models.TextField(null=True, blank=True)
    role_type = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True)
    created_by = models.TextField(null=True, blank=True)
    updated_by = models.TextField(null=True, blank=True)
    workflow_view = models.IntegerField(default=0)
    form_view = models.IntegerField(default=0)
    report_view = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'roles'
    
class password_storage(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE,related_name='user_id_repos',blank=True, null=True,db_column='user_id')
    passwordText =models.CharField(max_length=255,null=True,blank=True)
    
    class Meta:
        db_table = 'password_storage'

class error_log(models.Model):
    id = models.AutoField(primary_key=True)
    method =models.TextField(null=True,blank=True)
    error =models.TextField(null=True,blank=True)
    error_date = models.DateTimeField(null=True,blank=True,auto_now_add=True)
    user_id = models.TextField(null=True,blank=True)
    
    class Meta:
        db_table = 'error_log'

class common_model(models.Model):
    name = models.CharField(max_length=255)
    id1 =models.CharField(max_length=255)
    def __str__(self):
        return self.id1    


