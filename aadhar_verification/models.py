from django.db import models
from django.utils import timezone
import logging
from Account.models import CustomUser

logger = logging.getLogger(__name__)

class APIConfig(models.Model):
    name = models.CharField(max_length=100, unique=True)
    api_key = models.CharField(max_length=255)
    api_secret = models.CharField(max_length=255)
    base_url = models.URLField(default='https://api.sandbox.co.in')
    api_version = models.CharField(max_length=10, default='2.0')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "API Configuration"
        verbose_name_plural = "API Configurations"


class APIToken(models.Model):
    config = models.ForeignKey(APIConfig, on_delete=models.CASCADE)
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    token_type = models.CharField(max_length=50, default='Bearer')
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"Token for {self.config.name} - Expires: {self.expires_at}"

    class Meta:
        verbose_name = "API Token"
        verbose_name_plural = "API Tokens"


class AadharVerificationRequest(models.Model):
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('otp_sent', 'OTP Sent'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    aadhaar_number = models.CharField(max_length=12)
    reference_id = models.CharField(max_length=100, blank=True, null=True)
    consent = models.BooleanField(default=True)
    reason = models.TextField(default='Aadhaar Verification')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Aadhar Verification - {self.aadhaar_number} - {self.status}"

    def get_masked_aadhaar(self):
        """Return masked Aadhaar number for display"""
        return f"XXXX XXXX {self.aadhaar_number[-4:]}" if self.aadhaar_number else ""

    def get_status_badge_class(self):
        """Return Bootstrap badge class based on status"""
        status_classes = {
            'initiated': 'bg-secondary',
            'otp_sent': 'bg-warning',
            'verified': 'bg-success',
            'failed': 'bg-danger',
            'expired': 'bg-dark',
        }
        return status_classes.get(self.status, 'bg-secondary')

    class Meta:
        verbose_name = "Aadhar Verification Request"
        verbose_name_plural = "Aadhar Verification Requests"
        ordering = ['-created_at']


class AadharVerificationResult(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('T', 'Transgender'),
    ]

    verification_request = models.OneToOneField(
        AadharVerificationRequest, 
        on_delete=models.CASCADE,
        related_name='verification_result'
    )
    reference_id = models.CharField(max_length=100)
    status = models.CharField(max_length=50)
    message = models.TextField()
    care_of = models.CharField(max_length=255, blank=True, null=True)
    full_address = models.TextField(blank=True, null=True)
    date_of_birth = models.CharField(max_length=20, blank=True, null=True)
    email_hash = models.CharField(max_length=255, blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    year_of_birth = models.IntegerField(blank=True, null=True)
    mobile_hash = models.CharField(max_length=255, blank=True, null=True)
    photo = models.TextField(blank=True, null=True)  # Base64 encoded image
    share_code = models.CharField(max_length=10, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    verified_at = models.DateTimeField(auto_now_add=True)

    # Address breakdown
    country = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    house = models.CharField(max_length=255, blank=True, null=True)
    landmark = models.CharField(max_length=255, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    post_office = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    subdistrict = models.CharField(max_length=100, blank=True, null=True)
    vtc = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Result for {self.verification_request.aadhaar_number} - {self.status}"

    def get_photo_url(self):
        """Convert base64 photo to data URL for display"""
        if self.photo:
            return f"data:image/jpeg;base64,{self.photo}"
        return None

    def get_gender_display(self):
        """Get full gender display name"""
        gender_map = {'M': 'Male', 'F': 'Female', 'T': 'Transgender'}
        return gender_map.get(self.gender, '')

    def get_formatted_address(self):
        """Get formatted address string"""
        address_parts = []
        if self.house:
            address_parts.append(self.house)
        if self.street:
            address_parts.append(self.street)
        if self.landmark:
            address_parts.append(self.landmark)
        if self.vtc:
            address_parts.append(self.vtc)
        if self.district:
            address_parts.append(self.district)
        if self.state:
            address_parts.append(self.state)
        if self.pincode:
            address_parts.append(f"PIN: {self.pincode}")
        if self.country:
            address_parts.append(self.country)
        
        return ', '.join(filter(None, address_parts))

    class Meta:
        verbose_name = "Aadhar Verification Result"
        verbose_name_plural = "Aadhar Verification Results"


class VerificationLog(models.Model):
    LOG_TYPES = [
        ('token_generation', 'Token Generation'),
        ('otp_request', 'OTP Request'),
        ('otp_verification', 'OTP Verification'),
        ('error', 'Error'),
    ]

    log_type = models.CharField(max_length=20, choices=LOG_TYPES)
    request_data = models.JSONField(blank=True, null=True)
    response_data = models.JSONField(blank=True, null=True)
    status_code = models.IntegerField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Verification Log"
        verbose_name_plural = "Verification Logs"
        ordering = ['-created_at']