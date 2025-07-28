from django.db import models

# Create your models here.
# machineplan/models.py
from django.db import models
from django.urls import reverse
from BOM.models import BOMHeader
from django.contrib.auth import get_user_model

CustomUser = get_user_model()

class MachineType(models.Model):
    """Different types of machines available"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Machine Type"
        verbose_name_plural = "Machine Types"
        ordering = ['name']

    def __str__(self):
        return self.name
    

class Machine(models.Model):
    """Individual machines in the facility"""
    STATUS_CHOICES = [
        ('OP', 'Operational'),
        ('MN', 'Maintenance'),
        ('OO', 'Out of Order'),
        ('RT', 'Retired'),
    ]
    
    machine_id = models.CharField(max_length=50, unique=True, verbose_name="Machine ID")
    name = models.CharField(max_length=100)
    machine_type = models.ForeignKey(MachineType, on_delete=models.PROTECT)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default='OP')
    manufacturer = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=50, blank=True)
    serial_number = models.CharField(max_length=50, blank=True)
    installation_date = models.DateField(null=True, blank=True)
    capacity = models.CharField(max_length=100, help_text="Machine capacity (e.g., 100 units/hour)")
    operational_hours_per_day = models.DecimalField(
        max_digits=4, 
        decimal_places=1,
        default=8.0,
        help_text="Standard operational hours per day"
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Machine"
        verbose_name_plural = "Machines"
        ordering = ['machine_id']

    def __str__(self):
        return f"{self.machine_id} - {self.name}"

    def get_absolute_url(self):
        return reverse('mcp:machine_detail', kwargs={'pk': self.pk})

class MachineCapability(models.Model):
    """What operations/components a machine can handle"""
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='capabilities')
    component = models.ForeignKey(BOMHeader, on_delete=models.CASCADE)
    setup_time = models.DurationField(help_text="Time required to setup machine for this component")
    processing_time = models.DurationField(help_text="Time required to process one unit")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Machine Capability"
        verbose_name_plural = "Machine Capabilities"
        unique_together = ('machine', 'component')
        ordering = ['machine', 'component']

    def __str__(self):
        return f"{self.machine} can produce {self.component}"

class MachineSchedule(models.Model):
    """Scheduled operations for machines"""
    STATUS_CHOICES = [
        ('PL', 'Planned'),
        ('IP', 'In Progress'),
        ('CO', 'Completed'),
        ('CA', 'Cancelled'),
    ]
    
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='schedules')
    component = models.ForeignKey(BOMHeader, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default='PL')
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Machine Schedule"
        verbose_name_plural = "Machine Schedules"
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['start_time', 'end_time']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.machine} scheduled for {self.component} from {self.start_time} to {self.end_time}"

    def save(self, *args, **kwargs):
        # Calculate end_time based on component's processing time if not set
        if not self.end_time and self.start_time and self.component:
            capability = MachineCapability.objects.filter(
                machine=self.machine,
                component=self.component
            ).first()
            if capability:
                processing_time = capability.processing_time
                total_time = processing_time * self.quantity
                self.end_time = self.start_time + total_time
        super().save(*args, **kwargs)

class MaintenanceSchedule(models.Model):
    """Preventive maintenance schedules for machines"""
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='maintenance_schedules')
    maintenance_type = models.CharField(max_length=100)
    scheduled_date = models.DateField()
    actual_date = models.DateField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    technician = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Maintenance Schedule"
        verbose_name_plural = "Maintenance Schedules"
        ordering = ['scheduled_date']

    def __str__(self):
        return f"{self.maintenance_type} for {self.machine} on {self.scheduled_date}"
    

class Operation(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class WorkCenter(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class Routing(models.Model):
    component = models.ForeignKey(BOMHeader, on_delete=models.CASCADE, verbose_name="BOM Component")
    operation = models.ForeignKey(Operation, on_delete=models.CASCADE)
    sequence = models.PositiveIntegerField()
    work_center = models.ForeignKey(WorkCenter, on_delete=models.CASCADE)
    setup_time = models.PositiveIntegerField(help_text="Setup time in minutes")
    run_time_per_unit = models.PositiveIntegerField(help_text="Run time per unit in minutes")
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('component', 'sequence')
        ordering = ['component', 'sequence']
        verbose_name = "BOM Routing"
    
    def __str__(self):
        return f"{self.component} - Op {self.sequence}: {self.operation}"
    
    def get_absolute_url(self):
        return reverse('routing_list')

class ProductionOrder(models.Model):
    order_number = models.CharField(max_length=50, unique=True)
    component = models.ForeignKey(BOMHeader, on_delete=models.PROTECT, verbose_name="BOM Component" ,related_name="machine_production_orders" )
    quantity = models.PositiveIntegerField()
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('PLANNED', 'Planned'),
        ('RELEASED', 'Released'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ], default='PLANNED')
    
    def __str__(self):
        return f"{self.order_number} - {self.component} ({self.quantity})"

class MachinePlanning(models.Model):
    production_order = models.ForeignKey('MachinePlan.ProductionOrder', on_delete=models.CASCADE)
    component = models.ForeignKey(BOMHeader, on_delete=models.PROTECT, verbose_name="BOM Component")
    operation = models.ForeignKey(Operation, on_delete=models.PROTECT)
    machine = models.ForeignKey('Machine', on_delete=models.PROTECT)
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    status = models.CharField(max_length=20, choices=[
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ], default='SCHEDULED')
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "BOM Machine Planning"
    
    def __str__(self):
        return f"{self.production_order} - {self.operation} on {self.machine}"
    
    def get_absolute_url(self):
        return reverse('machine_planning_list')