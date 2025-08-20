
# User Management System

# models.py
from datetime import timezone
import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
# from Account.models import CustomUser

class Company(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    billing_details = models.TextField()
    contact_person = models.CharField(max_length=255)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Group(models.Model):
    name = models.CharField(max_length=255)
    leader = models.ForeignKey('Account.CustomUser', on_delete=models.SET_NULL, null=True, related_name='led_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

# class User(AbstractUser):
#     USER_TYPES = (
#         ('INDIVIDUAL', 'Individual Learner'),
#         ('GROUP_LEADER', 'Group Leader'),
#         ('GROUP_TRAINEE', 'Group Trainee'),
#         ('CORPORATE_TRAINEE', 'Corporate Trainee'),
#         ('CORPORATE_APPROVER', 'Corporate Approver'),
#         ('ADMIN', 'Admin'),
#     )
    
#     user_type = models.CharField(max_length=20, choices=USER_TYPES, default='INDIVIDUAL')
#     phone = models.CharField(max_length=20, blank=True, null=True)
#     company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
#     group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)
#     profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
#     dark_mode = models.BooleanField(default=False)
#     email_verified = models.BooleanField(default=False)
#     phone_verified = models.BooleanField(default=False)
#     last_activity = models.DateTimeField(auto_now=True)

    
#     def __str__(self):
#         return self.email

#     def save(self, *args, **kwargs):
#         # Ensure user_type consistency
#         if self.user_type == 'CORPORATE_TRAINEE' and not self.company:
#             raise ValueError("Corporate trainees must have a company")
#         if self.user_type == 'GROUP_TRAINEE' and not self.group:
#             raise ValueError("Group trainees must have a group")
#         super().save(*args, **kwargs)


# Course Management

# models.py
class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='category_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Course(models.Model):
    LEVEL_CHOICES = (
        ('BEGINNER', 'Beginner'),
        ('INTERMEDIATE', 'Intermediate'),
        ('ADVANCED', 'Advanced'),
    )
    
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300)
    instructor = models.ForeignKey('Account.CustomUser', on_delete=models.CASCADE, limit_choices_to={'is_staff': True})
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='BEGINNER')
    duration = models.PositiveIntegerField(help_text="Duration in hours")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    thumbnail = models.ImageField(upload_to='course_thumbnails/')
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    students = models.ManyToManyField('Account.CustomUser', related_name='courses_enrolled', blank=True)
    wishlist = models.ManyToManyField('Account.CustomUser', related_name='wishlisted_courses', blank=True)

    def __str__(self):
        return self.title

    @property
    def is_free(self):
        return self.price == 0

    @property
    def current_price(self):
        return self.discount_price if self.discount_price else self.price

class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField()
    is_free = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    video_url = models.URLField(blank=True, null=True)
    video_file = models.FileField(upload_to='lesson_videos/', blank=True, null=True)
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    order = models.PositiveIntegerField()
    is_free = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.module.title} - {self.title}"

    @property
    def video_type(self):
        if self.video_url:
            return 'url'
        elif self.video_file:
            return 'file'
        return None

class Resource(models.Model):
    RESOURCE_TYPES = (
        ('PDF', 'PDF Document'),
        ('DOC', 'Word Document'),
        ('PPT', 'PowerPoint'),
        ('ZIP', 'Zip Archive'),
        ('OTHER', 'Other'),
    )
    
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='lesson_resources/')
    resource_type = models.CharField(max_length=10, choices=RESOURCE_TYPES)
    is_free = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def get_extension(self):
        return self.file.name.split('.')[-1].upper()
    

# Enrollment & Access Control

