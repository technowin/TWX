# machineplan/urls.py
from django.urls import path
# from . import vfrom MaterialPlan.views import *iews 

app_name = 'mcp'


from MachinePlan.views import *

urlpatterns = [
    # Machine Type URLs
    path('machine-types/', MachineTypeListView.as_view(), name='machine_type_list'),
    path('machine-types/add/', MachineTypeCreateView.as_view(), name='machine_type_create'),
    path('machine-types/<int:pk>/', MachineTypeDetailView.as_view(), name='machine_type_detail'),
    path('machine-types/<int:pk>/edit/', MachineTypeUpdateView.as_view(), name='machine_type_update'),
    path('machine-types/<int:pk>/delete/', MachineTypeDeleteView.as_view(), name='machine_type_delete'),
    
    # Machine URLs
    path('machines/', MachineListView.as_view(), name='machine_list'),
    path('machines/add/', MachineCreateView.as_view(), name='machine_create'),
    path('machines/<int:pk>/', MachineDetailView.as_view(), name='machine_detail'),
    path('machines/<int:pk>/edit/', MachineUpdateView.as_view(), name='machine_update'),
    path('machines/<int:pk>/delete/', MachineDeleteView.as_view(), name='machine_delete'),
    
    # Machine Capability URLs
    path('capabilities/', MachineCapabilityListView.as_view(), name='machine_capability_list'),
    path('capabilities/add/', MachineCapabilityCreateView.as_view(), name='machine_capability_create'),
    path('capabilities/<int:pk>/edit/', MachineCapabilityUpdateView.as_view(), name='machine_capability_update'),
    path('capabilities/<int:pk>/delete/', MachineCapabilityDeleteView.as_view(), name='machine_capability_delete'),
    
    # Machine Schedule URLs
    path('schedules/', MachineScheduleListView.as_view(), name='machine_schedule_list'),
    path('schedules/add/', MachineScheduleCreateView.as_view(), name='machine_schedule_create'),
    path('schedules/<int:pk>/edit/', MachineScheduleUpdateView.as_view(), name='machine_schedule_update'),
    path('schedules/<int:pk>/delete/', MachineScheduleDeleteView.as_view(), name='machine_schedule_delete'),
    path('schedules/calendar/', MachineCalendarView.as_view(), name='machine_calendar'),
    
    # Maintenance Schedule URLs
    path('maintenance/', MaintenanceScheduleListView.as_view(), name='maintenance_schedule_list'),
    path('maintenance/add/', MaintenanceScheduleCreateView.as_view(), name='maintenance_schedule_create'),
    path('maintenance/<int:pk>/edit/', MaintenanceScheduleUpdateView.as_view(), name='maintenance_schedule_update'),
    path('maintenance/<int:pk>/delete/', MaintenanceScheduleDeleteView.as_view(), name='maintenance_schedule_delete'),

    path('routings/', RoutingListView.as_view(), name='routing_list'),
    path('routings/add/', RoutingCreateView.as_view(), name='routing_create'),
    path('routings/<int:pk>/edit/', RoutingUpdateView.as_view(), name='routing_edit'),
    path('routings/<int:pk>/delete/', RoutingDeleteView.as_view(), name='routing_delete'),
    
    # Machine Planning URLs
    path('machine-plans/', machine_planning_list, name='machine_planning_list'),
    path('machine-plans/create/', machine_planning_create, name='machine_planning_create'),
    path('machine-plans/edit/<int:pk>/', machine_planning_edit, name='machine_planning_edit'),
    path('machine-plans/delete/<int:pk>/', machine_planning_delete, name='machine_planning_delete'),

    path('operations/', OperationListView.as_view(), name='operation_list'),
    path('operations/add/', OperationCreateView.as_view(), name='operation_create'),
    path('operations/<int:pk>/edit/', OperationUpdateView.as_view(), name='operation_edit'),
    path('operations/<int:pk>/delete/', OperationDeleteView.as_view(), name='operation_delete'),

    path('workcenters/', WorkCenterListView.as_view(), name='workcenter_list'),
    path('workcenters/add/', WorkCenterCreateView.as_view(), name='workcenter_create'),
    path('workcenters/<int:pk>/edit/', WorkCenterUpdateView.as_view(), name='workcenter_edit'),
    path('workcenters/<int:pk>/delete/', WorkCenterDeleteView.as_view(), name='workcenter_delete'),
]