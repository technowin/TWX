# models.py - COMPLETE IMPLEMENTATION WITH ALL MISSING FIELDS
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from datetime import date, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from Account.models import CustomUser

class RMPProfile(models.Model):
    GENDER_CHOICES = (('M', 'Male'), ('F', 'Female'), ('O', 'Other'))
    CATEGORY_CHOICES = (('GEN', 'General'), ('OBC', 'OBC'), ('SC', 'SC'), ('ST', 'ST'))
    MARITAL_STATUS_CHOICES = (('S', 'Single'), ('M', 'Married'), ('D', 'Divorced'), ('W', 'Widowed'))
    BLOOD_GROUP_CHOICES = (
        ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'), ('AB+', 'AB+'), ('AB-', 'AB-')
    )
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='rmp_profile')
    mmc_registration_number = models.CharField(max_length=20, unique=True)
    prefix = models.CharField(max_length=10, blank=True)
    full_name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100)
    mother_name = models.CharField(max_length=100)
    marital_status = models.CharField(max_length=1, choices=MARITAL_STATUS_CHOICES)
    maiden_name = models.CharField(max_length=100, blank=True)
    husband_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES, blank=True)
    nationality = models.CharField(max_length=50, default='Indian')
    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)
    
    # Address fields
    communication_address = models.TextField()
    communication_city = models.CharField(max_length=50)
    communication_district = models.CharField(max_length=50)
    communication_state = models.CharField(max_length=50, default='Maharashtra')
    communication_pincode = models.CharField(max_length=10)
    
    residential_address = models.TextField()
    clinic_address = models.TextField(blank=True)
    clinic_phone = models.CharField(max_length=15, blank=True)
    
    # Registration details
    registration_date = models.DateField(default=timezone.now)
    registration_valid_till = models.DateField(null=True, blank=True)
    registration_type = models.CharField(max_length=20, default='provisional')
    registration_status = models.CharField(max_length=20, default='active')
    
    # Professional details
    specialization = models.CharField(max_length=100, blank=True)
    sub_specialization = models.CharField(max_length=100, blank=True)
    medical_council = models.CharField(max_length=100, blank=True)
    year_of_graduation = models.IntegerField(null=True, blank=True)
    college_name = models.CharField(max_length=200, blank=True)
    university = models.CharField(max_length=200, blank=True)
    
    # CPD points
    total_cpd_points = models.IntegerField(default=0)
    online_cpd_points = models.IntegerField(default=0)
    offline_cpd_points = models.IntegerField(default=0)
    cpd_points_required = models.IntegerField(default=30)
    cpd_cycle_start = models.DateField(default=timezone.now)
    cpd_cycle_end = models.DateField(null=True, blank=True)
    
    # Additional fields
    aadhaar_number = models.CharField(max_length=12, blank=True)
    pan_number = models.CharField(max_length=10, blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=15, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['mmc_registration_number']),
            models.Index(fields=['registration_status']),
            models.Index(fields=['specialization']),
        ]
    
    def __str__(self):
        return f"{self.mmc_registration_number} - {self.full_name}"
    
    def clean(self):
        if self.date_of_birth and self.date_of_birth > timezone.now().date():
            raise ValidationError('Date of birth cannot be in the future')
        
        if self.year_of_graduation:
            current_year = timezone.now().year
            if self.year_of_graduation < 1950 or self.year_of_graduation > current_year:
                raise ValidationError('Invalid year of graduation')
    
    @property
    def age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    @property
    def needs_renewal(self):
        if self.registration_valid_till:
            return self.registration_valid_till - timezone.now().date() <= timedelta(days=30)
        return False
    
    @property
    def cpd_points_deficit(self):
        return max(0, self.cpd_points_required - self.total_cpd_points)
    
    @property
    def cpd_cycle_progress(self):
        if self.cpd_cycle_start and self.cpd_cycle_end:
            total_days = (self.cpd_cycle_end - self.cpd_cycle_start).days
            days_passed = (timezone.now().date() - self.cpd_cycle_start).days
            return min(100, int((days_passed / total_days) * 100)) if total_days > 0 else 0
        return 0