# models.py
class Enrollment(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )
    
    user = models.ForeignKey('Account.CustomUser', on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrollment_date = models.DateTimeField(auto_now_add=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    is_paid = models.BooleanField(default=False)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    approved_by = models.ForeignKey('Account.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_enrollments')
    approved_date = models.DateTimeField(null=True, blank=True)
    access_expiry = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user.email} - {self.course.title}"

    @property
    def progress(self):
        total_lessons = sum(module.lessons.count() for module in self.course.modules.all())
        if total_lessons == 0:
            return 0
        completed_lessons = self.lesson_completions.count()
        return round((completed_lessons / total_lessons) * 100)

    def save(self, *args, **kwargs):
        if self.status == 'COMPLETED' and not self.completion_date:
            self.completion_date = timezone.now()
        super().save(*args, **kwargs)

class LessonCompletion(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='lesson_completions')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('enrollment', 'lesson')

    def __str__(self):
        return f"{self.enrollment.user.email} completed {self.lesson.title}"

class CorporateEnrollment(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    purchased_seats = models.PositiveIntegerField()
    used_seats = models.PositiveIntegerField(default=0)
    purchased_by = models.ForeignKey('Account.CustomUser', on_delete=models.SET_NULL, null=True, related_name='corporate_purchases')
    purchase_date = models.DateTimeField(auto_now_add=True)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100)
    access_expiry = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    @property
    def remaining_seats(self):
        return self.purchased_seats - self.used_seats

    def __str__(self):
        return f"{self.company.name} - {self.course.title}"

class CorporateEnrollmentRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    
    corporate_enrollment = models.ForeignKey(CorporateEnrollment, on_delete=models.CASCADE)
    user = models.ForeignKey('Account.CustomUser', on_delete=models.CASCADE)
    requested_by = models.ForeignKey('Account.CustomUser', on_delete=models.SET_NULL, null=True, related_name='corporate_requests')
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    processed_by = models.ForeignKey('Account.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_requests')
    processed_date = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ('corporate_enrollment', 'user')

    def __str__(self):
        return f"{self.user.email} - {self.corporate_enrollment.course.title}"

    def approve(self, approver):
        if self.status != 'PENDING':
            return False
        
        if self.corporate_enrollment.remaining_seats <= 0:
            return False
        
        self.status = 'APPROVED'
        self.processed_by = approver
        self.processed_date = timezone.now()
        self.save()
        
        # Create the actual enrollment
        Enrollment.objects.create(
            user=self.user,
            course=self.corporate_enrollment.course,
            status='ACTIVE',
            is_paid=True,
            payment_amount=0,
            approved_by=approver,
            approved_date=timezone.now(),
            access_expiry=self.corporate_enrollment.access_expiry
        )
        
        # Update used seats
        self.corporate_enrollment.used_seats += 1
        self.corporate_enrollment.save()
        
        return True

    def reject(self, approver, comments=None):
        if self.status != 'PENDING':
            return False
        
        self.status = 'REJECTED'
        self.processed_by = approver
        self.processed_date = timezone.now()
        self.comments = comments
        self.save()
        return True
    

# Payment & Subscription

# models.py
class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('RAZORPAY', 'Razorpay'),
        ('UPI', 'UPI'),
        ('CARD', 'Credit/Debit Card'),
        ('NET_BANKING', 'Net Banking'),
        ('WALLET', 'Wallet'),
        ('OFFLINE', 'Offline Payment'),
    )
    
    user = models.ForeignKey('Account.CustomUser', on_delete=models.SET_NULL, null=True, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=100, unique=True)
    invoice_id = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=100, null=True, blank=True)
    billing_name = models.CharField(max_length=255, null=True, blank=True)
    billing_email = models.EmailField(null=True, blank=True)
    billing_phone = models.CharField(max_length=20, null=True, blank=True)
    billing_address = models.TextField(null=True, blank=True)
    notes = models.JSONField(default=dict)

    def __str__(self):
        return f"Payment #{self.id} - {self.amount} {self.currency}"

    def save(self, *args, **kwargs):
        if not self.invoice_id:
            self.invoice_id = f"INV-{timezone.now().strftime('%Y%m%d')}-{str(self.id).zfill(5)}"
        super().save(*args, **kwargs)

