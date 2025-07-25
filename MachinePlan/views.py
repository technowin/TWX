# MachinePlan/views.py
from pyexpat.errors import messages
from django.http import JsonResponse
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


def machine_planning_list(request):
    plans = MachinePlanning.objects.all().select_related(
        'production_order', 'component', 'operation', 'machine'
    ).order_by('scheduled_start')
    
    # AJAX request handling
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = {
            'html': render_to_string('MachinePlan/partials/planning_table.html', {'plans': plans}, request=request)
        }
        return JsonResponse(data)
    
    return render(request, 'MachinePlan/machine_planning_list.html', {'plans': plans})

def machine_planning_create(request):
    if request.method == 'POST':
        form = MachinePlanningForm(request.POST)
        if form.is_valid():
            plan = form.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Machine Schedule created successfully!'
                })
            return redirect(reverse('machine_planning_list'))
        
        # Form is invalid
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors,
                'form_html': render_to_string(
                    'MachinePlan/partials/planning_form.html', 
                    {'form': form}, 
                    request=request
                )
            }, status=400)
        return render(request, 'MachinePlan/machine_planning_list.html', {'form': form})
    
    # GET request
    form = MachinePlanningForm()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'form_html': render_to_string(
                'MachinePlan/partials/planning_form.html', 
                {'form': form}, 
                request=request
            )
        })
    
    return render(request, 'MachinePlan/machine_planning_list.html', {'form': form})

def machine_planning_edit(request, pk):
    plan = get_object_or_404(MachinePlanning, pk=pk)
    
    if request.method == 'POST':
        form = MachinePlanningForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Machine Schedule updated successfully!'
                })
            return redirect(reverse('machine_planning_list'))
        
        # Form is invalid
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors,
                'form_html': render_to_string(
                    'MachinePlan/partials/planning_form.html', 
                    {'form': form, 'plan': plan}, 
                    request=request
                )
            }, status=400)
        return render(request, 'MachinePlan/machine_planning_list.html', {'form': form, 'plan': plan})
    
    # GET request
    form = MachinePlanningForm(instance=plan)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'form_html': render_to_string(
                'MachinePlan/partials/planning_form.html', 
                {'form': form, 'plan': plan}, 
                request=request
            )
        })
    
    return render(request, 'MachinePlan/machine_planning_list.html', {'form': form, 'plan': plan})

def machine_planning_delete(request, pk):
    plan = get_object_or_404(MachinePlanning, pk=pk)
    
    if request.method == 'POST':
        plan.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Machine Schedule deleted successfully!'
            })
        return redirect(reverse('machine_planning_list'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'confirm_html': render_to_string(
                'MachinePlan/partials/delete_confirm.html', 
                {'item': plan, 'type': 'Machine Schedule'}, 
                request=request
            )
        })
    
    return render(request, 'MachinePlan/machine_planning_list.html', {'plan': plan})


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
    template_name = 'MachinePlan/operation_confirm_delete.html'
    success_url = reverse_lazy('mcp:operation_list')


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

class WorkCenterUpdateView(UpdateView):
    model = WorkCenter
    form_class = WorkCenterForm
    template_name = 'MachinePlan/workcenter_form.html'
    success_url = reverse_lazy('mcp:workcenter_list')

class WorkCenterDeleteView(DeleteView):
    model = WorkCenter
    template_name = 'MachinePlan/workcenter_confirm_delete.html'
    success_url = reverse_lazy('mcp:workcenter_list')