class EducationalQualification(models.Model):
    QUALIFICATION_TYPES = (
        ('10th', 'Secondary School (10th)'),
        ('12th', 'Higher Secondary (12th)'),
        ('mbbs', 'MBBS'),
        ('md', 'MD'),
        ('ms', 'MS'),
        ('dm', 'DM'),
        ('mch', 'MCh'),
        ('diploma', 'Diploma'),
        ('other', 'Other'),
    )
    
    rmp = models.ForeignKey(RMPProfile, on_delete=models.CASCADE, related_name='educational_qualifications')
    qualification_type = models.CharField(max_length=20, choices=QUALIFICATION_TYPES)
    institution_name = models.CharField(max_length=200)
    board_university = models.CharField(max_length=200)
    roll_number = models.CharField(max_length=50)
    year_of_passing = models.IntegerField(
        validators=[MinValueValidator(1950), MaxValueValidator(2030)]
    )
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    marksheet = models.FileField(
        upload_to='educational_docs/',
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])],
        null=True,
        blank=True
    )
    is_verified = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-year_of_passing']
    
    def __str__(self):
        return f"{self.qualification_type} - {self.institution_name}"

class Subject(models.Model):
    educational_qualification = models.ForeignKey(EducationalQualification, on_delete=models.CASCADE, related_name='subjects')
    subject_name = models.CharField(max_length=100)
    maximum_marks = models.IntegerField()
    obtained_marks = models.IntegerField()
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    result = models.CharField(max_length=10, choices=(('pass', 'Pass'), ('fail', 'Fail')))
    

        
class MedicalQualification(models.Model):
    QUALIFICATION_LEVELS = (
        ('ug', 'Undergraduate'),
        ('pg', 'Postgraduate'),
        ('super_specialty', 'Super Specialty'),
        ('diploma', 'Diploma'),
        ('certificate', 'Certificate'),
    )
    
    rmp = models.ForeignKey(RMPProfile, on_delete=models.CASCADE, related_name='medical_qualifications')
    qualification_level = models.CharField(max_length=20, choices=QUALIFICATION_LEVELS)
    degree_name = models.CharField(max_length=100)
    specialization = models.CharField(max_length=100, blank=True)
    college_name = models.CharField(max_length=200)
    university = models.CharField(max_length=200)
    country = models.CharField(max_length=50, default='India')
    year_of_passing = models.IntegerField()
    duration = models.IntegerField(help_text="Duration in years")
    registration_number = models.CharField(max_length=50, blank=True)
    registration_council = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-year_of_passing']

class Experience(models.Model):
    rmp = models.ForeignKey(RMPProfile, on_delete=models.CASCADE, related_name='experiences')
    organization = models.CharField(max_length=200)
    designation = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    currently_working = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50, default='India')
    
    class Meta:
        ordering = ['-start_date']
    
    @property
    def duration(self):
        if self.currently_working:
            end = timezone.now().date()
        else:
            end = self.end_date or timezone.now().date()
        
        months = (end.year - self.start_date.year) * 12 + (end.month - self.start_date.month)
        years = months // 12
        remaining_months = months % 12
        return f"{years} years, {remaining_months} months"

class Publication(models.Model):
    PUBLICATION_TYPES = (
        ('journal', 'Journal Article'),
        ('conference', 'Conference Paper'),
        ('book', 'Book'),
        ('chapter', 'Book Chapter'),
        ('patent', 'Patent'),
    )
    
    rmp = models.ForeignKey(RMPProfile, on_delete=models.CASCADE, related_name='publications')
    publication_type = models.CharField(max_length=20, choices=PUBLICATION_TYPES)
    title = models.CharField(max_length=300)
    authors = models.TextField()
    journal_name = models.CharField(max_length=200, blank=True)
    volume = models.CharField(max_length=20, blank=True)
    issue = models.CharField(max_length=20, blank=True)
    pages = models.CharField(max_length=20, blank=True)
    publisher = models.CharField(max_length=200, blank=True)
    publication_date = models.DateField()
    doi = models.CharField(max_length=100, blank=True)
    url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-publication_date']

class Award(models.Model):
    rmp = models.ForeignKey(RMPProfile, on_delete=models.CASCADE, related_name='awards')
    award_name = models.CharField(max_length=200)
    awarding_organization = models.CharField(max_length=200)
    year = models.IntegerField()
    description = models.TextField(blank=True)
    certificate_file = models.FileField(upload_to='award_certificates/', null=True, blank=True)
    
    class Meta:
        ordering = ['-year']

