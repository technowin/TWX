# MachinePlan/views.py
from datetime import datetime, timedelta
from itertools import count
import json
import re
import traceback
from django.contrib import messages
from django.forms import inlineformset_factory
from django.http import JsonResponse
from django.db.models import Count, Q
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin

from Account.db_utils import callproc
from BOM.models import Component
from ManpowerPlan.models import EmployeeSkill, Proficeincy,Skill
from MaterialPlan.models import ProductionOrder
from .models import *
from .forms import *
from .forms import *
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q
from django.utils import timezone
from django.template.loader import render_to_string

from django.utils.dateparse import parse_datetime

class MachineTypeListView(ListView):
    model = MachineType
    template_name = 'MachinePlan/machine_type_list.html'
    context_object_name = 'machine_types'
    paginate_by = 20

class MachineTypeCreateView(CreateView):
    model = MachineType
    form_class = MachineTypeForm
    template_name = 'MachinePlan/machine_type_form.html'
    success_url = reverse_lazy('mcp:machine_type_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

class MachineTypeUpdateView( UpdateView):
    model = MachineType
    form_class = MachineTypeForm
    template_name = 'MachinePlan/machine_type_form.html'
    success_url = reverse_lazy('mcp:machine_type_list')

class MachineTypeDetailView( DetailView):
    model = MachineType
    template_name = 'MachinePlan/machine_type_detail.html'
    context_object_name = 'machine_type'


class MachineTypeDeleteView(LoginRequiredMixin, DeleteView):
    model = MachineType
    success_url = reverse_lazy('mcp:machine_type_list')
    
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        return messages.success(request, 'Machine type deleted successfully.')
        
        # if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        #     return JsonResponse({'success': True, 'redirect_url': success_url})
        # return redirect(success_url)

class MachineListView( ListView):
    model = Machine
    template_name = 'MachinePlan/machine_list.html'
    context_object_name = 'machines'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.GET.get('status')
        machine_type = self.request.GET.get('machine_type')
        
        if status:
            queryset = queryset.filter(status=status)
        if machine_type:
            queryset = queryset.filter(machine_type_id=machine_type)
            
        return queryset.order_by('machine_id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['machine_types'] = MachineType.objects.all()
        context['status_choices'] = Machine.STATUS_CHOICES
        return context

class MachineCreateView( CreateView):
    model = Machine
    form_class = MachineForm
    template_name = 'MachinePlan/machine_form.html'
    success_url = reverse_lazy('mcp:machine_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

class MachineUpdateView( UpdateView):
    model = Machine
    form_class = MachineForm
    template_name = 'MachinePlan/machine_form.html'
    success_url = reverse_lazy('mcp:machine_list')

class MachineDetailView( DetailView):
    model = Machine
    template_name = 'MachinePlan/machine_detail.html'
    context_object_name = 'machine'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['capabilities'] = self.object.capabilities.all()
        # context['schedules'] = self.object.schedules.filter(
        #     start_time__gte=timezone.now()
        # ).order_by('start_time')[:10]
        context['maintenance_schedules'] = self.object.maintenance_schedules.filter(
            scheduled_date__gte=timezone.now().date(),
            completed=False
        ).order_by('scheduled_date')[:5]
        return context

class MachineDeleteView(DeleteView):
    model = Machine
    # template_name = 'MachinePlan/machine_confirm_delete.html'
    success_url = reverse_lazy('mcp:machine_list')
    
    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            self.object.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            raise Exception(f"Error in retrieving module tables: {str(e)}")


class MachineCapabilityListView( ListView):
    model = MachineCapability
    template_name = 'MachinePlan/machine_capability_list.html'
    context_object_name = 'capabilities'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        machine_id = self.request.GET.get('machine')
        component_id = self.request.GET.get('component')
        
        if machine_id:
            queryset = queryset.filter(machine_id=machine_id)
        if component_id:
            queryset = queryset.filter(component_id=component_id)
            
        return queryset.select_related('machine', 'component')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['machines'] = Machine.objects.filter(status='OP')
        context['components'] = BOMHeader.objects.all()
        return context

class MachineCapabilityCreateView(CreateView):
    model = MachineCapability
    form_class = MachineCapabilityForm
    template_name = 'MachinePlan/machine_capability_form.html'
    success_url = reverse_lazy('mcp:machine_capability_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['machines'] = Machine.objects.all()  # Or add any filtering you need
        context['components'] = BOMHeader.objects.all()  # Or add any filtering you need
        return context

class MachineCapabilityUpdateView( UpdateView):
    model = MachineCapability
    form_class = MachineCapabilityForm
    template_name = 'MachinePlan/machine_capability_form.html'
    success_url = reverse_lazy('mcp:machine_capability_list')

class MachineCapabilityDeleteView(DeleteView):
    model = MachineCapability
    template_name = 'MachinePlan/machine_capability_confirm_delete.html'
    success_url = reverse_lazy('mcp:machine_capability_list')




class MaintenanceScheduleListView( ListView):
    model = MaintenanceSchedule
    template_name = 'MachinePlan/maintenance_schedule_list.html'
    context_object_name = 'maintenance_schedules'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        completed = self.request.GET.get('completed')
        machine_id = self.request.GET.get('machine')
        
        if date_from:
            queryset = queryset.filter(scheduled_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(scheduled_date__lte=date_to)
        if completed:
            queryset = queryset.filter(completed=(completed == 'true'))
        if machine_id:
            queryset = queryset.filter(machine_id=machine_id)
            
        return queryset.select_related('machine').order_by('scheduled_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['machines'] = Machine.objects.all()
        return context

class MaintenanceScheduleCreateView( CreateView):
    model = MaintenanceSchedule
    form_class = MaintenanceScheduleForm
    template_name = 'MachinePlan/maintenance_schedule_form.html'
    success_url = reverse_lazy('mcp:maintenance_schedule_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

class MaintenanceScheduleUpdateView( UpdateView):
    model = MaintenanceSchedule
    form_class = MaintenanceScheduleForm
    template_name = 'MachinePlan/maintenance_schedule_form.html'
    success_url = reverse_lazy('mcp:maintenance_schedule_list')


class MaintenanceScheduleDeleteView( DeleteView):
    model = MaintenanceSchedule
    template_name = 'MachinePlan/maintenance_schedule_confirm_delete.html'
    success_url = reverse_lazy('mcp:maintenance_schedule_list')


class RoutingListView(ListView):
    model = RoutingMaster
    template_name = 'MachinePlan/routing_list.html'
    context_object_name = 'routings'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related('component')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['components'] = BOMHeader.objects.all()
        return context

class RoutingCreateView(View):
    template_name = 'MachinePlan/routing_form.html'
    success_url = reverse_lazy('mcp:routing_list')

    def get(self, request, *args, **kwargs):
        context = {
            # 'form': RoutingForm(),
            'components': BOMHeader.objects.all(),
            'operations': Operation.objects.all(),
            'work_centers': WorkCenters.objects.all(),
            'proficiencies': Proficeincy.objects.all(),
            'skills': Skill.objects.all(),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        try:
            # Common fields
            name = request.POST.get("name")
            component_id = request.POST.get("component")
            notes = request.POST.get("notes")

            # Step fields (lists)
            operations = request.POST.getlist("operation[]")
            work_centers = request.POST.getlist("work_center[]")
            sequences = request.POST.getlist("sequence[]")
            setup_times = request.POST.getlist("setup_time[]")
            run_times = request.POST.getlist("run_time_per_unit[]")
            skills = request.POST.getlist("skill[]")
            employees_needed = request.POST.getlist("employees_needed[]")
            proficiencies = request.POST.getlist("min_proficiency[]")

            # Ensure at least one step row exists
            if not operations:
                messages.error(request, "Please add at least one routing step.")
                return redirect(request.path)

            for i in range(len(operations)):
                routing = RoutingMaster.objects.create(
                    name=name,
                    component_id=component_id if component_id else None,
                    notes=notes,
                    operation_id=operations[i] if operations[i] else None,
                    work_center_id=work_centers[i] if work_centers[i] else None,
                    sequence=sequences[i] if sequences[i] else i + 1,
                    setup_time=setup_times[i] if setup_times[i] else 0,
                    run_time_per_unit=run_times[i] if run_times[i] else 0,
                    skill_id=skills[i] if skills[i] else None,
                    employees_needed=employees_needed[i] if employees_needed[i] else 1,
                    min_proficiency_id=proficiencies[i] if proficiencies[i] else None,
                )

                # Update work center flag
                if routing.work_center:
                    routing.work_center.is_routing = True
                    routing.work_center.save()

            messages.success(request, "Routing created successfully!")
            return redirect(self.success_url)

        except Exception as e:
            # Log or print for debugging
            print("❌ Error in RoutingCreateView.post:", str(e))
            messages.error(request, f"Error: {str(e)}")
            return redirect(request.path)



class RoutingUpdateView(UpdateView):
    model = RoutingMaster
    # form_class = RoutingForm
    template_name = 'MachinePlan/routing_edit_form.html'
    success_url = reverse_lazy('mcp:routing_list')


class RoutingDeleteView(DeleteView):
    model = RoutingMaster
    template_name = 'MachinePlan/routing_confirm_delete.html'
    success_url = reverse_lazy('mcp:routing_list')


class MachinePlanningListView(ListView):
    model = MachineScheduling
    template_name = 'MachinePlan/machine_planning_list.html'
    context_object_name = 'schedules'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        # Filter by machine if provided
        machine_id = self.request.GET.get('machine')
        if machine_id:
            queryset = queryset.filter(machine_id=machine_id)
            
        # Filter by date range if provided
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(
                scheduled_start__date__gte=start_date,
                scheduled_end__date__lte=end_date
            )

        po_number = self.request.GET.get('po_order')
        if po_number:
            queryset = queryset.filter(production_order__order_number=po_number)

        bom_header = self.request.GET.get('bom_header')
        if bom_header:
            queryset = queryset.filter(production_order__bom__name=bom_header)
            
            
        return queryset.select_related('component', 'routing', 'machine', 'work_center')

class MachinePlanningCreateView(CreateView):
    model = MachineScheduling
    form_class = MachineTrackingForm
    template_name = 'MachinePlan/machine_plainning_form.html'
    success_url = reverse_lazy('mcp:machine_planning_list')
    
    def form_valid(self, form):
        # Set work_center from routing before saving
        if form.cleaned_data['routing']:
            form.instance.work_center = form.cleaned_data['routing'].work_center
        return super().form_valid(form)

class MachinePlanningUpdateView(UpdateView):
    model = MachineScheduling
    form_class = MachineTrackingForm
    template_name = 'MachinePlan/machine_planning_form.html'
    success_url = reverse_lazy('mcp:machine_scheduling_list')
    
    def form_valid(self, form):
        # Set work_center from routing before saving
        if form.cleaned_data['routing']:
            form.instance.work_center = form.cleaned_data['routing'].work_center
        return super().form_valid(form)

class MachinePlanningDeleteView(DeleteView):
    model = MachinePlanning
    success_url = reverse_lazy('mcp:machine_planning_list')
    
    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        messages.success(request, "Schedule deleted successfully!")
        return response


class OperationListView(ListView):
    model = Operation
    template_name = 'MachinePlan/operation_list.html'
    context_object_name = 'operations'
    paginate_by = 20

class OperationCreateView(CreateView):
    model = Operation
    form_class = OperationForm
    template_name = 'MachinePlan/operation_form.html'
    success_url = reverse_lazy('mcp:operation_list')

class OperationUpdateView(UpdateView):
    model = Operation
    form_class = OperationForm
    template_name = 'MachinePlan/operation_form.html'
    success_url = reverse_lazy('mcp:operation_list')


class OperationDeleteView(DeleteView):
    model = Operation
    success_url = reverse_lazy('mcp:operation_list')
    
    def form_valid(self, form):
        success_message = "Operation deleted successfully!"
        self.object = self.get_object()
        self.object.delete()
        
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': success_message
            })
        else:
            # For regular requests, add message and redirect
            messages.success(self.request, success_message)
            return super().form_valid(form)
    
    def delete(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


class WorkCenterListView(ListView):
    model = WorkCenters
    template_name = 'MachinePlan/workcenter_list.html'
    context_object_name = 'workcenters'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()

        # Add a dynamic attribute 'workstation_count' to each object
        for workcenter in queryset:
            workcenter.workstation_count = len(workcenter.get_workstation_ids_list())
        return queryset



class WorkCenterCreateView(CreateView):
    model = WorkCenters
    form_class = WorkCenterForm
    template_name = 'MachinePlan/workcenter_form.html'
    success_url = reverse_lazy('mcp:workcenter_list')
    
    def form_valid(self, form):
        workcenter = form.save(commit=False)
        workcenter.created_by = self.request.user
        workcenter.save()
        
        messages.success(self.request, "Work Center created successfully!")
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['workstations'] = WorkStations.objects.all().order_by('name')
        context['workcenter'] = None
        # Get initial selected workstation IDs for create view
        context['selected_workstation_ids'] = []
        return context

class WorkCenterUpdateView(UpdateView):
    model = WorkCenters
    form_class = WorkCenterForm
    template_name = 'MachinePlan/workcenter_form.html'
    success_url = reverse_lazy('mcp:workcenter_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Work Center updated successfully!")
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['workstations'] = WorkStations.objects.all().order_by('name')
        workcenter = self.get_object()
        context['workcenter'] = workcenter
        
        # Get selected workstation IDs as list
        if workcenter.workstation_ids:
            context['selected_workstation_ids'] = [int(id.strip()) for id in workcenter.workstation_ids.split(',') if id.strip()]
        else:
            context['selected_workstation_ids'] = []
        
        return context


class WorkCenterDeleteView(DeleteView):
    model = WorkCenters
    success_url = reverse_lazy('mcp:workcenter_list')
    
    def form_valid(self, form):
        """Handle successful form submission (DELETE request)"""
        success_message = "Work Center deleted successfully!"
        self.object = self.get_object()
        self.object.delete()
        
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # For AJAX requests, return JSON with message
            return JsonResponse({
                'status': 'success',
                'message': success_message
            })
        else:
            # For regular requests, add message and redirect
            messages.success(self.request, success_message)
            return super().form_valid(form)
    
    def delete(self, request, *args, **kwargs):
        """Override delete to ensure compatibility"""
        return self.post(request, *args, **kwargs)
    
def dashboard(request):
    # Machine status counts
    machine_status_counts = Machine.objects.values('status').annotate(count=Count('status'))
    status_map = {'OP': 'Operational', 'MN': 'Maintenance', 'OO': 'Out of Order', 'RT': 'Retired'}
    components= BOMHeader.objects.all()
    boms = BOMHeader.objects.all()
    
    operational_machines_count = Machine.objects.filter(status='OP').count()
    maintenance_machines_count = Machine.objects.filter(status='MN').count()
    ooo_machines_count = Machine.objects.filter(status='OO').count()
    retired_machines_count = Machine.objects.filter(status='RT').count()
    
    # Production orders
    active_orders_count = ProductionOrder.objects.exclude(
        Q(status='COMPLETED') | Q(status='CANCELLED')
    ).count()
    
    # Upcoming maintenance (next 7 days)
    upcoming_maintenance = MaintenanceSchedule.objects.filter(
        scheduled_date__gte=timezone.now().date(),
        scheduled_date__lte=timezone.now().date() + timedelta(days=7)
        # completed=False
    ).order_by('scheduled_date')[:5]
    
    # Production schedules for today and tomorrow
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    production_schedules = MachinePlanning.objects.filter(
        scheduled_start__gte=today_start,
        scheduled_end__lte=today_end
    ).order_by('scheduled_start')
    
    # Machine utilization data (simplified)
    machine_types = MachineType.objects.annotate(
        operational_machines=Count('machine', filter=Q(machine__status='OP')),
        total_machines=Count('machine')
    )
    
    # Calculate utilization for each machine type
    machine_type_data = []
    for mt in machine_types:
        if mt.total_machines > 0:
            # Calculate utilization percentage (example logic - adjust as needed)
            utilization = (mt.operational_machines / mt.total_machines) * 100
            # Or use your actual utilization calculation logic here
            machine_type_data.append({
                'name': mt.name,
                'utilization': min(round(utilization), 100)  # Cap at 100%
            })
    
    # Work center capacity data
    work_centers = WorkCenters.objects.all()
    work_center_names = [wc.name for wc in work_centers]
    work_center_available = [40, 40, 40, 40]  # Assuming 40 hours available per week
    work_center_scheduled = [32, 28, 35, 25]  # Scheduled hours
    
    context = {
        'boms':boms,
        'machine_types': MachineType.objects.all(),
        'work_centers': work_centers,
        'operational_machines_count': operational_machines_count,
        'maintenance_machines_count': maintenance_machines_count,
        'ooo_machines_count': ooo_machines_count,
        'retired_machines_count': retired_machines_count,
        'active_orders_count': active_orders_count,
        'upcoming_maintenance': upcoming_maintenance,
        'production_schedules': production_schedules,
        'machine_type_names': json.dumps([mt['name'] for mt in machine_type_data]),
        'machine_type_utilization': json.dumps([mt['utilization'] for mt in machine_type_data]),
        'work_center_names': work_center_names,
        'work_center_available': work_center_available,
        'work_center_scheduled': work_center_scheduled,
        'components': components,  # Replace with actual BOMHeader queryset
    }
    
    return render(request, 'MachinePlan/dashboard.html', context)


class MachineScheduleListView(ListView):
    model = MachineSchedule
    template_name = 'MachinePlan/machine_scheduling_list.html'
    context_object_name = 'schedules'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by status (from detail table)
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(details__status=status)

        # Filter by machine (from detail table)
        machine_id = self.request.GET.get('machine')
        if machine_id:
            queryset = queryset.filter(details__machine_id=machine_id)

        # Filter by date range (main schedule)
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(
                scheduled_start__date__gte=start_date,
                scheduled_end__date__lte=end_date
            )

        # Filter by PO number
        po_number = self.request.GET.get('po_order')
        if po_number:
            queryset = queryset.filter(production_order__order_number=po_number)

        # Filter by BOM
        bom_header = self.request.GET.get('bom_header')
        if bom_header:
            queryset = queryset.filter(component__name=bom_header)

        # ✅ distinct to avoid duplicates when joining details
        return queryset.select_related('production_order', 'component').prefetch_related('details').distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['machines'] = Machine.objects.all()
        context['status_choices'] = MachineScheduleDetail._meta.get_field('status').choices

        # Keep selected filters
        context['selected_po'] = self.request.GET.get('po_order', '')
        context['selected_component'] = self.request.GET.get('bom_header', '')

        return context


class MachineSchedulingDeleteView(DeleteView):
    model = MachineScheduling
    template_name = 'MachinePlan/machine_scheduling_confirm_delete.html'
    success_url = reverse_lazy('mcp:machine_scheduling_list')

def load_routings(request):
    """AJAX view to load routings based on selected component"""
    user_id = request.session.get('user_id', '')
    try:
        component_id = request.GET.get('component_id')
        if component_id:
            # Get routings for the component
            routings = RoutingMaster.objects.filter(component_id=component_id).order_by('sequence')
            
            # Prepare routing data for JSON response
            routing_data = []
            for routing in routings:
                routing_data.append({
                    'id': routing.id,
                    'operation_name': str(routing.operation),
                    'operation_code': routing.operation.code if routing.operation else '',
                    'sequence': routing.sequence,
                    'work_center': routing.work_center.name if routing.work_center else '',
                    'work_center_id': routing.work_center.id if routing.work_center else None,
                    'setup_time': routing.setup_time,
                    'run_time_per_unit': routing.run_time_per_unit
                })
            
            # Return JSON response
            return JsonResponse({
                'success': True,
                'routings': routing_data,
                'count': len(routing_data)
            })
        
        return JsonResponse({'success': False, 'error': 'Invalid component ID'}, status=400)
    
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        fun = tb[0].name if tb else 'unknown'
        print(f"Error in load_routings: {e}")
        # callproc("stp_error_log", [fun, str(e), user_id])
        return JsonResponse({
            'success': False, 
            'error': 'Oops...! Something went wrong!'
        }, status=500)

def load_machines(request):
    """AJAX view to load machines based on selected routing"""
    try:
        routing_id = request.GET.get('routing_id')
        if not routing_id:
            return JsonResponse({'success': False, 'error': 'No routing ID provided'}, status=400)
        
        # Get routing and work center
        routing = RoutingMaster.objects.get(id=routing_id)
        work_center = routing.work_center
        
        # Get machines for this work center
        machines = Machine.objects.filter(work_center=work_center)
        
        # Get machine status information
        now = timezone.now()
        machines_data = []
        
        for machine in machines:
            # Check current and upcoming schedules
            current_schedules = MachineScheduling.objects.filter(
                machine=machine
            ).exclude(status__in=['COMPLETED', 'CANCELLED']).order_by('scheduled_start')
            
            status_info = {
                'current': 'Available',
                'next_available': None,
                'busy_until': None
            }
            
            for schedule in current_schedules:
                if schedule.scheduled_start <= now <= schedule.scheduled_end:
                    status_info['current'] = 'Busy'
                    status_info['busy_until'] = schedule.scheduled_end
                    break
                elif schedule.scheduled_start > now:
                    status_info['next_available'] = schedule.scheduled_start
                    break
            
            # Safely get machine code - use empty string if attribute doesn't exist
            machine_code = getattr(machine, 'code', '')  # This won't raise error if code doesn't exist
            
            machines_data.append({
                'id': machine.id,
                'name': machine.name,
                'code': machine_code,  # Use the safely retrieved code
                'work_center_id': work_center.id,
                'work_center_name': work_center.name,
                'status': status_info['current'],
                'busy_until': status_info['busy_until'].strftime('%Y-%m-%d %H:%M:%S') if status_info['busy_until'] else None,
                'next_available': status_info['next_available'].strftime('%Y-%m-%d %H:%M:%S') if status_info['next_available'] else None
            })
        
        # Return JSON response
        return JsonResponse({
            'success': True,
            'machines': machines_data,
            'count': len(machines_data),
            'work_center': {
                'id': work_center.id,
                'name': work_center.name
            }
        })
        
    except RoutingMaster.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Routing not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)
    
def get_routings(request, component_id):
    component = get_object_or_404(BOMHeader, id=component_id)

    # ✅ get production orders linked to component
    production_orders = (
        ProductionOrder.objects.filter(bom=component)
        .select_related("order_status")
    )

    # ✅ fetch schedules for those production orders
    schedules = (
        MachineSchedule.objects.filter(
            component=component,
            production_order__in=production_orders
        )
        .prefetch_related("details", "production_order__order_status")
    )

    # build routing -> production orders map
    routing_po_map = {}
    routing_status_map = {}

    for schedule in schedules:
        po = schedule.production_order
        if not po or not po.order_status:
            continue

        # ✅ assign status correctly
        if po.order_status.id == 1:
            po_status = "Unplanned"
        elif 2 <= po.order_status.id <= 4:
            po_status = "Planned"
        elif 5 <= po.order_status.id <= 7:
            po_status = "In Progress"
        else:
            po_status = "Completed"

        for detail in schedule.details.all():
            rid = detail.routing_id

            # routing -> list of production orders (avoid duplicates)
            if rid not in routing_po_map:
                routing_po_map[rid] = []
            if not any(x["production_order"] == str(po) for x in routing_po_map[rid]):
                routing_po_map[rid].append({
                    "production_order": str(po),
                    "status": po_status,
                })

            # routing -> table status (use consistent rules)
            routing_status_map[rid] = po_status

    # ✅ get routings for this component
    routings = RoutingMaster.objects.filter(component=component).select_related(
        "operation", "work_center", "skill"
    )

    grouped = {}
    for r in routings:
        if r.name not in grouped:
            grouped[r.name] = {
                "rows": [],
                "production_orders": []
            }

        # add production orders (above table section)
        grouped[r.name]["production_orders"].extend(
            routing_po_map.get(r.id, [])
        )

        # add routing detail rows (status consistent with po_status)
        grouped[r.name]["rows"].append({
            "id": r.id,
            "sequence": r.sequence,
            "operation_name": r.operation.name if r.operation else "",
            "employee_need": r.employees_needed if r.employees_needed else "",
            "work_center": r.work_center.name if r.work_center else "",
            "min_proficiency": r.min_proficiency.name if r.min_proficiency else "",
            "skill": r.skill.skill_name if r.skill else "",
            "status": routing_status_map.get(r.id, "Pending"),
        })

    # convert to list of dicts
    data = []
    for name, details in grouped.items():
        data.append({
            "name": name,
            "production_orders": details["production_orders"],  # ⬅️ new section
            "rows": details["rows"]
        })

    return JsonResponse(data, safe=False)


def get_assignment_data(request, routing_id):
    """
    Return machine and employee list for each routing row based on work_center and skill.
    """
    try:
        routing = get_object_or_404(RoutingMaster, id=routing_id)

        # Get all rows that belong to the same routing (same name)
        rows = RoutingMaster.objects.filter(name=routing.name)

        assignment_rows = []
        for row in rows:
            # Machines filtered by work_center
            machines = Machine.objects.filter(
                work_center=row.work_center
            ).values("id", "name")

            # Employees filtered by skill (and proficiency if required)
            employees = EmployeeSkill.objects.filter(
                skill=row.skill,proficiency= row.min_proficiency
            ).select_related("employee")  # join to employee

            employee_list = [
                {
                    "id": es.employee.id,
                    "employee_name": es.employee.employee_name,
                    "proficiency": es.proficiency.name
                }
                for es in employees
            ]

            assignment_rows.append({
                "row_id": row.id,
                "operation": row.operation.name if row.operation else "",   # ✅ clean operation
                "skill": row.skill.skill_name if row.skill else "",        # ✅ clean skill
                "sequence": row.sequence,
                "machines": list(machines),
                "employees": employee_list,
            })

        return JsonResponse({"rows": assignment_rows})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)




class MachineScheduleCreateView(View):
    template_name = "MachinePlan/machine_scheduling_form.html"

    def get(self, request, *args, **kwargs):
        context = {
            "production_orders": ProductionOrder.objects.filter(machineschedule__isnull=True),
            "components": BOMHeader.objects.all(),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        try:
            # --- Save Master Schedule ---
            schedule = MachineSchedule.objects.create(
                name=request.POST.get("name"),
                production_order_id=request.POST.get("production_order"),
                component_id=request.POST.get("component"),
                scheduled_start=parse_datetime(request.POST.get("scheduled_start")),
                scheduled_end=parse_datetime(request.POST.get("scheduled_end")),
            )

            # --- Save Routing + Workstation assignments ---
            assignments_json = request.POST.get("assignments_json")
            if assignments_json:
                assignments = json.loads(assignments_json)

                for row in assignments:
                    routing_detail_id = row.get("routing_detail_id")
                    workstation_id = row.get("workstation_id")
                    routing_detail_id = row.get("routing_detail_id")
                    routing = get_object_or_404(RoutingDetail,id = routing_detail_id )
                    machine = get_object_or_404(WorkStations, id  = workstation_id).machine

                    routing_detail = RoutingDetail.objects.filter(id=routing_detail_id).first()
                    if not routing_detail:
                        continue

                    

                    MachineScheduleDetail.objects.create(
                        schedule=schedule,
                        routing = routing_detail.routing,
                        machine=machine,
                        seq=routing_detail.sequence,
                        workstation_id=workstation_id,
                        work_center=routing_detail.work_center,
                    )
                    schedule.routing = routing_detail.routing
                    schedule.save()

            return redirect(reverse("mcp:machine_scheduling_list"))

        except Exception as e:
            return render(request, self.template_name, {
                "production_orders": ProductionOrder.objects.all(),
                "components": BOMHeader.objects.all(),
                "error": str(e)
            })

        
# views.py
class MachineScheduleUpdateView(View):
    template_name = "MachinePlan/machine_scheduling_edit.html"

    def get(self, request, pk, *args, **kwargs):
        schedule = get_object_or_404(MachineSchedule, pk=pk)

        # ✅ Fetch all detail rows for this schedule
        details = (
            MachineScheduleDetail.objects
            .filter(schedule=schedule)
            .select_related("routing", "machine", "workstation", "work_center")
        )

        pre_assignments = []

        for d in details:
            # ✅ Extract all possible workstations for this work_center
            workstation_list = []
            if d.work_center and d.work_center.workstation_ids:
                try:
                    ws_ids = [int(x) for x in d.work_center.workstation_ids.split(",") if x.strip()]
                    workstation_list = WorkStations.objects.filter(id__in=ws_ids)
                except ValueError:
                    workstation_list = []

            # ✅ Build record for JS
            pre_assignments.append({
                "routing_detail_id": d.routing.id if d.routing else None,
                "sequence": d.seq or "",
                "operation": getattr(d.routing, "name", ""),  # from RoutingMaster
                "employee_needed": "",
                "proficiency": "",
                "skill": "",
                "work_center": d.work_center.name if d.work_center else "",
                "workstation_id": d.workstation.id if d.workstation else None,  # ✅ preselected workstation
                "workstations": [
                    {
                        "id": w.id,
                        "name": w.name,
                        "employee_count": getattr(w, "employee_count", 0),
                    }
                    for w in workstation_list
                ],
            })

        context = {
            "schedule": schedule,
            "production_orders": ProductionOrder.objects.all(),
            "components": BOMHeader.objects.all(),
            "assignments_json": json.dumps(pre_assignments),
        }

        return render(request, self.template_name, context)






    def post(self, request, pk, *args, **kwargs):
        schedule = get_object_or_404(MachineSchedule, pk=pk)

        name = request.POST.get("name")
        scheduled_start = request.POST.get("scheduled_start")
        scheduled_end = request.POST.get("scheduled_end")
        assignments_json = request.POST.get("assignments_json", "[]")

        # Update schedule main fields
        schedule.name = name
        schedule.scheduled_start = scheduled_start
        schedule.scheduled_end = scheduled_end
        schedule.save()

        # Delete old MachineScheduleDetail rows
        schedule.details.all().delete()

        # Create new MachineScheduleDetail rows from assignments_json
        if assignments_json:
            assignments = json.loads(assignments_json)

            for row in assignments:
                routing_detail_id = row.get("routing_detail_id")
                workstation_id = row.get("workstation_id")

                if not routing_detail_id or not workstation_id:
                    continue

                routing_detail = get_object_or_404(RoutingDetail, id=routing_detail_id)
                machine = get_object_or_404(WorkStations, id=workstation_id).machine

                MachineScheduleDetail.objects.create(
                    schedule=schedule,
                    routing=routing_detail.routing,
                    machine=machine,
                    seq=routing_detail.sequence,
                    workstation_id=workstation_id,
                    work_center=routing_detail.work_center,
                )

            # Update schedule.routing to last routing used
            schedule.routing = routing_detail.routing
            schedule.save()

        return redirect(reverse("mcp:machine_scheduling_list"))



def routing_create(request, pk=None):
    """
    Handles both create and edit (if pk is given)
    """
    routing = get_object_or_404(RoutingMaster, pk=pk) if pk else None

    if request.method == "POST":
        # Save Routing Master (header)
        name = request.POST.get("name")
        component_id = request.POST.get("component")
        notes = request.POST.get("notes")

        component = BOMHeader.objects.get(id=component_id)

        if routing:  # Edit mode
            routing.name = name
            routing.component = component
            routing.notes = notes
            routing.created_by = get_object_or_404(CustomUser, id =  request.session.get('user_id', ''))
            routing.save()
            # Clear old details (replace with new)
            routing.details.all().delete()
        else:  # Create mode
            routing = RoutingMaster.objects.create(
                name=name,
                component=component,
                notes=notes,
                created_by = get_object_or_404(CustomUser, id =  request.session.get('user_id', ''))
            )

        # Save Routing Details
        operations = request.POST.getlist("operation[]")
        work_centers = request.POST.getlist("work_center[]")
        sequences = request.POST.getlist("sequence[]")
        employees_needed = request.POST.getlist("employees_needed[]")
        skills = request.POST.getlist("skill[]")
        proficiencies = request.POST.getlist("min_proficiency[]")

        for i in range(len(sequences)):
            RoutingDetail.objects.create(
                routing=routing,
                sequence=sequences[i],
                operation=Operation.objects.get(id=operations[i]) if operations[i] else None,
                work_center=WorkCenters.objects.get(id=work_centers[i]) if work_centers[i] else None,
                employees_needed=employees_needed[i],
                skill=Skill.objects.get(id=skills[i]) if skills[i] else None,
                min_proficiency=Proficeincy.objects.get(id=proficiencies[i]) if proficiencies[i] else None,
            )

        return redirect("mcp:routing_list")

    # -----------------------------
    # GET request → open form
    # -----------------------------
    context = {
        "object": routing,  # RoutingMaster (None in create, filled in edit)
        "details": routing.details.all() if routing else [],  # Pre-fill RoutingDetails
        "operations": Operation.objects.all(),
        "work_centers": WorkCenters.objects.all(),
        "skills": Skill.objects.all(),
        "proficiencies": Proficeincy.objects.all(),
        "components": BOMHeader.objects.all(),
    }
    return render(request, "MachinePlan/routing_form.html", context)

class WorkStationListView(ListView):
    model = WorkStations
    template_name = 'MachinePlan/workstation_list.html'
    context_object_name = 'workstations'
    
    def get_queryset(self):
        return WorkStations.objects.select_related('machine', 'created_by', 'updated_by')

class WorkStationCreateView(CreateView):
    model = WorkStations
    form_class = WorkStationForm  # Use the custom form
    template_name = 'MachinePlan/workstation_form.html'
    success_url = reverse_lazy('mcp:workstation_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'WorkStation created successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create WorkStation'
        context['submit_text'] = 'Create'
        return context

class WorkStationUpdateView(UpdateView):
    model = WorkStations
    form_class = WorkStationForm  # Use the custom form
    template_name = 'MachinePlan/workstation_form.html'
    success_url = reverse_lazy('mcp:workstation_list')
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'WorkStation updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update WorkStation'
        context['submit_text'] = 'Update'
        return context

class WorkStationDeleteView(DeleteView):
    model = WorkStations
    success_url = reverse_lazy('mcp:workstation_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'WorkStation deleted successfully!')
        return super().delete(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)
    
def get_component_by_production_order(request):
    production_order_id = request.GET.get('production_order_id')

    try:
        po = ProductionOrder.objects.get(id=production_order_id)
        component = po.bom
        return JsonResponse({
            'component_id': component.id,
            'component_name': component.name
        })
    except ProductionOrder.DoesNotExist:
        return JsonResponse({'error': 'Production order not found'}, status=404)
    
def get_routing_data(request):
    component_id = request.POST.get("component_id")

    try:
        # ✅ Step 1: Get routing for that component
        routing = RoutingMaster.objects.filter(component=component_id).first()
        if not routing:
            return JsonResponse({"schedules": []})

        routing_id = routing.id  # ✅ Now safe to access

        # ✅ Step 2: Get related routing details
        routing_details = RoutingDetail.objects.filter(routing=routing)
        routing_detail_ids = routing_details.values_list("id", flat=True)

        # ✅ Step 3: Get matching machine schedules
        machine_schedules = MachineSchedule.objects.filter(component_id=component_id)

        # ✅ Step 4: Prepare response data (with start and end dates)
        data = []
        for schedule in machine_schedules:
            data.append({
                "start_date": schedule.scheduled_start.strftime("%Y-%m-%dT%H:%M:%S"),
                "end_date": schedule.scheduled_end.strftime("%Y-%m-%dT%H:%M:%S") if schedule.scheduled_end else None,
                "production_order": getattr(schedule.production_order, "order_number", str(schedule.production_order.id)),
            })

        return JsonResponse({
            "schedules": data,
            "routing_id": routing_id
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    
def get_routing_details(request):
    routing_id = request.GET.get("routing_id")

    try:
        if not routing_id:
            return JsonResponse({"error": "Missing routing_id"}, status=400)

        routing_details = RoutingDetail.objects.filter(routing_id=routing_id).order_by("sequence")
        data = []

        for detail in routing_details:
            # print(detail.id)
            # Get work center
            work_center = getattr(detail, "work_center", None)
            work_center_name = work_center.name if work_center else ""
            work_center_id = work_center.id if work_center else None

            # 🔹 Prepare workstation dropdown data
            workstation_dropdown = []
            if work_center and getattr(work_center, "workstation_ids", None):
                workstation_ids = [
                    int(w.strip()) for w in work_center.workstation_ids.split(",") if w.strip().isdigit()
                ]

                for ws in WorkStations.objects.filter(id__in=workstation_ids):
                    # Count employees from comma-separated employee_ids
                    emp_count = (
                        len([e for e in ws.employee.split(",") if e.strip().isdigit()])
                        if ws.employee else 0
                    )
                    workstation_dropdown.append({
                        "id": ws.id,
                        "name": ws.name,
                        "employee_count": emp_count,
                    })

            # 🔹 Construct row data
            data.append({
                "sequence": detail.sequence,
                "routing_detail_id":detail.id,
                "operation": getattr(detail.operation, "name", "") if detail.operation else "",
                "employee_needed": detail.employees_needed,
                "proficiency": (
                    detail.min_proficiency.name
                    if hasattr(detail.min_proficiency, "name")
                    else str(detail.min_proficiency)
                    if detail.min_proficiency
                    else ""
                ),
                "skill": getattr(detail.skill, "skill_name", "") if detail.skill else "",
                "work_center": work_center_name,
                "work_center_id": work_center_id,
                "workstations": workstation_dropdown,  # ✅ include dropdown data here
            })

        return JsonResponse({"routing_details": data})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



    
def get_workstation_details(request):
    workstation_id = request.GET.get("workstation_id")

    if not workstation_id:
        return JsonResponse({"success": False, "error": "Missing workstation_id"}, status=400)

    try:
        ws = WorkStations.objects.get(id=workstation_id)

        # 🔹 Machine info
        machine_name = ws.machine.name if ws.machine else "N/A"
        capacity = getattr(ws.machine, "capacity", "N/A")
        status = getattr(ws.machine, "status", "N/A")

        # 🔹 Employees linked (comma-separated)
        employee_data = []
        if ws.employee:
            emp_ids = [int(e.strip()) for e in ws.employee.split(",") if e.strip().isdigit()]

            for emp in Employee.objects.filter(id__in=emp_ids):
                emp_skills = EmployeeSkill.objects.filter(employee=emp)
                skills_data = [
                    {"skill_name": s.skill.skill_name, "proficiency": s.proficiency.name}
                    for s in emp_skills
                ]

                employee_data.append({
                    "id": emp.id,
                    "name": emp.employee_name,
                    "skills": skills_data
                })

        return JsonResponse({
            "success": True,
            "machine_name": machine_name,
            "capacity": capacity,
            "status": status,
            "employees": employee_data
        })

    except WorkStations.DoesNotExist:
        return JsonResponse({"success": False, "error": "Workstation not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    

def get_component_qty(production_id):
    try:
        po = ProductionOrder.objects.get(id=production_id)
        return po.quantity  # or po.component.quantity if stored on component
    except ProductionOrder.DoesNotExist:
        return 0
    
def get_machines_by_workstation(workstation_id):

    try:
        workstation = WorkStations.objects.get(id=workstation_id)
        # return as a list to keep compatibility with loops
        return [workstation.machine]
    except WorkStations.DoesNotExist:
        return []


def get_numeric_capacity(capacity_str):
    """
    Extract numeric part from a string like "50 units/hour"
    Returns float
    """
    match = re.search(r'\d+\.?\d*', capacity_str)  # matches integers or decimals
    if match:
        return float(match.group())
    return 0


def calculate_end_date(request):
    if request.method == "POST":
        import json
        from datetime import datetime, timedelta

        production_id = request.POST.get("production_id")
        workstation_ids = json.loads(request.POST.get("workstation_ids", "[]"))
        scheduled_start = request.POST.get("scheduled_start")

        # get component quantity
        try:
            po = ProductionOrder.objects.get(id=production_id)
            component_qty = po.quantity
        except ProductionOrder.DoesNotExist:
            return JsonResponse({"error": "Invalid production ID"}, status=400)

        total_hours_needed = 0

        for ws_id in workstation_ids:
            machines = get_machines_by_workstation(ws_id)
            for machine in machines:
                # extract number from "50 units/hour"
                capacity_per_shift = get_numeric_capacity(machine.capacity)
                if capacity_per_shift > 0:
                    total_hours_needed += (component_qty / capacity_per_shift) * 8

        start_dt = datetime.strptime(scheduled_start, "%Y-%m-%dT%H:%M")
        end_dt = start_dt + timedelta(hours=total_hours_needed)

        return JsonResponse({"end_date": end_dt.strftime("%Y-%m-%dT%H:%M")})

    return JsonResponse({"error": "Invalid request"}, status=400)