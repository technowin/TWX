# MachinePlan/views.py
from datetime import date, datetime, timedelta
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
from MaterialPlan.models import MaterialPlan, ProductionOrder
from .models import *
from .forms import *
from .forms import *
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q
from django.utils import timezone
from django.template.loader import render_to_string

from django.db import transaction

from django.utils.dateparse import parse_datetime


def parse_custom_datetime(dt_str):
    if not dt_str:
        return None
    for fmt in ("%d-%m-%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return None

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
    def form_valid(self, form):
        operation = form.save(commit=False)
        operation.cost_per_unit = form.cleaned_data['cost_per_unit']
        operation.save()
        return super().form_valid(form)

class OperationUpdateView(UpdateView):
    model = Operation
    form_class = OperationForm
    template_name = 'MachinePlan/operation_form.html'
    success_url = reverse_lazy('mcp:operation_list')
    def form_valid(self, form):
        operation = form.save(commit=False)
        operation.cost_per_unit = form.cleaned_data['cost_per_unit']
        operation.save()
        return super().form_valid(form)


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
    # Get parameters from URL (they might be None)
        po_order_param = request.GET.get("po_order")
        bom_header_param = request.GET.get("bom_header")

        po_order = None
        bom_header = None

        # Only fetch if provided and valid
        if po_order_param:
            po_order = get_object_or_404(ProductionOrder, order_number = po_order_param).id
        if bom_header_param:
            bom_header = get_object_or_404(BOMHeader, name = bom_header_param).id

        # Determine index based on data availability
        index = 1 if (po_order and bom_header) else 0

        context = {
            "production_orders": ProductionOrder.objects.filter(machineschedule__isnull=True),
            "components": BOMHeader.objects.all(),
            "po_order": po_order,
            "bom_header": bom_header,
            "index": index,
        }

        return render(request, self.template_name, context)


    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            # Start transaction
            with transaction.atomic():
            # --- 1️⃣ Save Master Schedule ---
                scheduled_start = parse_datetime(request.POST.get("scheduled_start"))
                scheduled_end = parse_datetime(request.POST.get("scheduled_end"))
                production_order = request.POST.get("production_order")
                index = request.POST.get("index")

                schedule = MachineSchedule.objects.create(
                    name=request.POST.get("name"),
                    production_order_id=request.POST.get("production_order"),
                    component_id=request.POST.get("component"),
                    scheduled_start=scheduled_start,
                    scheduled_end=scheduled_end,
                    created_by=request.user,
                )

                # --- Calculate ISO Week Range ---
                start_week = scheduled_start.isocalendar()[1]
                end_week = scheduled_end.isocalendar()[1]
                week_display = f"Week {start_week}" if start_week == end_week else f"Week {start_week} - Week {end_week}"

                # --- 2️⃣ Save Routing + Workstation + Machine + Employee Assignments ---
                assignments_json = request.POST.get("assignments_json")
                if assignments_json:
                    assignments = json.loads(assignments_json)
                    for row in assignments:
                        routing_detail_id = row.get("routing_detail_id")
                        workstation_id = row.get("workstation_id")
                        machine_id = row.get("machine_id")
                        employee_ids = row.get("employee_ids", [])

                        routing_detail = get_object_or_404(RoutingDetail, id=routing_detail_id)

                        MachineScheduleDetail.objects.create(
                            schedule=schedule,
                            routing=routing_detail.routing,
                            machine_id=machine_id,
                            operation = routing_detail.operation,
                            seq=routing_detail.sequence,
                            workstation_id=workstation_id,
                            work_center=routing_detail.work_center,
                            employee=",".join(map(str, employee_ids)) if employee_ids else "",
                        )

                        if not schedule.routing_id:
                            schedule.routing = routing_detail.routing
                            schedule.save()

                # --- 3️⃣ Save Shift Table Data ---
                shift_table_json = request.POST.get("shift_table_json")
                if shift_table_json:
                    shift_table_data = json.loads(shift_table_json)
                    production_order_id = request.POST.get("production_order")
                    component_id = request.POST.get("component")

                    for row in shift_table_data:
                        seq = row.get("sequence")
                        employee_names = row.get("employee_ids", [])
                        employee_ids = list(
                            Employee.objects.filter(employee_name__in=employee_names)
                            .values_list("id", flat=True)
                        )
                        employee_ids_str = ",".join(map(str, employee_ids))

                        # Find matching detail record by schedule + sequence
                        detail = MachineScheduleDetail.objects.filter(schedule=schedule, seq=seq).first()
                        if not detail:
                            raise Exception(f"No detail found for sequence {seq}")

                        ShiftTable.objects.create(
                            machine_schedule=schedule,
                            machine_schedule_detail=detail,
                            sequence=seq,
                            production_order=get_object_or_404(ProductionOrder, id=production_order_id),
                            bom_component=get_object_or_404(BOMHeader, id=component_id),
                            workstation=get_object_or_404(WorkStations, name=row.get("workstation", "")),
                            machine=get_object_or_404(Machine, name=row.get("machine", "")).id,
                            employees=employee_ids_str,
                            shift=get_object_or_404(Shift, shift_name=row.get("shift_name", "")),
                            start_time=parse_custom_datetime(row.get("start")),
                            end_time=parse_custom_datetime(row.get("end")),
                            total_quantity=row.get("total_quantity") or 0,
                            completed_quantity=row.get("completed_quantity") or 0,
                            remaining_quantity=row.get("remaining_quantity") or 0,
                            created_by=request.user,
                            week=week_display,  # 🆕 Store calculated week value here
                        )
                if index =="1":
                    production = get_object_or_404(ProductionOrder,id = production_order)
                    production.order_status = get_object_or_404(StatusAction, id = 2)
                    production.save()

                    return redirect("plm_index")
                else:
                    return redirect(reverse("mcp:machine_scheduling_list"))

        except Exception as e:
            # Transaction will automatically rollback if exception occurs
            transaction.set_rollback(True)
            return render(request, self.template_name, {
                "production_orders": ProductionOrder.objects.all(),
                "components": BOMHeader.objects.all(),
                "error": f"Error while saving schedule: {str(e)}",
            })


# views.py
class MachineScheduleUpdateView(View):
    template_name = "MachinePlan/machine_scheduling_edit.html"

    def get(self, request, pk, *args, **kwargs):
        
        schedule = get_object_or_404(MachineSchedule, pk=pk)

        # Get assignments data
        assignments_data = self.get_assignments(schedule)
        
        # Get shift table data
        shift_table_data = self.get_shift_table(schedule)
        
        # DEBUG: Print the actual data before JSON serialization
        print("=== DEBUG BEFORE JSON SERIALIZATION ===")
        
        print("--- ASSIGNMENTS DATA ---")
        for i, assignment in enumerate(assignments_data):
            print(f"Assignment {i}:")
        
        print("--- SHIFT TABLE DATA ---")
        print(f"Number of shift records: {len(shift_table_data)}")
        for i, shift in enumerate(shift_table_data):
            print(f"Shift {i}:")
        
        # Convert to JSON and debug
        assignments_json = json.dumps(assignments_data, default=str)
        shift_table_json = json.dumps(shift_table_data, default=str)
        
        
        context = {
            "schedule": schedule,
            "production_orders": ProductionOrder.objects.all(),
            "components": BOMHeader.objects.all(),
            "assignments_json": assignments_json,
            "shift_table_json": shift_table_json,
        }
        return render(request, self.template_name, context)

    def get_assignments(self, schedule):
        details = MachineScheduleDetail.objects.filter(schedule=schedule).select_related(
            'routing', 'workstation', 'machine', 'work_center'
        )
        assignments = []
        
        for d in details:
            # Get the routing detail
            routing_detail = None
            if d.routing and d.seq:
                try:
                    seq_num = int(d.seq)
                    routing_detail = RoutingDetail.objects.filter(
                        routing=d.routing, 
                        sequence=seq_num
                    ).select_related('operation', 'skill', 'min_proficiency').first()
                except (ValueError, TypeError):
                    routing_detail = None
            
            # Get workstations from work_center
            workstations = []
            if d.work_center and hasattr(d.work_center, 'workstation_ids') and d.work_center.workstation_ids:
                try:
                    workstation_ids = [int(id.strip()) for id in d.work_center.workstation_ids.split(",") if id.strip()]
                    workstations = WorkStations.objects.filter(id__in=workstation_ids)
                except Exception:
                    pass
            
            # Get machines and employees for the selected workstation (if available)
            machines = []
            employees = []
            if d.workstation:
                if hasattr(d.workstation, 'machine') and d.workstation.machine:
                    try:
                        machine_ids = [int(id.strip()) for id in d.workstation.machine.split(",") if id.strip()]
                        machines = Machine.objects.filter(id__in=machine_ids)
                    except Exception:
                        pass
                
                if hasattr(d.workstation, 'employee') and d.workstation.employee:
                    try:
                        employee_ids = [int(id.strip()) for id in d.workstation.employee.split(",") if id.strip()]
                        employees = Employee.objects.filter(id__in=employee_ids)
                    except Exception:
                        pass
            
            # Make sure we're using the exact field names that JavaScript expects
            assignment_data = {
                "routing_detail_id": d.id,
                "routing_id": d.routing.id if d.routing else None,
                "workstation_id": d.workstation.id if d.workstation else None,  # This should be set!
                "machine_id": d.machine.id if d.machine else None,  # This should be set!
                "employee_ids": [int(e) for e in d.employee.split(",") if e and e.strip()] if d.employee else [],  # This should be set!
                "sequence": d.seq,
                "operation": routing_detail.operation.name if routing_detail and routing_detail.operation else "",
                "employee_needed": routing_detail.employees_needed if routing_detail else 0,
                "skill": routing_detail.skill.skill_name if routing_detail and routing_detail.skill else "",
                "proficiency": routing_detail.min_proficiency if routing_detail and routing_detail.min_proficiency else "",
                "work_center": d.work_center.name if d.work_center else "",
                "workstations": [
                    {"id": ws.id, "name": ws.name, "employee_count": getattr(ws, 'employee_count', 0)} 
                    for ws in workstations
                ],
                "machines": [
                    {"id": m.id, "name": m.name} 
                    for m in machines
                ],
                "employees": [
                    {"id": emp.id, "employee_name": emp.employee_name} 
                    for emp in employees
                ]
            }
            
            # Debug print to verify the data
            print(f"Assignment data for detail {d.id}: workstation_id={assignment_data['workstation_id']}, machine_id={assignment_data['machine_id']}, employee_ids={assignment_data['employee_ids']}")
            
            assignments.append(assignment_data)
        
        return assignments

    def get_shift_table(self, schedule):
        """Extract data from ShiftTable"""
        shifts = ShiftTable.objects.filter(machine_schedule=schedule).select_related(
            'workstation', 'shift'
        )
        data = []
        
        print("=== DEBUG SHIFT TABLE DATA ===")
        for s in shifts:
            
            # Get employee names
            employee_names = []
            if s.employees:
                try:
                    employee_ids = [int(i.strip()) for i in s.employees.split(",") if i.strip()]
                    employee_names = list(
                        Employee.objects.filter(id__in=employee_ids)
                        .values_list("employee_name", flat=True)
                    )
                except Exception as e:
                    print(f"Error parsing employees: {e}")

            # Get machine name
            machine_name = ""
            if s.machine:  # s.machine is already the machine ID
                try:
                    machine_obj = Machine.objects.filter(id=s.machine).first()
                    machine_name = machine_obj.name if machine_obj else ""
                except Exception as e:
                    print(f"Error getting machine: {e}")

            shift_data = {
                "sequence": s.sequence,
                "workstation": s.workstation.name if s.workstation else "",
                "machine": machine_name,
                "employee_ids": employee_names,
                "shift_name": s.shift.shift_name if s.shift else "",
                "start": s.start_time.strftime("%Y-%m-%d %H:%M") if s.start_time else "",
                "end": s.end_time.strftime("%Y-%m-%d %H:%M") if s.end_time else "",
                "total_quantity": s.total_quantity,
                "completed_quantity": s.completed_quantity,
                "remaining_quantity": s.remaining_quantity,
            }
            
            print(f"Shift data: {shift_data}")
            data.append(shift_data)
    
        return data

    
    def post(self, request, pk, *args, **kwargs):
        try:
            with transaction.atomic():
                schedule = get_object_or_404(MachineSchedule, pk=pk)

                # --- 1️⃣ Update Master Schedule ---
                schedule.name = request.POST.get("name")
                production_order_id = request.POST.get("production_order")
                component_id = request.POST.get("component")
                
                if production_order_id:
                    schedule.production_order_id = production_order_id
                if component_id:
                    schedule.component_id = component_id
                    
                schedule.scheduled_start = parse_datetime(request.POST.get("scheduled_start"))
                schedule.scheduled_end = parse_datetime(request.POST.get("scheduled_end"))
                schedule.updated_by = request.user
                schedule.save()

                # --- 2️⃣ Delete old details before re-saving ---
                MachineScheduleDetail.objects.filter(schedule=schedule).delete()
                ShiftTable.objects.filter(machine_schedule=schedule).delete()

                # --- 3️⃣ Save Routing + Assignments ---
                assignments_json = request.POST.get("assignments_json")
                if assignments_json:
                    assignments = json.loads(assignments_json)
                    for row in assignments:
                        routing_detail_id = row.get("routing_detail_id")
                        workstation_id = row.get("workstation_id")
                        machine_id = row.get("machine_id")
                        employee_ids = row.get("employee_ids", [])

                        routing_detail = get_object_or_404(RoutingDetail, id=routing_detail_id)

                        MachineScheduleDetail.objects.create(
                            schedule=schedule,
                            routing=routing_detail.routing,
                            machine_id=machine_id,
                            operation = routing_detail.operation,
                            seq=routing_detail.sequence,
                            workstation_id=workstation_id,
                            work_center=routing_detail.work_center,
                            employee=",".join(map(str, employee_ids)) if employee_ids else "",
                        )

                # --- 4️⃣ Save Shift Table ---
                shift_table_json = request.POST.get("shift_table_json")
                if shift_table_json:
                    shift_table_data = json.loads(shift_table_json)
                    production_order_id = request.POST.get("production_order")
                    component_id = request.POST.get("component")

                    start_week = schedule.scheduled_start.isocalendar()[1]
                    end_week = schedule.scheduled_end.isocalendar()[1]
                    week_display = f"Week {start_week}" if start_week == end_week else f"Week {start_week} - Week {end_week}"

                    for row in shift_table_data:
                        seq = row.get("sequence")
                        employee_names = row.get("employee_ids", [])
                        employee_ids = list(
                            Employee.objects.filter(employee_name__in=employee_names)
                            .values_list("id", flat=True)
                        )
                        employee_ids_str = ",".join(map(str, employee_ids))

                        detail = MachineScheduleDetail.objects.filter(schedule=schedule, seq=str(seq)).first()
                        if not detail:
                            print(f"Warning: No detail found for sequence {seq}")
                            continue

                        # Parse datetime with error handling
                        start_time = parse_custom_datetime(row.get("start"))
                        end_time = parse_custom_datetime(row.get("end"))
                        
                        # Debug print to check parsed datetimes
                        print(f"Parsing datetime - Start: '{row.get('start')}' -> {start_time}")
                        print(f"Parsing datetime - End: '{row.get('end')}' -> {end_time}")
                        
                        if not start_time or not end_time:
                            print(f"Warning: Invalid datetime for sequence {seq}. Start: {start_time}, End: {end_time}")
                            continue

                        # Get objects with error handling
                        workstation_name = row.get("workstation", "")
                        workstation = WorkStations.objects.filter(name=workstation_name).first()
                        if not workstation:
                            print(f"Warning: Workstation '{workstation_name}' not found")
                            continue

                        machine_name = row.get("machine", "")
                        machine = Machine.objects.filter(name=machine_name).first()
                        if not machine:
                            print(f"Warning: Machine '{machine_name}' not found")
                            continue

                        shift_name = row.get("shift_name", "")
                        shift = Shift.objects.filter(shift_name=shift_name).first()
                        if not shift:
                            print(f"Warning: Shift '{shift_name}' not found")
                            continue

                        ShiftTable.objects.create(
                            machine_schedule=schedule,
                            machine_schedule_detail=detail,
                            sequence=seq,
                            production_order=get_object_or_404(ProductionOrder, id=production_order_id),
                            bom_component=get_object_or_404(BOMHeader, id=component_id),
                            workstation=workstation,
                            machine=machine.id,  # Store the ID, not the object
                            employees=employee_ids_str,
                            shift=shift,
                            start_time=start_time,
                            end_time=end_time,
                            total_quantity=row.get("total_quantity") or 0,
                            completed_quantity=row.get("completed_quantity") or 0,
                            remaining_quantity=row.get("remaining_quantity") or 0,
                            created_by=request.user,
                            week=week_display,
                        )

                    print(f"Successfully created {len(shift_table_data)} shift table entries")

                return redirect(reverse("mcp:machine_scheduling_list"))

        except Exception as e:
            transaction.set_rollback(True)
            schedule = get_object_or_404(MachineSchedule, pk=pk)
            assignments_data = self.get_assignments(schedule)
        
        return render(request, self.template_name, {
            "schedule": schedule,
            "production_orders": ProductionOrder.objects.all(),
            "components": BOMHeader.objects.all(),
            "assignments_json": json.dumps(assignments_data, default=str),
            "shift_table_json": json.dumps(self.get_shift_table(schedule), default=str),
            "error": f"Error while updating schedule: {str(e)}",
        })








    # def post(self, request, pk, *args, **kwargs):
    #     schedule = get_object_or_404(MachineSchedule, pk=pk)

    #     name = request.POST.get("name")
    #     scheduled_start = request.POST.get("scheduled_start")
    #     scheduled_end = request.POST.get("scheduled_end")
    #     assignments_json = request.POST.get("assignments_json", "[]")

    #     # Update schedule main fields
    #     schedule.name = name
    #     schedule.scheduled_start = scheduled_start
    #     schedule.scheduled_end = scheduled_end
    #     schedule.save()

    #     # Delete old MachineScheduleDetail rows
    #     schedule.details.all().delete()

    #     # Create new MachineScheduleDetail rows from assignments_json
    #     if assignments_json:
    #         assignments = json.loads(assignments_json)

    #         for row in assignments:
    #             routing_detail_id = row.get("routing_detail_id")
    #             workstation_id = row.get("workstation_id")

    #             if not routing_detail_id or not workstation_id:
    #                 continue

    #             routing_detail = get_object_or_404(RoutingDetail, id=routing_detail_id)
    #             machine = get_object_or_404(WorkStations, id=workstation_id).machine

    #             MachineScheduleDetail.objects.create(
    #                 schedule=schedule,
    #                 routing=routing_detail.routing,
    #                 machine=machine,
    #                 seq=routing_detail.sequence,
    #                 workstation_id=workstation_id,
    #                 work_center=routing_detail.work_center,
    #             )

    #         # Update schedule.routing to last routing used
    #         schedule.routing = routing_detail.routing
    #         schedule.save()

    #     return redirect(reverse("mcp:machine_scheduling_list"))



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
        return WorkStations.objects.select_related('created_by', 'updated_by')

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
    
# def get_routing_data(request):

#     component_id = request.POST.get("component_id")

#     try:
#         routing = RoutingMaster.objects.filter(component=component_id).first()
#         if not routing:
#             return JsonResponse({"schedules": [], "routing_id": None})

#         routing_id = routing.id
#         routing_details = RoutingDetail.objects.filter(routing=routing)
#         routing_detail_ids = routing_details.values_list("id", flat=True)

#         machine_schedules = MachineSchedule.objects.filter(component_id=component_id)
#         # if not machine_schedules.exists():
#         #     return JsonResponse({"schedules": [], "routing_id": routing_id})

#         schedule_ids = machine_schedules.values_list("id", flat=True)

#         shift_rows = (
#             ShiftTable.objects
#             .select_related("machine_schedule", "machine_schedule__production_order")
#             .filter(machine_schedule_id__in=schedule_ids)
#         )

#         data = []
#         for shift in shift_rows:
#             production_order = getattr(
#                 shift.machine_schedule.production_order, "order_number", None
#             ) or str(shift.machine_schedule.production_order_id)

#             data.append({
#                 "start_date": shift.start_time.strftime("%Y-%m-%dT%H:%M:%S") if shift.start_time else None,
#                 "end_date": shift.end_time.strftime("%Y-%m-%dT%H:%M:%S") if shift.end_time else None,
#                 "production_order": production_order,
#                 "shift_name": str(shift.shift) if shift.shift else None,
#             })

#         # ✅ Step 6: Return holiday list with description
#         current_year = date.today().year
#         holidays = list(
#             Holiday.objects.filter(date__year=current_year)
#             .values("date", "description")
#         )

#         # ✅ Step 7: Weekly off
#         weekly_off_row = WeeklyOff.objects.first()
#         weekly_off_day = getattr(weekly_off_row, "day") if weekly_off_row else None

#         return JsonResponse({
#             "schedules": data,
#             "routing_id": routing_id,
#             "holidays": holidays,
#             "weekly_off": weekly_off_day
#         })

#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)

def get_routing_data(request):
    component_id = request.POST.get("component_id")

    try:
        routing = RoutingMaster.objects.filter(component=component_id).first()
        if not routing:
            return JsonResponse({"schedules": [], "routing_id": None})

        routing_id = routing.id
        routing_details = RoutingDetail.objects.filter(routing=routing)
        routing_detail_ids = routing_details.values_list("id", flat=True)

        machine_schedules = MachineSchedule.objects.filter(component_id=component_id)
        schedule_ids = machine_schedules.values_list("id", flat=True)

        shift_rows = (
            ShiftTable.objects
            .select_related(
                "machine_schedule", 
                "machine_schedule__production_order",
                "shift"  # Added to get shift details
            )
            .filter(machine_schedule_id__in=schedule_ids)
        )

        # Get all shifts from ShiftMaster to know the order
        all_shifts = Shift.objects.all().order_by('shift_code')
        shift_order = {shift.id: shift.shift_code for shift in all_shifts}
        shift_colors = {
            "Shift1": "#28a745",  # Green
            "Shift2": "#ffc107",  # Yellow
            "Shift3": "#dc3545",  # Red
            "Default": "#4099ff"  # Blue
        }

        # Group shifts by date and shift code
        shifts_by_date = {}
        for shift in shift_rows:
            shift_date = shift.start_time.date() if shift.start_time else None
            if not shift_date:
                continue
                
            shift_code = shift_order.get(shift.id, "Default")
            
            if shift_date not in shifts_by_date:
                shifts_by_date[shift_date] = {}
            
            if shift_code not in shifts_by_date[shift_date]:
                shifts_by_date[shift_date][shift_code] = []
                
            production_order = getattr(
                shift.machine_schedule.production_order, "order_number", None
            ) or str(shift.machine_schedule.production_order)
            
            shifts_by_date[shift_date][shift_code].append({
                "start_time": shift.start_time,
                "end_time": shift.end_time,
                "production_order": production_order,
                "shift_id": shift.id,
                "shift_code": shift_code,
                "employee": getattr(shift, 'employee', None),
                "quantity": getattr(shift, 'quantity', None),
                "machine": getattr(shift.machine_schedule, 'machine', None),
            })

        # Prepare data for frontend
        data = []
        for date_str, shifts in shifts_by_date.items():
            date_data = {
                "date": date_str.isoformat(),
                "shifts": {}
            }
            
            for shift_code, shift_details in shifts.items():
                date_data["shifts"][shift_code] = shift_details
                
            data.append(date_data)

        # ✅ Step 6: Return holiday list with description
        current_year = date.today().year
        holidays = list(
            Holiday.objects.filter(date__year=current_year)
            .values("date", "description")
        )

        # ✅ Step 7: Weekly off
        weekly_off_row = WeeklyOff.objects.first()
        weekly_off_day = getattr(weekly_off_row, "day") if weekly_off_row else None

        return JsonResponse({
            "schedules": data,
            "routing_id": routing_id,
            "holidays": holidays,
            "weekly_off": weekly_off_day,
            "shift_colors": shift_colors,
            "all_shifts": list(all_shifts.values('id', 'shift_code', 'shift_name'))
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
    try:
        if request.method != "POST":
            return JsonResponse({"error": "Invalid request method"}, status=400)

        production_id = request.POST.get("production_id")
        scheduled_start = request.POST.get("scheduled_start")
        routing_data = json.loads(request.POST.get("routing_data", "[]"))

        if not production_id or not routing_data or not scheduled_start:
            return JsonResponse({"error": "Missing required fields"}, status=400)

        # --- 1️⃣ Get Production Order Quantity ---
        try:
            po = ProductionOrder.objects.get(id=production_id)
            total_qty = po.quantity
        except ProductionOrder.DoesNotExist:
            return JsonResponse({"error": "Invalid production ID"}, status=400)

        # --- 2️⃣ Get Active Shifts ---
        active_shifts = Shift.objects.filter(is_active=1).order_by('start_time')
        if not active_shifts.exists():
            return JsonResponse({"error": "No active shifts found"}, status=400)

        shifts_list = []
        for s in active_shifts:
            start = datetime.combine(datetime.today(), s.start_time)
            end = datetime.combine(datetime.today(), s.end_time)
            if end <= start:
                end += timedelta(days=1)
            shift_hours = (end - start).total_seconds() / 3600
            if s.break_time_period:
                shift_hours -= s.break_time_period.hour + s.break_time_period.minute / 60
            shifts_list.append({
                "id": s.id,
                "name": s.shift_name,
                "start": s.start_time,
                "end": s.end_time,
                "hours": max(0, shift_hours)
            })

        # --- 3️⃣ Prepare Holiday and Weekflow Data ---
        holiday_dates = set(Holiday.objects.values_list("date", flat=True))
        week_off_days = set(
            WeeklyOff.objects.filter(is_active=True).values_list("day", flat=True)
        )  # e.g., {'Sunday', 'Saturday'}

        def is_non_working_day(date_to_check):
            """Return True if date is a holiday or weekly off."""
            if date_to_check.date() in holiday_dates:
                return True
            if date_to_check.strftime("%A") in week_off_days:
                return True
            return False

        # --- 4️⃣ Start Date ---
        current_dt = datetime.strptime(scheduled_start, "%Y-%m-%dT%H:%M")

        # --- 5️⃣ Production Planning ---
        production_plan = []

        for routing in sorted(routing_data, key=lambda x: int(x.get("sequence", 0))):
            routing_detail_id = routing.get("routing_detail_id")
            sequence = routing.get("sequence")
            ws_id = routing.get("workstation_id")
            machine_id = routing.get("machine_id")
            employee_ids = routing.get("employee_ids", [])

            employee_names = []
            if employee_ids:
                employees = Employee.objects.filter(id__in=employee_ids).values_list("employee_name", flat=True)
                employee_names = list(employees)

            if not ws_id or not machine_id or not employee_ids:
                continue

            try:
                ws = WorkStations.objects.get(id=ws_id)
                machine = Machine.objects.get(id=machine_id)
            except:
                continue

            machine_capacity = get_numeric_capacity(machine.capacity)
            if machine_capacity <= 0:
                continue

            qty_remaining = total_qty

            # --- 6️⃣ Process Sequences with Non-Working Day Skip ---
            while qty_remaining > 0:
                # Skip to next valid working day if current day is holiday or week off
                while is_non_working_day(current_dt):
                    current_dt += timedelta(days=1)
                    current_dt = datetime.combine(current_dt.date(), shifts_list[0]["start"])

                for shift in shifts_list:
                    shift_start = current_dt.replace(hour=shift["start"].hour, minute=shift["start"].minute)
                    shift_end = current_dt.replace(hour=shift["end"].hour, minute=shift["end"].minute)
                    if shift_end <= shift_start:
                        shift_end += timedelta(days=1)

                    # Skip shifts if they fall on a non-working day
                    if is_non_working_day(shift_start):
                        continue

                    if current_dt < shift_start:
                        current_dt = shift_start

                    available_hours = (shift_end - current_dt).total_seconds() / 3600
                    if available_hours <= 0:
                        continue

                    qty_this_shift = min(qty_remaining, available_hours * machine_capacity)
                    hours_needed = qty_this_shift / machine_capacity

                    shift_plan_entry = {
                        "routing_detail_id": routing_detail_id,
                        "sequence": sequence,
                        "workstation": ws.name,
                        "machine": machine.name,
                        "employee_ids": employee_names,
                        "shift_id": shift["id"],
                        "shift_name": shift["name"],
                        "start": current_dt.strftime("%Y-%m-%dT%H:%M"),
                        "end": (current_dt + timedelta(hours=hours_needed)).strftime("%Y-%m-%dT%H:%M"),
                        "quantity_processed": round(qty_this_shift, 2),
                        "machine_capacity": machine_capacity
                    }

                    production_plan.append(shift_plan_entry)

                    qty_remaining -= qty_this_shift
                    current_dt += timedelta(hours=hours_needed)

                    if qty_remaining <= 0:
                        break

                # If still remaining, move to next working day
                if qty_remaining > 0:
                    current_dt += timedelta(days=1)
                    while is_non_working_day(current_dt):
                        current_dt += timedelta(days=1)
                    current_dt = datetime.combine(current_dt.date(), shifts_list[0]["start"])

        return JsonResponse({
            "success": True,
            "production_plan": production_plan,
            "total_quantity": total_qty,
            "estimated_end_date": current_dt.strftime("%Y-%m-%dT%H:%M")
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
   

def relocate_shift(request):
    try:
        if request.method != "POST":
            return JsonResponse({"error": "Invalid request method"}, status=400)

        removed_row_id = request.POST.get("removed_row_id")
        shift_table_data = json.loads(request.POST.get("shift_table_data", "[]"))
        production_id = request.POST.get("production_id")

        if not removed_row_id or not shift_table_data or not production_id:
            return JsonResponse({"error": "Missing required data"}, status=400)

        # Get production quantity
        try:
            po = ProductionOrder.objects.get(id=production_id)
            total_qty = po.quantity
        except ProductionOrder.DoesNotExist:
            return JsonResponse({"error": "Invalid production ID"}, status=400)

        # Get active shifts
        active_shifts = Shift.objects.filter(is_active=1).order_by('start_time')
        if not active_shifts.exists():
            return JsonResponse({"error": "No active shifts found"}, status=400)

        # Prepare shifts list with proper ordering
        shifts_list = []
        for s in active_shifts:
            start = datetime.combine(datetime.today(), s.start_time)
            end = datetime.combine(datetime.today(), s.end_time)
            if end <= start:
                end += timedelta(days=1)
            shift_hours = (end - start).total_seconds() / 3600
            if s.break_time_period:
                shift_hours -= s.break_time_period.hour + s.break_time_period.minute / 60
            shifts_list.append({
                "id": s.id,
                "name": s.shift_name,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "hours": max(0, shift_hours)
            })

        # Separate rows: before removed, removed, and after removed
        rows_before = []
        removed_row = None
        rows_after = []
        
        for row in shift_table_data:
            if str(row['row_id']) == str(removed_row_id):
                removed_row = row
            elif not removed_row:
                rows_before.append(row)
            else:
                rows_after.append(row)

        if not removed_row:
            return JsonResponse({"error": "Removed row not found"}, status=400)

        # Calculate the work quantity from removed row
        try:
            # Parse the date format from frontend (dd-mm-yyyy HH:MM)
            removed_start = datetime.strptime(removed_row['start'], "%d-%m-%Y %H:%M")
            removed_end = datetime.strptime(removed_row['end'], "%d-%m-%Y %H:%M")
            removed_duration_hours = (removed_end - removed_start).total_seconds() / 3600
            
            # Get machine capacity for the removed row
            try:
                machine = Machine.objects.get(name=removed_row['machine_name'])
                machine_capacity = get_numeric_capacity(machine.capacity)
                removed_quantity = removed_duration_hours * machine_capacity
            except Machine.DoesNotExist:
                removed_quantity = removed_row.get('completed_quantity', 0)
                
        except (ValueError, KeyError):
            removed_quantity = removed_row.get('completed_quantity', 0)

        # Find where to insert the relocated work - after the last row before removed row
        relocation_start_time = None
        if rows_before:
            # Start after the last row in 'before' section
            last_before_row = rows_before[-1]
            try:
                relocation_start_time = datetime.strptime(last_before_row['end'], "%d-%m-%Y %H:%M")
            except (ValueError, KeyError):
                # If no end time, use the removed row's start time
                relocation_start_time = datetime.strptime(removed_row['start'], "%d-%m-%Y %H:%M")
        else:
            # If no rows before, use removed row's start time
            relocation_start_time = datetime.strptime(removed_row['start'], "%d-%m-%Y %H:%M")

        current_dt = relocation_start_time
        relocated_rows = []

        # Relocate the removed work
        qty_remaining = removed_quantity
        sequence = removed_row['sequence']
        
        try:
            machine = Machine.objects.get(name=removed_row['machine_name'])
            machine_capacity = get_numeric_capacity(machine.capacity)
        except Machine.DoesNotExist:
            machine_capacity = 1

        workstation_name = removed_row.get('workstation_name', '')
        employee_names = removed_row.get('employee_names', [])

        # Function to find the next available shift
        def find_next_available_shift(start_dt):
            current_date = start_dt.date()
            max_days_check = 30  # Prevent infinite loop
            
            for day in range(max_days_check):
                for shift in shifts_list:
                    shift_start = datetime.combine(current_date, shift["start_time"])
                    shift_end = datetime.combine(current_date, shift["end_time"])
                    if shift_end <= shift_start:
                        shift_end += timedelta(days=1)
                    
                    # Check if this shift is after our start datetime
                    if shift_start >= start_dt:
                        return shift_start, shift, current_date
                
                # Move to next day
                current_date += timedelta(days=1)
            
            return start_dt, shifts_list[0], current_date

        # Distribute the removed quantity across shifts
        while qty_remaining > 0:
            shift_start_dt, current_shift, current_date = find_next_available_shift(current_dt)
            current_dt = shift_start_dt
            
            shift_end_dt = datetime.combine(current_date, current_shift["end_time"])
            if shift_end_dt <= shift_start_dt:
                shift_end_dt += timedelta(days=1)

            # Calculate available hours in this shift
            available_hours = (shift_end_dt - current_dt).total_seconds() / 3600
            if available_hours <= 0:
                current_dt = shift_end_dt
                continue

            # Calculate how much we can process in available time
            qty_this_shift = min(qty_remaining, available_hours * machine_capacity)
            hours_needed = qty_this_shift / machine_capacity

            # Create new plan entry for relocated work
            new_entry = {
                "routing_detail_id": removed_row.get('routing_detail_id'),
                "sequence": sequence,
                "workstation": workstation_name,
                "machine": removed_row['machine_name'],
                "employee_ids": employee_names,
                "shift_id": current_shift["id"],
                "shift_name": current_shift["name"],
                "start": current_dt.strftime("%Y-%m-%dT%H:%M"),
                "end": (current_dt + timedelta(hours=hours_needed)).strftime("%Y-%m-%dT%H:%M"),
                "quantity_processed": round(qty_this_shift, 2),
                "machine_capacity": machine_capacity
            }

            relocated_rows.append(new_entry)
            qty_remaining -= qty_this_shift
            current_dt += timedelta(hours=hours_needed)

        # Now build the final production plan in the correct order
        production_plan = []
        
        # 1. Add all rows before the removed row (unchanged)
        for row in rows_before:
            try:
                production_plan.append({
                    "routing_detail_id": row.get('routing_detail_id'),
                    "sequence": row.get('sequence'),
                    "workstation": row.get('workstation_name'),
                    "machine": row.get('machine_name'),
                    "employee_ids": row.get('employee_names', []),
                    "shift_id": None,
                    "shift_name": row.get('shift_name'),
                    "start": datetime.strptime(row['start'], "%d-%m-%Y %H:%M").strftime("%Y-%m-%dT%H:%M"),
                    "end": datetime.strptime(row['end'], "%d-%m-%Y %H:%M").strftime("%Y-%m-%dT%H:%M"),
                    "quantity_processed": row.get('completed_quantity', 0),
                    "machine_capacity": machine_capacity
                })
            except (ValueError, KeyError):
                continue

        # 2. Add relocated rows (the removed row's work redistributed)
        production_plan.extend(relocated_rows)

        # 3. Add all rows after the removed row (unchanged)
        for row in rows_after:
            try:
                production_plan.append({
                    "routing_detail_id": row.get('routing_detail_id'),
                    "sequence": row.get('sequence'),
                    "workstation": row.get('workstation_name'),
                    "machine": row.get('machine_name'),
                    "employee_ids": row.get('employee_names', []),
                    "shift_id": None,
                    "shift_name": row.get('shift_name'),
                    "start": datetime.strptime(row['start'], "%d-%m-%Y %H:%M").strftime("%Y-%m-%dT%H:%M"),
                    "end": datetime.strptime(row['end'], "%d-%m-%Y %H:%M").strftime("%Y-%m-%dT%H:%M"),
                    "quantity_processed": row.get('completed_quantity', 0),
                    "machine_capacity": machine_capacity
                })
            except (ValueError, KeyError):
                continue

        # Calculate the final end date (use the end time of the last row)
        final_end_date = current_dt
        if production_plan:
            try:
                last_row_end = datetime.strptime(production_plan[-1]['end'], "%Y-%m-%dT%H:%M")
                final_end_date = max(final_end_date, last_row_end)
            except (ValueError, KeyError):
                pass

        # Update row IDs for the frontend
        for i, plan in enumerate(production_plan):
            plan['row_id'] = i

        return JsonResponse({
            "success": True,
            "production_plan": production_plan,
            "total_quantity": total_qty,
            "estimated_end_date": final_end_date.strftime("%Y-%m-%dT%H:%M")
        })

    except Exception as e:
        import traceback
        return JsonResponse({"success": False, "error": str(e) + traceback.format_exc()}, status=500)








    


def get_workstation_details(request):
    workstation_id = request.GET.get("workstation_id")
    try:
        if not workstation_id:
            return JsonResponse({"error": "Missing workstation_id"}, status=400)

        ws = WorkStations.objects.get(id=workstation_id)

        # 🔹 Machines
        machines = []
        if ws.machine:
            machine_ids = [int(m.strip()) for m in ws.machine.split(",") if m.strip().isdigit()]
            for m in Machine.objects.filter(id__in=machine_ids):
                machines.append({
                    "id": m.id,
                    "name": m.name,
                    "capacity": m.capacity  # assuming you have a capacity field
                })

        # 🔹 Employees
        employees = []
        if ws.employee:
            emp_ids = [int(e.strip()) for e in ws.employee.split(",") if e.strip().isdigit()]
            for emp in Employee.objects.filter(id__in=emp_ids):
                # Get employee skill & proficiency
                emp_skill_objs = EmployeeSkill.objects.filter(employee=emp)
                skill_info = []
                for es in emp_skill_objs:
                    skill_name = getattr(es.skill, "skill_name")
                    prof_name = getattr(es.proficiency, "name") 
                    skill_info.append(f"{skill_name} ({prof_name})")

                employees.append({
                    "id": emp.id,
                    "name": emp.employee_name,
                    "skill": ", ".join(skill_info) if skill_info else "",
                })

        return JsonResponse({
            "machines": machines,
            "employees": employees
        })

    except WorkStations.DoesNotExist:
        return JsonResponse({"error": "Workstation not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def production_planning_with_batch(request):
    try:
        # with transaction.atomic():
            # Get production order and component
            production_order = get_object_or_404(ProductionOrder, order_number=request.GET.get('po_order'))
            component = get_object_or_404(BOMHeader, name=request.GET.get('bom_header'))
            
            # Get machine schedule for this combination
            machine_schedule = MachineSchedule.objects.filter(
                production_order=production_order,
                component=component
            ).first()
            
            if not machine_schedule:
                return JsonResponse({'error': 'No machine schedule found for this combination'}, status=404)
            
            # Check if batch already exists
            existing_batch = BatchMaster.objects.filter(
                production_order=production_order,
                bom_component=component,
                machine_schedule=machine_schedule
            ).first()
            
            # Create BatchMaster record if not exists
            if not existing_batch:
                # Generate batch number
                batch_no = f"BATCH-{production_order.order_number}-{component.name}-{production_order.quantity}-{datetime.now().strftime('%Y%m%d%H%M')}"
                
                batch = BatchMaster.objects.create(
                    batch_no=batch_no,
                    production_order=production_order,
                    bom_component=component,
                    machine_schedule=machine_schedule,
                    quanity=production_order.quantity,
                    production_date=machine_schedule.scheduled_start,
                    status='PLANNED',
                    created_by=request.user if request.user.is_authenticated else None
                )
            else:
                batch = existing_batch
            
            # Get machine schedule details
            machine_schedule_details = MachineScheduleDetail.objects.filter(
                schedule=machine_schedule
            ).select_related('schedule', 'routing', 'machine')

            for detail in machine_schedule_details:
                if detail.employee:
                    emp_ids = [int(emp_id.strip()) for emp_id in detail.employee.split(',') if emp_id.strip()]
                    employees = Employee.objects.filter(id__in=emp_ids).values_list('employee_name', flat=True)  # use correct field name
                    detail.employee = ", ".join(employees)
                else:
                    detail.employee = "—"
            
            # Get shift data for this machine schedule
            shifts = ShiftTable.objects.filter(
                machine_schedule_detail__schedule=machine_schedule
            ).distinct().select_related('machine_schedule_detail', 'shift')

            for shift in shifts:
                if shift.employees:
                    try:
                        emp_ids = [
                            int(emp_id.strip())
                            for emp_id in shift.employees.split(',')
                            if emp_id.strip().isdigit()
                        ]
                        employees = Employee.objects.filter(id__in=emp_ids).values_list('employee_name', flat=True)
                        shift.employee_names = ", ".join(employees) if employees else "—"
                    except Exception as e:
                        shift.employee_names = f"Error: {str(e)}"
                else:
                    shift.employee_names = "—"

            
            # Get all batches for this production order (for the table)
            all_batches = BatchMaster.objects.filter(production_order=production_order).select_related(
                'production_order', 'bom_component', 'machine_schedule', 'created_by'
            )
            
            context = {
                'production_order': production_order,
                'component': component,
                'batch': batch,
                'machine_schedule': machine_schedule,
                'machine_schedule_details': machine_schedule_details,
                'shifts': shifts,
                'all_batches': all_batches,
            }
            
            return render(request, 'MachinePlan/production_planning.html', context)
    
    except Exception as e:
        # Rollback happens automatically because of @transaction.atomic
        # transaction.set_rollback(True)
        return JsonResponse({'error': str(e)}, status=500)
    

def confirm_production_plan(request,batch_id, production_order_id, component_id):
    if request.method == 'POST':
        try:
            # Get the production order and component
            production_order = get_object_or_404(ProductionOrder, id=production_order_id).id
            component = get_object_or_404(Component, id=component_id)

            batches = get_object_or_404(BatchMaster, id = batch_id)
            batches.status = 'IN_PROGRESS'
            batches.save()
            
            
                
            production_order = get_object_or_404(ProductionOrder, id=production_order_id)
            production_order.order_status = get_object_or_404(StatusAction, id = 4)
            production_order.save()
                
            messages.success(request, f'Production plan confirmed! moved to In Progress.')
                
        except Exception as e:
            messages.error(request, f'Error confirming production plan: {str(e)}')
    
    # Redirect back to the production planning page
    return redirect('plm_index')




def create_batch_routing_log(request):
    try:
        # Get production order and component
        production_order = get_object_or_404(ProductionOrder, order_number =(request.GET.get('po_order')))
        component =  get_object_or_404(BOMHeader, name =(request.GET.get('bom_header')))
        
        # Get batch for this production order and component
        batch = get_object_or_404(BatchMaster, production_order=production_order, bom_component=component)
        
        # Get machine schedule
        machine_schedule = get_object_or_404(MachineSchedule, production_order=production_order)
        
        # Get all machine schedule details
        machine_schedule_details = MachineScheduleDetail.objects.filter(schedule=machine_schedule)
        
        created_logs = []
        
        # Check if routing logs already exist for this batch
        existing_logs = BatchRoutingLog.objects.filter(batch=batch)
        if existing_logs.exists():
            messages.info(request, f'Batch routing logs already exist for this batch. Showing existing {existing_logs.count()} entries.')
            batch_routing_logs = existing_logs.order_by('machine_schedule_detail__seq')
        else:
            # Create BatchRoutingLog entries for each machine schedule detail
            for detail in machine_schedule_details:
                # Get employee names as comma separated string
                employee_names = get_employee_names_from_ids(detail.employee)
                
                # Create BatchRoutingLog entry without start_time and end_time
                routing_log = BatchRoutingLog.objects.create(
                    batch=batch,
                    machine_schedule=machine_schedule,
                    machine_schedule_detail=detail,
                    start_time=None,  # Will be set by user in frontend
                    end_time=None,    # Will be set by user in frontend
                    machine_id=detail.machine,
                    employee=employee_names,
                    quantity_pass=0,  # Initial value, will be updated during production
                    quantity_reject=0, # Initial value, will be updated during production
                    created_by=request.user
                )
                created_logs.append(routing_log)
            
            messages.success(request, f'Successfully created {len(created_logs)} batch routing log entries!')
        
        # Get all routing logs for this batch to display
        batch_routing_logs = BatchRoutingLog.objects.filter(batch=batch).order_by('machine_schedule_detail__seq')
        
        # Calculate counts
        total_operations = batch_routing_logs.count()
        completed_operations = batch_routing_logs.filter(end_time__isnull=False).count()
        pending_operations = batch_routing_logs.filter(end_time__isnull=True).count()
        
        context = {
            'production_order': production_order,
            'component': component,
            'batch': batch,
            'batch_routing_logs': batch_routing_logs,
            'created_count': len(created_logs),
            'total_operations': total_operations,
            'completed_operations': completed_operations,
            'pending_operations': pending_operations,
        }
        
        return render(request, 'MachinePlan/production_plan_execution.html', context)
        
    except Exception as e:
        messages.error(request, f'Error creating batch routing log: {str(e)}')
        return redirect('MachinePlan/production_plan_exceution.html')

def get_employee_names_from_ids(employee_ids_str):
    """
    Convert comma separated employee IDs to comma separated employee names
    """
    if not employee_ids_str:
        return "Not Assigned"
    
    try:
        # Split the comma separated IDs
        employee_ids = [eid.strip() for eid in employee_ids_str.split(',') if eid.strip()]
        
        # Get employee objects
        employees = Employee.objects.filter(id__in=employee_ids)
        
        # Extract names
        employee_names = [f"{emp.employee_name}".strip() for emp in employees]
        
        return ", ".join(employee_names) if employee_names else "Not Assigned"
        
    except Exception as e:
        # Fallback: return the original IDs if there's any error
        return employee_ids_str
    
def complete_batch_process(request, batch_id):
    if request.method == 'POST':
        try:
            batch = get_object_or_404(BatchMaster, id=batch_id)
            
            # Update batch status to COMPLETED
            batch.status = 'COMPLETED'
            batch.save()
            
            # Update all routing logs with end time
            BatchRoutingLog.objects.filter(batch=batch).update(
                end_time=timezone.now(),
                updated_by=request.user
            )
            
            messages.success(request, f'Batch {batch.batch_no} process completed successfully!')
            return redirect('mcp:batch_routing_log_view', production_order_id=batch.production_order.id, component_id=batch.bom_component.id)
            
        except Exception as e:
            messages.error(request, f'Error completing batch process: {str(e)}')
    
    return redirect('plm_index')

def update_batch_routing_log(request):
    try:
        log_id = request.POST.get("log_id")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")
        quantity_pass = request.POST.get("quantity_pass")
        quantity_reject = request.POST.get("quantity_reject")

        log = get_object_or_404(BatchRoutingLog, id=log_id)

        # Update fields
        if start_time:
            log.start_time = start_time
        if end_time:
            log.end_time = end_time
        if quantity_pass:
            log.quantity_pass = quantity_pass
        if quantity_reject:
            log.quantity_reject = quantity_reject

        log.save()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
    

def mps_complete_redirect(request, production_order_id, component_id):
    """
    Redirect to machine scheduling update view for the given production order and component
    """
    try:
        # Get the production order and component
        production_order = get_object_or_404(ProductionOrder, id=production_order_id)
        component = get_object_or_404(BOMHeader, id=component_id)
        
        # Get the MachineSchedule object for this combination
        machine_schedule = get_object_or_404(
            MachineSchedule, 
            production_order=production_order,
            component=component
        )
        
        # Redirect to the machine scheduling update view
        return redirect('mcp:machine_scheduling_update', pk=machine_schedule.id)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
    
def mps_complete_redirect(request, production_order_id, component_id):
    """
    Redirect to machine scheduling update view for the given production order and component
    """
    try:
        # Get the production order and component
        production_order = get_object_or_404(ProductionOrder, id=production_order_id)
        component = get_object_or_404(BOMHeader, id=component_id)
        
        # Get the MachineSchedule object for this combination
        material = get_object_or_404(
            MaterialPlan, 
            production_order=production_order,
            bom=component
        )
        
        # Redirect to the machine scheduling update view
        return redirect('plan_detail', pk=material.id)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
     
def production_plan_complete_redirect(request, production_order_id, component_id):
    """
    Redirect to machine scheduling update view for the given production order and component
    """
    try:
        # Get the production order and component
        po_order = get_object_or_404(ProductionOrder, id=production_order_id).order_number
        bom_header = get_object_or_404(BOMHeader, id=component_id).name
        
        # Simple redirect with query parameters
        return redirect(f"{reverse('mcp:production_planning_with_batch')}?po_order={po_order}&bom_header={bom_header}")
        
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})