# Enhanced Application model with all 23 service types
class Application(models.Model):
    APPLICATION_TYPES = (
        ('provisional', 'Provisional Registration'),
        ('permanent', 'Permanent Registration'),
        ('foreign_provisional', 'Foreign Provisional Registration'),
        ('foreign_permanent', 'Foreign Permanent Registration'),
        ('additional_qualification', 'Additional Qualification Registration'),
        ('renewal', 'Renewal of Registration'),
        ('verification', 'Form Verification'),
        ('address_change', 'Change of Address'),
        ('name_change', 'Change of Name'),
        ('good_standing_mmc', 'Good Standing Certification (MMC)'),
        ('good_standing_nmc', 'Good Standing Certification (NMC)'),
        ('good_standing_nri', 'Good Standing Certificate (NRI)'),
        ('noc_state', 'No Objection Certificate for other state'),
        ('reapplication_noc', 'Reapplication of NOC'),
        ('noc_provisional', 'NOC for Provisional to other state'),
        ('confirmation', 'Confirmation of Registration'),
        ('duplicate', 'Duplication Certificate'),
        ('foreign_verification', 'Foreign Verification Form'),
        ('defaulter', 'Permanent Registration for defaulter RMP'),
        ('reentry', 'Re-enter of Registration'),
        ('termination', 'Termination of RMP'),
        ('manual_verification', 'Manual Document Verification'),
        ('id_card', 'ID Card Generation'),
    )
    
    APPLICATION_STATUS = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('additional_info_required', 'Additional Information Required'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    )
    
    PRIORITY_LEVELS = (
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
        ('priority', 'Priority'),
    )
    
    application_id = models.AutoField(primary_key=True)
    applicant = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='applications')
    application_type = models.CharField(max_length=50, choices=APPLICATION_TYPES)
    rmp = models.ForeignKey(RMPProfile, on_delete=models.CASCADE, related_name='applications')
    application_date = models.DateTimeField(auto_now_add=True)
    submitted_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=30, choices=APPLICATION_STATUS, default='draft')
    current_step = models.IntegerField(default=1)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='normal')
    
    # Application-specific data
    application_data = models.JSONField(default=dict)
    
    # Payment details
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.BooleanField(default=False)
    payment_reference = models.CharField(max_length=100, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    
    # Admin fields
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_applications')
    review_notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_applications')
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Certificate Details
    certificate_generated = models.BooleanField(default=False)
    certificate_number = models.CharField(max_length=50, blank=True, null=True)
    certificate_issue_date = models.DateTimeField(blank=True, null=True)

    # SLA tracking
    sla_days = models.IntegerField(default=15)
    expected_completion_date = models.DateTimeField(null=True, blank=True)
    actual_completion_date = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-submitted_date']
        indexes = [
            models.Index(fields=['application_id']),
            models.Index(fields=['status']),
            models.Index(fields=['application_type']),
            models.Index(fields=['submitted_date']),
        ]
    
    def __str__(self):
        return f"{self.application_id} - {self.get_application_type_display()}"
    
    def save(self, *args, **kwargs):
        if not self.expected_completion_date and self.submitted_date:
            self.expected_completion_date = self.submitted_date + timedelta(days=self.sla_days)
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        if self.expected_completion_date and self.status not in ['completed', 'approved', 'rejected']:
            return timezone.now() > self.expected_completion_date
        return False
    
    @property
    def days_remaining(self):
        if self.expected_completion_date and self.status not in ['completed', 'approved', 'rejected']:
            remaining = self.expected_completion_date - timezone.now()
            return max(0, remaining.days)
        return 0

class ApplicationStep(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='steps')
    step_number = models.IntegerField()
    step_name = models.CharField(max_length=100)
    is_completed = models.BooleanField(default=False)
    completed_date = models.DateTimeField(null=True, blank=True)
    data = models.JSONField(default=dict)
    notes = models.TextField(blank=True)
    required_documents = models.JSONField(default=list)  # List of required document types
    
    class Meta:
        unique_together = ['application', 'step_number']
        ordering = ['step_number']

class Document(models.Model):
    DOCUMENT_TYPES = (
        ('photo', 'Photograph'),
        ('signature', 'Signature'),
        ('ssc', 'SSC Certificate'),
        ('hsc', 'HSC Certificate'),
        ('mci_eligibility', 'MCI Eligibility Certificate'),
        ('screening_test', 'Screening Test Result'),
        ('passport', 'Passport'),
        ('provisional_reg', 'Provisional Registration Certificate'),
        ('internship', 'Internship Certificate'),
        ('affidavit', 'Affidavit'),
        ('embassy_letter', 'Embassy Letter'),
        ('domicile', 'Domicile Certificate'),
        ('degree', 'Degree Certificate'),
        ('address_proof', 'Address Proof'),
        ('birth_certificate', 'Birth Certificate'),
        ('caste_certificate', 'Caste Certificate'),
        ('medical_council_reg', 'Medical Council Registration'),
        ('experience_certificate', 'Experience Certificate'),
        ('publication', 'Publication Proof'),
        ('award', 'Award Certificate'),
        ('research', 'Research Document'),
        ('other', 'Other Document'),
    )
    
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    document_file = models.FileField(
        upload_to='application_documents/%Y/%m/%d/',
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'])]
    )
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField(default=0)  # Size in bytes
    uploaded_date = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    verification_notes = models.TextField(blank=True)
    verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='mmc_documents_verified')
    verified_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['document_type']),
            models.Index(fields=['is_verified']),
        ]
    
    def __str__(self):
        return f"{self.application.application_id} - {self.get_document_type_display()}"
    
    def save(self, *args, **kwargs):
        if self.document_file and not self.file_name:
            self.file_name = self.document_file.name
        if self.document_file and self.file_size == 0:
            self.file_size = self.document_file.size
        super().save(*args, **kwargs)

