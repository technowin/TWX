# machineplan/urls.py
from django.urls import path

from MachinePlanning.views import MachineTypeDetailView

# import MachinePlan
# from . import vfrom MaterialPlan.views import *iews 

app_name = 'mcp'


from Account import views
from MachinePlanning.views import *

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
    # path('capabilities/<int:pk>/detail/', machine_capability_detail, name='machine_capability_detail'),
    
    
    # Maintenance Schedule URLs
    path('maintenance/', MaintenanceScheduleListView.as_view(), name='maintenance_schedule_list'),
    path('maintenance/add/', MaintenanceScheduleCreateView.as_view(), name='maintenance_schedule_create'),
    path('maintenance/<int:pk>/edit/', MaintenanceScheduleUpdateView.as_view(), name='maintenance_schedule_update'),
    path('maintenance/<int:pk>/delete/', MaintenanceScheduleDeleteView.as_view(), name='maintenance_schedule_delete'),

    path('routings/', RoutingListView.as_view(), name='routing_list'),
    path('routings/add/', routing_create, name='routing_create'),
    path('routings<int:pk>/edit/', routing_create, name='routing_edit'),
    path('routings/<int:pk>/edit/', RoutingUpdateView.as_view(), name='routing_update'),
    path('routings/<int:pk>/delete/', RoutingDeleteView.as_view(), name='routing_delete'),
    
    # Machine Planning URLs
    path('machine-plans/', MachinePlanningListView.as_view(), name='machine_planning_list'),
    path('machine-plans/create/', MachinePlanningCreateView.as_view(), name='machine_planning_create'),
    path('machine-plans/<int:pk>/edit/', MachinePlanningUpdateView.as_view(), name='machine_planning_edit'),
    path('machine-plans/<int:pk>/delete/', MachinePlanningDeleteView.as_view(), name='machine_planning_delete'),

    path('operations/', OperationListView.as_view(), name='operation_list'),
    path('operations/add/', OperationCreateView.as_view(), name='operation_create'),
    path('operations/<int:pk>/edit/', OperationUpdateView.as_view(), name='operation_edit'),
    path('operations/<int:pk>/delete/', OperationDeleteView.as_view(), name='operation_delete'),

    path('workcenters/', WorkCenterListView.as_view(), name='workcenter_list'),
    path('workcenters/create/', WorkCenterCreateView.as_view(), name='workcenter_create'),
    path('workcenters/<int:pk>/edit/', WorkCenterUpdateView.as_view(), name='workcenter_edit'),
    path('workcenters/<int:pk>/delete/', WorkCenterDeleteView.as_view(), name='workcenter_delete'),

    path('machine_scheduling/', MachineScheduleListView.as_view(), name='machine_scheduling_list'),
    path('machine_scheduling/create/', MachineScheduleCreateView.as_view(), name='machine_scheduling_create'),
    path('machine_scheduling/<int:pk>/update/', MachineScheduleUpdateView.as_view(), name='machine_scheduling_update'),
    path('machine_scheduling/<int:pk>/delete/', MachineSchedulingDeleteView.as_view(), name='machine_scheduling_delete'),
    path('machine_scheduling/ajax/load-routings/', load_routings, name='ajax_load_routings'),
    path('machine_scheduling/ajax/load-machines/', load_machines, name='ajax_load_machines'),

    path("get_routings/<int:component_id>/",get_routings, name="get_routings"),
    path("get_assignment_data/<int:routing_id>/",get_assignment_data, name="get_assignment_data"),

    path('workstations/', WorkStationListView.as_view(), name='workstation_list'),
    path('workstations/create/', WorkStationCreateView.as_view(), name='workstation_create'),
    path('workstations/<int:pk>/update/', WorkStationUpdateView.as_view(), name='workstation_update'),
    path('workstations/<int:pk>/delete/', WorkStationDeleteView.as_view(), name='workstation_delete'),
    path('get-component-by-production/', get_component_by_production_order, name='get_component_by_production'),
    path("get-routing-details/", get_routing_details, name="get_routing_details"),
    path("get_workstation_details/", get_workstation_details, name="get_workstation_details"),
    path("calculate_end_date/", calculate_end_date, name="calculate_end_date"),
    path("relocate_shift/", relocate_shift, name="relocate_shift"),

    path('production-planning/', production_planning_with_batch, name='production_planning_with_batch'),
    path('production-order/<int:batch_id>/<int:production_order_id>/component/<int:component_id>/confirm-plan/',confirm_production_plan,  name='confirm_production_plan'),

    path('production-order/', create_batch_routing_log, name='create_batch_routing_log'),
    path('batch/<int:batch_id>/complete-process/',complete_batch_process, name='complete_batch_process'),
    path('update-batch-routing-log/', update_batch_routing_log, name='update_batch_routing_log'),
    path('mps-complete/<int:production_order_id>/<int:component_id>/', mps_complete_redirect, name='mps_complete_redirect'),
    path('mrp_complete/<int:production_order_id>/<int:component_id>/', mps_complete_redirect, name='mrp_complete_redirect'),
    path('production_plan_complete/<int:production_order_id>/<int:component_id>/', production_plan_complete_redirect, name='production_plan_complete_redirect'),






    path('dashboard/',dashboard, name='dashboard'),

    path('get-routing-data/', get_routing_data, name='get_routing_data'),
]