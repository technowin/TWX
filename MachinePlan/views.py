# MachinePlan/views.py
from datetime import timedelta
from itertools import count
import json
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin

from BOM.models import Component
from .models import Machine, MachineType, MachineCapability, MachineSchedule, MaintenanceSchedule
from  .forms import *
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q
from django.utils import timezone
from django.template.loader import render_to_string

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

# class MachineTypeDeleteView( DeleteView):
#     model = MachineType
#     template_name = 'MachinePlan/machine_type_confirm_delete.html'
#     success_url = reverse_lazy('mcp:machine_type_list')

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
        context['schedules'] = self.object.schedules.filter(
            start_time__gte=timezone.now()
        ).order_by('start_time')[:10]
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

class MachineCapabilityCreateView( CreateView):
    model = MachineCapability
    form_class = MachineCapabilityForm
    template_name = 'MachinePlan/machine_capability_form.html'
    success_url = reverse_lazy('mcp:machine_capability_list')

class MachineCapabilityUpdateView( UpdateView):
    model = MachineCapability
    form_class = MachineCapabilityForm
    template_name = 'MachinePlan/machine_capability_form.html'
    success_url = reverse_lazy('mcp:machine_capability_list')

class MachineCapabilityDeleteView(DeleteView):
    model = MachineCapability
    template_name = 'MachinePlan/machine_capability_confirm_delete.html'
    success_url = reverse_lazy('mcp:machine_capability_list')

class MachineScheduleListView(ListView):
    model = MachineSchedule
    template_name = 'MachinePlan/machine_schedule_list.html'
    context_object_name = 'schedules'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        status = self.request.GET.get('status')
        machine_id = self.request.GET.get('machine')
        
        if date_from:
            queryset = queryset.filter(start_time__gte=date_from)
        if date_to:
            queryset = queryset.filter(end_time__lte=date_to)
        if status:
            queryset = queryset.filter(status=status)
        if machine_id:
            queryset = queryset.filter(machine_id=machine_id)
            
        return queryset.select_related('machine', 'component').order_by('start_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['machines'] = Machine.objects.filter(status='OP')
        context['status_choices'] = MachineSchedule.STATUS_CHOICES
        return context

class MachineScheduleCreateView( CreateView):
    model = MachineSchedule
    form_class = MachineScheduleForm
    template_name = 'MachinePlan/machine_schedule_form.html'
    success_url = reverse_lazy('mcp:machine_schedule_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

class MachineScheduleUpdateView( UpdateView):
    model = MachineSchedule
    form_class = MachineScheduleForm
    template_name = 'MachinePlan/machine_schedule_form.html'
    success_url = reverse_lazy('mcp:machine_schedule_list')

class MachineScheduleDeleteView( DeleteView):
    model = MachineSchedule
    template_name = 'MachinePlan/machine_schedule_confirm_delete.html'
    success_url = reverse_lazy('mcp:machine_schedule_list')

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

class MachineCalendarView( ListView):
    model = MachineSchedule
    template_name = 'MachinePlan/machine_calendar.html'
    context_object_name = 'schedules'

    def get_queryset(self):
        date_from = self.request.GET.get('date_from', timezone.now().date())
        date_to = self.request.GET.get('date_to', timezone.now().date() + timezone.timedelta(days=7))
        
        return MachineSchedule.objects.filter(
            start_time__date__gte=date_from,
            end_time__date__lte=date_to
        ).select_related('machine', 'component').order_by('start_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['machines'] = Machine.objects.filter(status='OP')
        return context
    

class RoutingListView(ListView):
    model = Routing
    template_name = 'MachinePlan/routing_list.html'
    context_object_name = 'routings'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related('component', 'operation', 'work_center')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add dropdown options for the modal forms
        context['components'] = BOMHeader.objects.all()
        context['operations'] = Operation.objects.all()
        context['work_centers'] = WorkCenter.objects.all()
        return context

class RoutingCreateView(CreateView):
    model = Routing
    form_class = RoutingForm
    template_name = 'MachinePlan/routing_form.html'
    success_url = reverse_lazy('mcp:routing_list')

class RoutingUpdateView(UpdateView):
    model = Routing
    form_class = RoutingForm
    template_name = 'MachinePlan/routing_form.html'
    success_url = reverse_lazy('mcp:routing_list')

class RoutingDeleteView(DeleteView):
    model = Routing
    template_name = 'MachinePlan/routing_confirm_delete.html'
    success_url = reverse_lazy('mcp:routing_list')


class MachinePlanningListView(ListView):
    model = MachinePlanning
    template_name = 'MachinePlan/machine_planning_list.html'
    context_object_name = 'plans'
    
    def get_queryset(self):
        return super().get_queryset().select_related(
            'production_order', 'component', 'operation', 'machine'
        ).order_by('scheduled_start')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add the additional context needed for dropdowns
        context['production_orders'] = ProductionOrder.objects.all()
        context['components'] = BOMHeader.objects.all()
        context['operations'] = Operation.objects.all()
        context['machines'] = Machine.objects.all()
        status_field = MachinePlanning._meta.get_field('status')
        context['status_choices'] = status_field.choices  # Assuming STATUS_CHOICES is defined in your model
        return context

class MachinePlanningCreateView(CreateView):
    model = MachinePlanning
    form_class = MachinePlanningForm
    success_url = reverse_lazy('mcp:machine_planning_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        messages.success(self.request, "Schedule created successfully!")
        return response
    
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors})
        return super().form_invalid(form)

class MachinePlanningUpdateView(UpdateView):
    model = MachinePlanning
    form_class = MachinePlanningForm
    success_url = reverse_lazy('mcp:machine_planning_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        messages.success(self.request, "Schedule updated successfully!")
        return response
    
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors})
        return super().form_invalid(form)

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
    model = WorkCenter
    template_name = 'MachinePlan/workcenter_list.html'
    context_object_name = 'workcenters'
    paginate_by = 20

class WorkCenterCreateView(CreateView):
    model = WorkCenter
    form_class = WorkCenterForm
    template_name = 'MachinePlan/workcenter_form.html'
    success_url = reverse_lazy('mcp:workcenter_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Work Center created successfully!")
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

class WorkCenterUpdateView(UpdateView):
    model = WorkCenter
    form_class = WorkCenterForm
    template_name = 'MachinePlan/workcenter_form.html'
    success_url = reverse_lazy('mcp:workcenter_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Work Center updated successfully!")
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class WorkCenterDeleteView(DeleteView):
    model = WorkCenter
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
    production_schedules = MachineSchedule.objects.filter(
        start_time__gte=today_start,
        end_time__lte=today_end
    ).order_by('start_time')
    
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
    work_centers = WorkCenter.objects.all()
    work_center_names = [wc.name for wc in work_centers]
    work_center_available = [40, 40, 40, 40]  # Assuming 40 hours available per week
    work_center_scheduled = [32, 28, 35, 25]  # Scheduled hours
    
    context = {
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