class Certificate(models.Model):
    CERTIFICATE_TYPES = (
        ('PROVISIONAL', 'Provisional Registration Certificate'),
        ('PERMANENT', 'Permanent Registration Certificate'),
        ('GOOD_STANDING', 'Good Standing Certificate'),
        ('NOC', 'No Objection Certificate'),
        ('DUPLICATE', 'Duplicate Certificate'),
        ('CPD_COMPLETION', 'CPD Completion Certificate'),
    )
    
    certificate_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='certificates')
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='certificates')
    certificate_type = models.CharField(max_length=20, choices=CERTIFICATE_TYPES)
    certificate_number = models.CharField(max_length=50, unique=True)
    issue_date = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField(blank=True, null=True)
    certificate_file = models.FileField(upload_to='certificates/', blank=True, null=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.get_certificate_type_display()} - {self.certificate_number}"
    
class CPDProgram(models.Model):
    PROGRAM_TYPES = (
        ('seminar', 'Seminar'),
        ('workshop', 'Workshop'),
        ('conference', 'Conference'),
        ('online_course', 'Online Course'),
        ('webinar', 'Webinar'),
        ('symposium', 'Symposium'),
        ('training', 'Training Program'),
        ('research', 'Research Presentation'),
    )
    PROGRAM_STATUS = (
        ('Draft', 'Draft'),
        ('Published', 'Published'),
        ('Ongoing', 'Ongoing'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )
    title = models.CharField(max_length=200)
    program_type = models.CharField(max_length=200,choices=PROGRAM_TYPES)
    description = models.TextField()
    detailed_description = models.TextField(blank=True)
    organizer = models.CharField(max_length=200)
    co_organizers = models.TextField(blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    venue = models.TextField()
    max_participants = models.IntegerField()
    cpd_points = models.IntegerField()
    is_online = models.BooleanField(default=False)
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=200,choices=PROGRAM_STATUS, default='DRAFT')
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='mmc_cpd_program')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    # Additional fields
    target_audience = models.TextField(blank=True)
    learning_objectives = models.TextField(blank=True)
    prerequisites = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=15, blank=True)
    website = models.URLField(blank=True)
    
    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['start_date']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.title
    
    def clean(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError('End date must be after start date')
    
    @property
    def is_upcoming(self):
        return self.start_date > timezone.now()
    
    @property
    def is_ongoing(self):
        now = timezone.now()
        return self.start_date <= now <= self.end_date
    
    @property
    def available_slots(self):
        attended_count = self.attendances.count()
        return max(0, self.max_participants - attended_count)
    
    @property
    def registration_status(self):
        if not self.is_active:
            return 'inactive'
        elif self.available_slots == 0:
            return 'full'
        elif self.start_date <= timezone.now():
            return 'ongoing'
        else:
            return 'open'

class CPDAttendance(models.Model):
    ATTENDANCE_STATUS = (
        ('registered', 'Registered'),
        ('attended', 'Attended'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    rmp = models.ForeignKey(RMPProfile, on_delete=models.CASCADE, related_name='cpd_attendances')
    program = models.ForeignKey(CPDProgram, on_delete=models.CASCADE, related_name='attendances')
    registration_date = models.DateTimeField(auto_now_add=True)
    attendance_status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS, default='registered')
    attendance_date = models.DateTimeField(null=True, blank=True)
    points_earned = models.IntegerField()
    certificate_issued = models.BooleanField(default=False)
    certificate_file = models.FileField(upload_to='cpd_certificates/', null=True, blank=True)
    feedback = models.TextField(blank=True)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    payment_status = models.BooleanField(default=False)
    payment_reference = models.CharField(max_length=100, blank=True)
    
    class Meta:
        unique_together = ['rmp', 'program']
        indexes = [
            models.Index(fields=['attendance_status']),
        ]

class Accreditation(models.Model):
    ACCREDITATION_TYPES = (
        ('organization', 'Organization/Association/Institution'),
        ('speaker', 'Speaker'),
        ('faculty', 'Faculty'),
    )
    
    ACCREDITATION_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    )
    
    name = models.CharField(max_length=200)
    accreditation_type = models.CharField(max_length=20, choices=ACCREDITATION_TYPES)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)
    address = models.TextField()
    accreditation_number = models.CharField(max_length=50, unique=True)
    issue_date = models.DateField()
    expiry_date = models.DateField()
    status = models.CharField(max_length=20, choices=ACCREDITATION_STATUS, default='pending')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='mmc_accrediation')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    # Additional fields
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    specialties = models.TextField(blank=True)  # Comma-separated specialties
    review_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['expiry_date']),
        ]
    
    def __str__(self):
        return f"{self.accreditation_number} - {self.name}"
    
    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()
    
    @property
    def days_until_expiry(self):
        return (self.expiry_date - timezone.now().date()).days

