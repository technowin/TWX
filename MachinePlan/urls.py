# machineplan/urls.py
from django.urls import path
from . import views

app_name = 'mcp'

urlpatterns = [
    # Machine Type URLs
    path('machine-types/', views.MachineTypeListView.as_view(), name='machine_type_list'),
    path('machine-types/add/', views.MachineTypeCreateView.as_view(), name='machine_type_create'),
    path('machine-types/<int:pk>/', views.MachineTypeDetailView.as_view(), name='machine_type_detail'),
    path('machine-types/<int:pk>/edit/', views.MachineTypeUpdateView.as_view(), name='machine_type_update'),
    path('machine-types/<int:pk>/delete/', views.MachineTypeDeleteView.as_view(), name='machine_type_delete'),
    
    # Machine URLs
    path('machines/', views.MachineListView.as_view(), name='machine_list'),
    path('machines/add/', views.MachineCreateView.as_view(), name='machine_create'),
    path('machines/<int:pk>/', views.MachineDetailView.as_view(), name='machine_detail'),
    path('machines/<int:pk>/edit/', views.MachineUpdateView.as_view(), name='machine_update'),
    path('machines/<int:pk>/delete/', views.MachineDeleteView.as_view(), name='machine_delete'),
    
    # Machine Capability URLs
    path('capabilities/', views.MachineCapabilityListView.as_view(), name='machine_capability_list'),
    path('capabilities/add/', views.MachineCapabilityCreateView.as_view(), name='machine_capability_create'),
    path('capabilities/<int:pk>/edit/', views.MachineCapabilityUpdateView.as_view(), name='machine_capability_update'),
    path('capabilities/<int:pk>/delete/', views.MachineCapabilityDeleteView.as_view(), name='machine_capability_delete'),
    
    # Machine Schedule URLs
    path('schedules/', views.MachineScheduleListView.as_view(), name='machine_schedule_list'),
    path('schedules/add/', views.MachineScheduleCreateView.as_view(), name='machine_schedule_create'),
    path('schedules/<int:pk>/edit/', views.MachineScheduleUpdateView.as_view(), name='machine_schedule_update'),
    path('schedules/<int:pk>/delete/', views.MachineScheduleDeleteView.as_view(), name='machine_schedule_delete'),
    path('schedules/calendar/', views.MachineCalendarView.as_view(), name='machine_calendar'),
    
    # Maintenance Schedule URLs
    path('maintenance/', views.MaintenanceScheduleListView.as_view(), name='maintenance_schedule_list'),
    path('maintenance/add/', views.MaintenanceScheduleCreateView.as_view(), name='maintenance_schedule_create'),
    path('maintenance/<int:pk>/edit/', views.MaintenanceScheduleUpdateView.as_view(), name='maintenance_schedule_update'),
    path('maintenance/<int:pk>/delete/', views.MaintenanceScheduleDeleteView.as_view(), name='maintenance_schedule_delete'),

    path('routings/', views.RoutingListView.as_view(), name='routing_list'),
    path('routings/add/', views.RoutingCreateView.as_view(), name='routing_create'),
    path('routings/<int:pk>/edit/', views.RoutingUpdateView.as_view(), name='routing_edit'),
    path('routings/<int:pk>/delete/', views.RoutingDeleteView.as_view(), name='routing_delete'),
    
    # Machine Planning URLs
    path('machine-plans/', views.machine_planning_list, name='machine_planning_list'),
    path('machine-plans/create/', views.machine_planning_create, name='machine_planning_create'),
    path('machine-plans/edit/<int:pk>/', views.machine_planning_edit, name='machine_planning_edit'),
    path('machine-plans/delete/<int:pk>/', views.machine_planning_delete, name='machine_planning_delete'),
]