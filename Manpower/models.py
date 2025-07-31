# models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from MachinePlan.models import MachinePlanning, WorkCenter, Routing

class Employee(models.Model):
    employee_code = models.CharField(max_length=10, unique=True, verbose_name="Employee ID")
    employee_name = models.CharField(max_length=100, verbose_name="Full Name")
    work_center = models.ForeignKey(WorkCenter, on_delete=models.PROTECT, verbose_name="Primary Work Center")
    hire_date = models.DateField(verbose_name="Hire Date", null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Active Employee")
    contact_number = models.CharField(max_length=15, blank=True, verbose_name="Contact Number")
    email = models.EmailField(blank=True, verbose_name="Email Address")
    
    class Meta:
        ordering = ['employee_name']
        verbose_name = "Employee"
        verbose_name_plural = "Employees"
    
    def __str__(self):
        return f"{self.employee_code} - {self.employee_name}"

class Skill(models.Model):
    skill_code = models.CharField(max_length=10, unique=True, verbose_name="Skill Code")
    skill_name = models.CharField(max_length=50, verbose_name="Skill Name")
    description = models.TextField(blank=True, verbose_name="Description")
    
    class Meta:
        ordering = ['skill_name']
        verbose_name = "Skill"
        verbose_name_plural = "Skills"
    
    def __str__(self):
        return f"{self.skill_code} - {self.skill_name}"

class EmployeeSkill(models.Model):
    PROFICIENCY_CHOICES = [
        (1, 'Basic Knowledge'),
        (2, 'Novice'),
        (3, 'Competent'),
        (4, 'Proficient'),
        (5, 'Expert'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    proficiency = models.PositiveSmallIntegerField(
        choices=PROFICIENCY_CHOICES,
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    certification_date = models.DateField(null=True, blank=True, verbose_name="Certification Date")
    certified_by = models.CharField(max_length=100, blank=True, verbose_name="Certified By")
    
    class Meta:
        unique_together = ('employee', 'skill')
        verbose_name = "Employee Skill"
        verbose_name_plural = "Employee Skills"
    
    def __str__(self):
        return f"{self.employee} - {self.skill} (Level {self.proficiency})"

class Shift(models.Model):
    shift_code = models.CharField(max_length=10, unique=True, verbose_name="Shift Code")
    shift_name = models.CharField(max_length=50, verbose_name="Shift Name")
    start_time = models.TimeField(verbose_name="Start Time")
    end_time = models.TimeField(verbose_name="End Time")
    description = models.CharField(max_length=100, blank=True, verbose_name="Description")
    is_active = models.BooleanField(default=True, verbose_name="Active Shift")
    
    class Meta:
        ordering = ['start_time']
        verbose_name = "Shift"
        verbose_name_plural = "Shifts"
    
    def __str__(self):
        return f"{self.shift_code} - {self.shift_name} ({self.start_time.strftime('%H:%M')} to {self.end_time.strftime('%H:%M')})"

class LaborRequirement(models.Model):
    routing = models.ForeignKey(Routing, on_delete=models.CASCADE, related_name='labor_requirements')
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT, verbose_name="Required Skill")
    employees_needed = models.PositiveSmallIntegerField(default=1, verbose_name="Employees Needed")
    min_proficiency = models.PositiveSmallIntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Minimum Proficiency"
    )
    notes = models.TextField(blank=True, verbose_name="Additional Notes")
    
    class Meta:
        verbose_name = "Labor Requirement"
        verbose_name_plural = "Labor Requirements"
        unique_together = ('routing', 'skill')
    
    def __str__(self):
        return f"{self.routing} requires {self.employees_needed} {self.skill} (min level {self.min_proficiency})"

class LaborAssignment(models.Model):
    schedule = models.ForeignKey(MachinePlanning, on_delete=models.CASCADE, related_name='labor_assignments')
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, verbose_name="Assigned Employee")
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, verbose_name="Assigned Shift")
    date = models.DateField(verbose_name="Assignment Date")
    hours_allocated = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0.25), MaxValueValidator(24)],
        verbose_name="Hours Allocated"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('planned', 'Planned'),
            ('confirmed', 'Confirmed'),
            ('completed', 'Completed'),
            ('absent', 'Absent'),
            ('reassigned', 'Reassigned'),
        ],
        default='planned',
        verbose_name="Assignment Status"
    )
    notes = models.TextField(blank=True, verbose_name="Assignment Notes")
    
    class Meta:
        verbose_name = "Labor Assignment"
        verbose_name_plural = "Labor Assignments"
        ordering = ['date', 'shift__start_time']
    
    def __str__(self):
        return f"{self.employee} assigned to {self.schedule} on {self.date}"

class EmployeeAvailability(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='availabilities')
    date = models.DateField(verbose_name="Date")
    is_available = models.BooleanField(default=True, verbose_name="Is Available")
    reason = models.CharField(max_length=100, blank=True, verbose_name="Reason for Unavailability")
    notes = models.TextField(blank=True, verbose_name="Additional Notes")
    
    class Meta:
        verbose_name = "Employee Availability"
        verbose_name_plural = "Employee Availabilities"
        unique_together = ('employee', 'date')
    
    def __str__(self):
        return f"{self.employee} availability on {self.date}: {'Available' if self.is_available else 'Unavailable'}"

class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(verbose_name="Date")
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, verbose_name="Shift")
    clock_in = models.DateTimeField(null=True, blank=True, verbose_name="Clock In Time")
    clock_out = models.DateTimeField(null=True, blank=True, verbose_name="Clock Out Time")
    status = models.CharField(
        max_length=20,
        choices=[
            ('present', 'Present'),
            ('absent', 'Absent'),
            ('late', 'Late Arrival'),
            ('left_early', 'Left Early'),
            ('on_leave', 'On Leave'),
        ],
        default='present',
        verbose_name="Attendance Status"
    )
    overtime_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        verbose_name="Overtime Hours"
    )
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"
        unique_together = ('employee', 'date')
    
    def __str__(self):
        return f"{self.employee} attendance on {self.date}: {self.status}"

class LeaveRequest(models.Model):
    LEAVE_TYPES = [
        ('vacation', 'Vacation'),
        ('sick', 'Sick Leave'),
        ('personal', 'Personal Leave'),
        ('bereavement', 'Bereavement Leave'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES, verbose_name="Leave Type")
    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(verbose_name="End Date")
    reason = models.TextField(verbose_name="Reason for Leave")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leave_requests',
        verbose_name="Approved By"
    )
    approval_date = models.DateTimeField(null=True, blank=True, verbose_name="Approval Date")
    notes = models.TextField(blank=True, verbose_name="Approver Notes")
    
    class Meta:
        verbose_name = "Leave Request"
        verbose_name_plural = "Leave Requests"
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.employee} - {self.get_leave_type_display()} from {self.start_date} to {self.end_date} ({self.status})"