class CPDParticipation(models.Model):
    ATTENDANCE_STATUS = (
        ('REGISTERED', 'Registered'),
        ('ATTENDED', 'Attended'),
        ('COMPLETED', 'Completed'),
        ('ABSENT', 'Absent'),
        ('CANCELLED', 'Cancelled'),
    )
    
    participant = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='cpd_participations')
    program = models.ForeignKey(CPDProgram, on_delete=models.CASCADE, related_name='participations')
    registration_date = models.DateTimeField(auto_now_add=True)
    attendance_status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS, default='REGISTERED')
    
    # Completion details
    completion_date = models.DateTimeField(blank=True, null=True)
    certificate_issued = models.BooleanField(default=False)
    certificate_number = models.CharField(max_length=50, blank=True, null=True)
    certificate_issue_date = models.DateTimeField(blank=True, null=True)
    points_earned = models.IntegerField(default=0)
    
    # Feedback
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    feedback_date = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        unique_together = ['participant', 'program']
        ordering = ['-registration_date']
    
    def __str__(self):
        return f"{self.participant} - {self.program.title}"
    
    def save(self, *args, **kwargs):
        # Auto-set completion date and points when status changes to COMPLETED
        if self.attendance_status == 'COMPLETED' and not self.completion_date:
            self.completion_date = timezone.now()
            if not self.points_earned:
                self.points_earned = self.program.cpd_points
            
            # Update user's total CPD points
            self.participant.total_cpd_points += self.points_earned
            self.participant.save()
        
        # Generate certificate number if not exists
        if self.certificate_issued and not self.certificate_number:
            self.certificate_number = f"CPD{timezone.now().strftime('%Y%m%d%H%M%S')}"
            self.certificate_issue_date = timezone.now()
        
        super().save(*args, **kwargs)
class Payment(models.Model):
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    )
    
    PAYMENT_METHODS = (
        ('online', 'Online Payment'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('dd', 'Demand Draft'),
    )
    
    payment_id = models.AutoField(primary_key=True)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='online')
    transaction_id = models.CharField(max_length=100, blank=True)
    bank_reference = models.CharField(max_length=100, blank=True)
    payment_gateway_response = models.JSONField(default=dict)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_reason = models.TextField(blank=True)
    refund_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['payment_date']),
        ]