class Order(models.Model):
    ORDER_STATUS_CHOICES = (
        ('CREATED', 'Created'),
        ('PAID', 'Paid'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    )
    
    user = models.ForeignKey('Account.CustomUser', on_delete=models.SET_NULL, null=True, related_name='orders')
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='CREATED')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.JSONField(default=dict)

    def __str__(self):
        return f"Order #{self.id}"

    @property
    def total_amount(self):
        return self.amount - self.discount_amount + self.tax_amount

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity} x {self.course.title if self.course else 'Course'}"

class Coupon(models.Model):
    COUPON_TYPES = (
        ('PERCENTAGE', 'Percentage'),
        ('FIXED', 'Fixed Amount'),
    )
    
    code = models.CharField(max_length=20, unique=True)
    coupon_type = models.CharField(max_length=20, choices=COUPON_TYPES)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    uses = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('Account.CustomUser', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.code

    def is_valid(self, user=None):
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_to:
            return False
        if self.max_uses and self.uses >= self.max_uses:
            return False
        return True

    def apply_discount(self, amount):
        if self.coupon_type == 'PERCENTAGE':
            return amount * (self.value / 100)
        else:
            return min(self.value, amount)
        

# Learning Experience

# models.py
class Certificate(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name='certificate')
    certificate_id = models.CharField(max_length=20, unique=True)
    issued_date = models.DateTimeField(auto_now_add=True)
    download_count = models.PositiveIntegerField(default=0)
    verification_url = models.URLField(unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Certificate for {self.enrollment.course.title} - {self.enrollment.user.email}"

    def save(self, *args, **kwargs):
        if not self.certificate_id:
            self.certificate_id = f"CERT-{timezone.now().strftime('%Y%m%d')}-{str(self.enrollment.id).zfill(5)}"
        if not self.verification_url:
            self.verification_url = f"{settings.SITE_URL}/verify/{uuid.uuid4()}"
        super().save(*args, **kwargs)

class Note(models.Model):
    user = models.ForeignKey('Account.CustomUser', on_delete=models.CASCADE, related_name='notes')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='notes')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_private = models.BooleanField(default=True)

    def __str__(self):
        return f"Note by {self.user.email} on {self.lesson.title}"

class Bookmark(models.Model):
    user = models.ForeignKey('Account.CustomUser', on_delete=models.CASCADE, related_name='bookmarks')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('user', 'lesson')

    def __str__(self):
        return f"Bookmark by {self.user.email} on {self.lesson.title}"

class Discussion(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='discussions')
    user = models.ForeignKey('Account.CustomUser', on_delete=models.CASCADE, related_name='discussions')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_resolved = models.BooleanField(default=False)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    def __str__(self):
        return f"Discussion by {self.user.email} on {self.lesson.title}"

class DiscussionVote(models.Model):
    VOTE_TYPES = (
        ('UP', 'Upvote'),
        ('DOWN', 'Downvote'),
    )
    
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey('Account.CustomUser', on_delete=models.CASCADE, related_name='votes')
    vote_type = models.CharField(max_length=4, choices=VOTE_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('discussion', 'user')

    def __str__(self):
        return f"{self.get_vote_type_display()} by {self.user.email} on discussion #{self.discussion.id}"
    

# Notification 

# models.py
class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('ENROLLMENT', 'Enrollment'),
        ('COURSE_UPDATE', 'Course Update'),
        ('DISCUSSION_REPLY', 'Discussion Reply'),
        ('PAYMENT', 'Payment'),
        ('SYSTEM', 'System'),
    )
    
    user = models.ForeignKey('Account.CustomUser', on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=100)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_url = models.URLField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.user.email}"
    

# Feedback 

# models.py
class Feedback(models.Model):
    RATING_CHOICES = (
        (1, '1 Star - Poor'),
        (2, '2 Stars - Fair'),
        (3, '3 Stars - Good'),
        (4, '4 Stars - Very Good'),
        (5, '5 Stars - Excellent'),
    )
    
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='feedbacks')
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=False)

    class Meta:
        unique_together = ('enrollment',)

    def __str__(self):
        return f"Feedback for {self.enrollment.course.title} by {self.enrollment.user.email}"
    
