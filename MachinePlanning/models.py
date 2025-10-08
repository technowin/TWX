from datetime import timezone
from django.db import models

# Create your models here.
# machineplan/models.py
from django.db import models
from django.shortcuts import get_object_or_404
from django.urls import reverse
from BOM.models import BOMHeader
from django.contrib.auth import get_user_model

from MachinePlanning.services import update_production_order_status
from ManpowerPlan.models import Employee, Shift
from PLM.models import StatusAction
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.timezone import now

CustomUser = get_user_model()

class MachineType(models.Model):
    """Different types of machines available"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True,null=True, blank=True)
    created_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='machine_type_created_by',verbose_name="Created By")
    updated_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='machine_type_updated_by',verbose_name="Updated By")

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
    machine_type = models.ForeignKey(MachineType, on_delete=models.CASCADE)
    work_center = models.ForeignKey('MachinePlanning.WorkCenters', on_delete=models.CASCADE,null=True,blank=True)
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
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True,null=True, blank=True)
    updated_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='machine_updated_by',verbose_name="Updated By")

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
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True,null=True, blank=True)
    created_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='machiencap_created_by',verbose_name="Created By")
    updated_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='machiencap_updated_by',verbose_name="Updated By")

    class Meta:
        verbose_name = "Machine Capability"
        verbose_name_plural = "Machine Capabilities"
        unique_together = ('machine', 'component')
        ordering = ['machine', 'component']

    def __str__(self):
        return f"{self.machine} can produce {self.component}"



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
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True,null=True, blank=True)
    updated_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='maintenance_updated_by',verbose_name="Updated By")

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
    created_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='operation_created_by',verbose_name="Created By")
    updated_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='operation_updated_by',verbose_name="Updated By")
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True,null=True, blank=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class WorkCenters(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    workstation = models.ForeignKey('MachinePlanning.WorkStations',on_delete=models.SET_NULL,null=True,blank=True,related_name='workstation_id',verbose_name="Work Station")
    created_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='workcenter_created_by',verbose_name="Created By")
    updated_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='workcenter_updated_by',verbose_name="Updated By")
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True,null=True, blank=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    


class RoutingMaster(models.Model):
    name = models.TextField(null=True, blank=True)
    component = models.ForeignKey('BOM.BOMHeader',on_delete=models.CASCADE,verbose_name="BOM Component")
    notes = models.TextField(blank=True, verbose_name="Additional Notes")
    created_at = models.DateTimeField(null=True,blank=True, auto_now_add=True)
    created_by = models.ForeignKey('Account.CustomUser',on_delete=models.CASCADE,null=True, blank=True)
    created_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='routingmaster_created_by',verbose_name="Created By")
    updated_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='routingmaster_updated_by',verbose_name="Updated By")
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True,null=True, blank=True)
    class Meta:
        verbose_name = "BOM Routing"
        verbose_name_plural = "BOM Routings"

    def __str__(self):
        return f"{self.name} - {self.component}"

    def get_absolute_url(self):
        return reverse('routing_list')


class RoutingDetail(models.Model):
    routing = models.ForeignKey( RoutingMaster,on_delete=models.CASCADE,related_name="details")
    operation = models.ForeignKey(Operation, on_delete=models.CASCADE,null=True,blank=True)
    production_order = models.ForeignKey('MaterialPlan.ProductionOrder',on_delete=models.CASCADE,null=True,blank=True)
    sequence = models.PositiveIntegerField()
    work_center = models.ForeignKey(WorkCenters, on_delete=models.CASCADE)
    setup_time = models.PositiveIntegerField(help_text="Setup time in minutes" ,null=True,blank=True)
    run_time_per_unit = models.PositiveIntegerField(help_text="Run time per unit in minutes",null=True,blank=True)
    skill = models.ForeignKey('ManpowerPlan.Skill',on_delete=models.CASCADE,verbose_name="Required Skill",null=True,blank=True)
    employees_needed = models.PositiveSmallIntegerField(verbose_name="Employees Needed",null=True,blank=True)
    min_proficiency = models.ForeignKey('ManpowerPlan.Proficeincy',on_delete=models.CASCADE,related_name='rout_require_proficiency',null=True,blank=True)
    created_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='routingdetail_created_by',verbose_name="Created By")
    updated_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='routingdetail_updated_by',verbose_name="Updated By")
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True,null=True, blank=True)

    class Meta:
        unique_together = ('routing', 'sequence')
        ordering = ['routing', 'sequence']
        verbose_name = "Routing Detail"
        verbose_name_plural = "Routing Details"

    def __str__(self):
        return f"{self.routing.name} - Seq {self.sequence}"


class MachinePlanning(models.Model):
    production_order = models.ForeignKey('MaterialPlan.ProductionOrder', on_delete=models.CASCADE,null=True,blank=True)
    component = models.ForeignKey(BOMHeader, on_delete=models.CASCADE, verbose_name="BOM Component")
    operation = models.ForeignKey(Operation, on_delete=models.CASCADE,null=True,blank=True)
    routing = models.ForeignKey(RoutingMaster, on_delete=models.CASCADE,null=True,blank=True)
    machine = models.ForeignKey('Machine', on_delete=models.CASCADE,null=True,blank=True)
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    status = models.CharField(max_length=20, choices=[
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('PLANNED', 'Planned'),
    ], default='SCHEDULED')
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='machineplan_created_by',verbose_name="Created By")
    updated_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='machineplan_updated_by',verbose_name="Updated By")
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True,null=True, blank=True)
    
    class Meta:
        verbose_name = "BOM Machine Planning"
    
    def __str__(self):
        return f"{self.production_order} - {self.operation} on {self.machine}"
    
    def get_absolute_url(self):
        return reverse('machine_planning_list')
    
    
class MachineScheduling(models.Model):
    production_order = models.ForeignKey('MaterialPlan.ProductionOrder', on_delete=models.CASCADE, null=True, blank=True)
    component = models.ForeignKey(BOMHeader, on_delete=models.CASCADE, verbose_name="BOM Component")
    routing = models.ForeignKey(RoutingMaster, on_delete=models.CASCADE)
    seq = models.TextField(null= True, blank=True)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    work_center = models.ForeignKey(WorkCenters, on_delete=models.CASCADE)  
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='machienschduling_created_by',verbose_name="Created By")
    updated_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='machienschduling_updated_by',verbose_name="Updated By")
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True,null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ], default='SCHEDULED')
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Machine Scheduling"
        ordering = ['scheduled_start']
    
    def __str__(self):
        return f"{self.production_order} - {self.routing.operation} on {self.machine} - {self.seq}"
    
    def get_absolute_url(self):
        return reverse('machine_scheduling_list')
    
    def save(self, *args, **kwargs):
    # Automatically set work_center from routing
        if self.routing and not self.work_center:
            self.work_center = self.routing.work_center
        super().save(*args, **kwargs)

        # Call your existing logic
        update_production_order_status(self.production_order)

        # --- NEW LOGIC ---
        if self.production_order and self.component:
            # Get the last (highest seq) schedule for this order+component
            last_schedule = (
                MachineScheduling.objects.filter(
                    production_order=self.production_order,
                    component=self.component
                )
                .order_by("-seq")  # highest seq
                .first()
            )

            if last_schedule and last_schedule.actual_end:
                # Check if last row's actual_end < now
                if last_schedule.actual_end < now():
                    self.production_order.order_status = get_object_or_404(StatusAction, id = 7)
                    self.production_order.save(update_fields=["order_status"])


class MachineSchedule(models.Model):
    name = models.CharField(max_length=255, verbose_name="Schedule Name", null=True, blank=True)
    production_order = models.ForeignKey('MaterialPlan.ProductionOrder', on_delete=models.CASCADE, null=True, blank=True)
    routing = models.ForeignKey('MachinePlanning.RoutingMaster', on_delete=models.CASCADE, null=True, blank=True)
    component = models.ForeignKey('BOM.BOMHeader', on_delete=models.CASCADE, verbose_name="BOM Component")
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
    created_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='machienschedule_created_by',verbose_name="Created By")
    updated_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='machienschedule_updated_by',verbose_name="Updated By")
    ccreated_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True,null=True, blank=True)
    
    class Meta:
        verbose_name = "Machine Schedule"
        ordering = ['scheduled_start']
    
    def __str__(self):
        return f"{self.name} - {self.production_order} - {self.component}"
    
    def get_absolute_url(self):
        return reverse('machine_schedule_list')


# --- Detail table ---
class MachineScheduleDetail(models.Model):
    schedule = models.ForeignKey(MachineSchedule, on_delete=models.CASCADE, related_name='details')
    seq = models.TextField(null=True, blank=True)
    routing = models.ForeignKey(RoutingMaster, on_delete=models.CASCADE)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    workstation = models.ForeignKey('MachinePlanning.WorkStations',on_delete=models.CASCADE, null=True, blank=True)
    work_center = models.ForeignKey(WorkCenters, on_delete=models.CASCADE, null=True, blank=True)  
    employee = models.TextField(verbose_name="Assigned Employee", null=True, blank=True)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, null=True, blank=True)
    hours_allocated = models.DecimalField(max_digits=4,decimal_places=2,validators=[MinValueValidator(0.25), MaxValueValidator(24)], verbose_name="Hours Allocated",null=True,blank=True )
    created_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='machienscheduledetail_created_by',verbose_name="Created By")
    updated_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='machienscheduledetail_updated_by',verbose_name="Updated By")
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True,null=True, blank=True)
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('SCHEDULED', 'Scheduled'),
            ('IN_PROGRESS', 'In Progress'),
            ('COMPLETED', 'Completed'),
            ('CANCELLED', 'Cancelled'),
            ('ABSENT', 'Absent'),
            ('REASSIGNED', 'Reassigned'),
        ],
        default='SCHEDULED'
    )
    
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Machine Schedule Detail"
        ordering = ['seq']
    
    def __str__(self):
        return f"{self.schedule.name} - {self.routing.operation} on {self.machine}"

    def save(self, *args, **kwargs):
        # --- AUTO SET WORK_CENTER FROM ROUTING ---
        if self.routing and not self.work_center:
            self.work_center = self.routing.work_center
        
        super().save(*args, **kwargs)

        # --- UPDATE PRODUCTION ORDER STATUS ---
        production_order = self.schedule.production_order
        component = self.schedule.component

        if production_order:
            from .services import update_production_order_status  # adjust to your path
            update_production_order_status(production_order)

        # --- NEW LOGIC: Check last schedule for this production order & component ---
        if production_order and component:
            last_schedule = (
                MachineScheduleDetail.objects.filter(
                    schedule__production_order=production_order,
                    schedule__component=component
                )
                .order_by("-seq")
                .first()
            )
            if last_schedule and last_schedule.actual_end:
                if last_schedule.actual_end < now():
                    production_order.order_status = get_object_or_404(StatusAction, id=7)
                    production_order.save(update_fields=["order_status"])


class WorkStations(models.Model):
    """Workstation linking machines and employees"""

    name = models.TextField(null=True,blank=True)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE,related_name='workstation',verbose_name="Machine")
    work_center = models.ForeignKey(WorkCenters, on_delete=models.CASCADE, related_name="work_center_station",null=True,blank=True)
    employee = models.TextField(null=True, blank=True, verbose_name='Assigned Employees')
    created_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True, blank=True,related_name='workstations_created_by',verbose_name="Created By")
    updated_by = models.ForeignKey( CustomUser,on_delete=models.SET_NULL, null=True,blank=True,related_name='workstations_updated_by',verbose_name="Updated By")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Work Station"
        verbose_name_plural = "Work Stations"
        ordering = ['machine__machine_id']

    def __str__(self):
        return f"WorkStation: {self.name} - {self.machine.name}"

    def get_employee_names(self):
        """Return a readable string of employee names."""
        from .models import Employee  # local import to avoid circular import
        if not self.employee:
            return ""
        ids = [int(e) for e in self.employee.split(',') if e.strip().isdigit()]
        employees = Employee.objects.filter(id__in=ids)
        return ", ".join(emp.employee_name for emp in employees)