class Complaint(models.Model):
    COMPLAINT_STATUS = (
        ('registered', 'Registered'),
        ('under_investigation', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
        ('reopened', 'Reopened'),
    )
    
    SEVERITY_LEVELS = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    
    complaint_id = models.AutoField(primary_key=True)
    against_rmp = models.ForeignKey(RMPProfile, on_delete=models.CASCADE, related_name='complaints_against')
    filed_by = models.ForeignKey(RMPProfile, on_delete=models.CASCADE, related_name='complaints_filed')
    complaint_text = models.TextField()
    filed_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30, choices=COMPLAINT_STATUS, default='registered')
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='medium')
    resolution_text = models.TextField(blank=True)
    resolved_date = models.DateTimeField(null=True, blank=True)
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='mmc_complaints')
    
    # Additional fields
    category = models.CharField(max_length=100, blank=True)
    sub_category = models.CharField(max_length=100, blank=True)
    evidence_documents = models.ManyToManyField(Document, blank=True, related_name='complaint_evidence')
    
    class Meta:
        ordering = ['-filed_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['severity']),
        ]

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('registration', 'Registration Update'),
        ('cpd', 'CPD Program'),
        ('complaint', 'Complaint Update'),
        ('payment', 'Payment Status'),
        ('system', 'System Notification'),
        ('renewal', 'Renewal Reminder'),
        ('deadline', 'Deadline Alert'),
        ('approval', 'Approval Notification'),
        ('rejection', 'Rejection Notification'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='mmc_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)
    related_object_id = models.CharField(max_length=100, blank=True)
    action_url = models.CharField(max_length=200, blank=True)
    priority = models.CharField(max_length=10, choices=(('low', 'Low'), ('medium', 'Medium'), ('high', 'High')), default='medium')
    
    class Meta:
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type']),
        ]

class TerminationRequest(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='termination_request')
    termination_reason = models.TextField()
    termination_date = models.DateField()
    supporting_documents = models.FileField(upload_to='termination_docs/')
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_terminations')
    approval_date = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"Termination - {self.application.applicant.get_full_name()}"

class GoodStandingRequest(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='good_standing_request')
    purpose = models.TextField()
    country = models.CharField(max_length=100)
    receiving_authority = models.CharField(max_length=200)
    authority_address = models.TextField()
    delivery_method = models.CharField(max_length=20, choices=[('EMAIL', 'Email'), ('POST', 'Postal')])
    
    def __str__(self):
        return f"Good Standing - {self.application.applicant.get_full_name()}"

class NOCRequest(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='noc_request')
    destination_state = models.CharField(max_length=100)
    destination_council = models.CharField(max_length=200)
    reason_for_transfer = models.TextField()
    expected_departure_date = models.DateField()
    
    def __str__(self):
        return f"NOC - {self.application.applicant.get_full_name()}"

class ChangeRequest(models.Model):
    CHANGE_TYPES = (
        ('NAME', 'Change of Name'),
        ('ADDRESS', 'Change of Address'),
        ('QUALIFICATION', 'Additional Qualification'),
    )
    
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='change_request')
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPES)
    old_value = models.TextField()
    new_value = models.TextField()
    supporting_documents = models.FileField(upload_to='change_request_docs/')
    
    def __str__(self):
        return f"{self.get_change_type_display()} - {self.application.applicant.get_full_name()}"

class VerificationTask(models.Model):
    TASK_STATUS = (
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('OVERDUE', 'Overdue'),
    )

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='verification_tasks')
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='verification_tasks')
    assigned_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    completed_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=TASK_STATUS, default='PENDING')
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Verification - {self.application.application_id}"


# AI Integration Models
class AIPerformanceScore(models.Model):
    rmp = models.OneToOneField(RMPProfile, on_delete=models.CASCADE, related_name='ai_score')
    overall_score = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    cpd_score = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    compliance_score = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    patient_care_score = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    professional_conduct_score = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    research_score = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)], default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    # Detailed breakdown
    score_breakdown = models.JSONField(default=dict)
    
    class Meta:
        verbose_name = "AI Performance Score"
        verbose_name_plural = "AI Performance Scores"

