# machineplan/admin.py
from django.contrib import admin
from .models import *

class MachineCapabilityInline(admin.TabularInline):
    model = MachineCapability
    extra = 1



class MaintenanceScheduleInline(admin.TabularInline):
    model = MaintenanceSchedule
    extra = 1
    readonly_fields = ['created_by', 'created_at']
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ['machine_id', 'name', 'machine_type', 'status', 'capacity']
    list_filter = ['status', 'machine_type']
    search_fields = ['machine_id', 'name', 'model_number', 'serial_number']
    inlines = [MachineCapabilityInline, MaintenanceScheduleInline]
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(MachineType)
class MachineTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']

@admin.register(MachineCapability)
class MachineCapabilityAdmin(admin.ModelAdmin):
    list_display = ['machine', 'component', 'setup_time', 'processing_time']
    list_filter = ['machine']
    search_fields = ['machine__name', 'component__part_number']



@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = ['machine', 'maintenance_type', 'scheduled_date', 'completed']
    list_filter = ['completed', 'machine']
    search_fields = ['machine__name', 'maintenance_type']
    readonly_fields = ['created_by', 'created_at']
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Routing)
class RoutingAdmin(admin.ModelAdmin):
    list_display = ['component', 'sequence', 'operation', 'work_center', 
                   'setup_time', 'run_time_per_unit']
    list_filter = ['work_center', 'operation']
    search_fields = ['component__part_number', 'operation__name']
    ordering = ['component', 'sequence']


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'description']
    search_fields = ['code', 'name']
    ordering = ['code']

@admin.register(MachinePlanning)
class MachinePlanningAdmin(admin.ModelAdmin):
    list_display = ('production_order', 'component', 'operation', 'machine', 'status', 'scheduled_start', 'scheduled_end')
    list_filter = ('status', 'machine')
    search_fields = ('production_order__order_number', 'component__part_number')
    date_hierarchy = 'scheduled_start'
    ordering = ('-scheduled_start',)