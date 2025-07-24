# machineplan/admin.py
from django.contrib import admin
from .models import Machine, MachineType, MachineCapability, MachineSchedule, MaintenanceSchedule

class MachineCapabilityInline(admin.TabularInline):
    model = MachineCapability
    extra = 1

class MachineScheduleInline(admin.TabularInline):
    model = MachineSchedule
    extra = 1
    readonly_fields = ['created_by', 'created_at']
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

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
    inlines = [MachineCapabilityInline, MachineScheduleInline, MaintenanceScheduleInline]
    
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

@admin.register(MachineSchedule)
class MachineScheduleAdmin(admin.ModelAdmin):
    list_display = ['machine', 'component', 'start_time', 'end_time', 'status']
    list_filter = ['status', 'machine']
    search_fields = ['machine__name', 'component__part_number']
    readonly_fields = ['created_by', 'created_at']
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

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