class AIInsight(models.Model):
    INSIGHT_TYPES = (
        ('performance', 'Performance Insight'),
        ('compliance', 'Compliance Alert'),
        ('cpd', 'CPD Recommendation'),
        ('risk', 'Risk Assessment'),
        ('opportunity', 'Growth Opportunity'),
        ('deadline', 'Deadline Alert'),
        ('trend', 'Performance Trend'),
    )
    
    rmp = models.ForeignKey(RMPProfile, on_delete=models.CASCADE, related_name='ai_insights')
    insight_type = models.CharField(max_length=20, choices=INSIGHT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    severity = models.CharField(max_length=10, choices=(('low', 'Low'), ('medium', 'Medium'), ('high', 'High')), default='medium')
    generated_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    action_items = models.JSONField(default=list)
    confidence_level = models.DecimalField(max_digits=3, decimal_places=2, default=0.8)
    
    class Meta:
        ordering = ['-generated_date']
        indexes = [
            models.Index(fields=['rmp', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.rmp.mmc_registration_number} - {self.insight_type}"

class PredictiveAlert(models.Model):
    ALERT_TYPES = (
        ('renewal', 'Registration Renewal'),
        ('cpd_deficit', 'CPD Points Deficit'),
        ('complaint_risk', 'High Complaint Risk'),
        ('document_expiry', 'Document Expiry'),
        ('payment_due', 'Payment Due'),
        ('deadline', 'Upcoming Deadline'),
        ('performance_drop', 'Performance Drop'),
        ('sla_breach', 'SLA Breach Alert'),
    )
    
    rmp = models.ForeignKey(RMPProfile, on_delete=models.CASCADE, related_name='predictive_alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.TextField()
    predicted_date = models.DateField()
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(1)])
    generated_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_dismissed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-generated_date']
        indexes = [
            models.Index(fields=['rmp', 'is_active']),
        ]

# Report Models
class Report(models.Model):
    REPORT_TYPES = (
        ('payment_summary', 'Payment Summary'),
        ('application_status', 'Application Status'),
        ('cpd_participation', 'CPD Participation'),
        ('staff_performance', 'Staff Performance'),
        ('revenue_analysis', 'Revenue Analysis'),
        ('registration_trends', 'Registration Trends'),
        ('complaint_analysis', 'Complaint Analysis'),
        ('ai_performance', 'AI Performance Report'),
        ('sla_compliance', 'SLA Compliance Report'),
    )
    
    report_id = models.AutoField(primary_key=True)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)
    generated_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='mmc_reports')
    generated_date = models.DateTimeField(auto_now_add=True)
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    report_data = models.JSONField(default=dict)
    file_path = models.FileField(upload_to='reports/', null=True, blank=True)
    is_scheduled = models.BooleanField(default=False)
    schedule_frequency = models.CharField(max_length=20, blank=True, choices=(
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ))
    
    class Meta:
        ordering = ['-generated_date']

class IDCard(models.Model):
    rmp = models.OneToOneField(RMPProfile, on_delete=models.CASCADE, related_name='id_card')
    card_number = models.CharField(max_length=20, unique=True)
    issue_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True)
    photo = models.ImageField(upload_to='id_card_photos/')
    signature = models.ImageField(upload_to='id_card_signatures/')
    is_active = models.BooleanField(default=True)
    generated_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='mmc_idcard')
    
    
    def __str__(self):
        return f"ID Card - {self.card_number}"

# Audit Log Model
class AuditLog(models.Model):
    ACTION_TYPES = (
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('view', 'View'),
        ('download', 'Download'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='mmc_auditlog')
    action_type = models.CharField(max_length=10, choices=ACTION_TYPES)
    model_name = models.CharField(max_length=50)
    object_id = models.CharField(max_length=100)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action_type']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.action_type} - {self.model_name}"

# System Configuration Model
class SystemConfig(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    data_type = models.CharField(max_length=20, choices=(
        ('string', 'String'),
        ('integer', 'Integer'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
    ), default='string')
    is_active = models.BooleanField(default=True)
    updated_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='mmc_sys_config')
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "System Configuration"
        verbose_name_plural = "System Configurations"
    
    def __str__(self):
        return self.key