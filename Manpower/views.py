# views.py
from datetime import date, timedelta
from io import BytesIO
import traceback
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Count, Sum, Case, When, IntegerField,F
from django.utils import timezone
import pandas as pd


from .models import (
    Employee, Skill, EmployeeSkill, Shift, LaborRequirement, 
    LaborAssignment, EmployeeAvailability, Attendance, LeaveRequest
)
from .forms import (
    EmployeeForm, SkillForm, EmployeeSkillForm, ShiftForm, 
    LaborRequirementForm, LaborAssignmentForm, EmployeeAvailabilityForm,
    AttendanceForm, LeaveRequestForm
)
from MachinePlan.models import MachinePlanning, MachineScheduling, Routing
    
class EmployeeListView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = 'Manpower/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Get filter parameters from request
        code_filter = self.request.GET.get('code')
        name_filter = self.request.GET.get('name')
        work_center_filter = self.request.GET.get('work_center')
        
        # Apply filters if they exist
        if code_filter:
            queryset = queryset.filter(employee_code=code_filter)
        if name_filter:
            queryset = queryset.filter(employee_name=name_filter)
        if work_center_filter:
            queryset = queryset.filter(work_center__name=work_center_filter)
            
        return queryset  # Removed the is_active filter
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        
        # Get unique values for dropdowns
        context['unique_codes'] = Employee.objects.all().order_by('employee_code').values_list('employee_code', flat=True).distinct()    
        context['unique_names'] = Employee.objects.all().order_by('employee_name').values_list('employee_name', flat=True).distinct()    
        context['unique_work_centers'] = Employee.objects.all().order_by('work_center__name').values_list('work_center__name', flat=True).distinct()
            
        return context

class EmployeeCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'Manpower/employee_form.html'
    
    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except AttributeError:
            return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.object:
            context['title'] = "Add New Employee"
        else:
            context['title'] = f"Edit Employee: {self.object.employee_name}"
        return context
    
    def form_valid(self, form):
        messages.success(self.request, "Employee saved successfully!")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('manpower:employee_list')

@login_required
def delete_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    employee.save()
    messages.success(request, f"Employee {employee.employee_name} has been deactivated.")
    return JsonResponse({'success': True})

class EmployeeDetailView(LoginRequiredMixin, DetailView):
    model = Employee
    template_name = 'Manpower/employee_detail.html'
    context_object_name = 'employee'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['skills'] = self.object.skills.all().select_related('skill')
        context['assignments'] = self.object.labor_assignments.all().select_related('schedule', 'shift')
        context['availabilities'] = self.object.availabilities.all().order_by('-date')[:10]
        context['attendances'] = self.object.attendances.all().order_by('-date')[:10]
        return context

# Similar views for other models (Skill, EmployeeSkill, Shift, etc.)
# Following the same pattern as Employee views

class SkillListView(LoginRequiredMixin, ListView):
    model = Skill
    template_name = 'Manpower/skill_list.html'
    context_object_name = 'skills'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Get filter parameters from request
        code_filter = self.request.GET.get('code')
        name_filter = self.request.GET.get('name')
        
        # Apply filters if they exist
        if code_filter:
            queryset = queryset.filter(skill_code__icontains=code_filter)
        if name_filter:
            queryset = queryset.filter(skill_name__icontains=name_filter)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get unique values for dropdowns
        context['unique_codes'] = Skill.objects.all()\
            .order_by('skill_code')\
            .values_list('skill_code', flat=True)\
            .distinct()
            
        context['unique_names'] = Skill.objects.all()\
            .order_by('skill_name')\
            .values_list('skill_name', flat=True)\
            .distinct()
            
        return context

class SkillCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = Skill
    form_class = SkillForm
    template_name = 'Manpower/skill_form.html'
    
    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except AttributeError:
            return None
    
    def get_success_url(self):
        return reverse_lazy('manpower:skill_list')

@require_POST
@login_required
def delete_skill(request, pk):
    skill = get_object_or_404(Skill, pk=pk)
    skill.delete()
    messages.success(request, f"Skill {skill.skill_name} has been deleted.")
    return JsonResponse({'success': True})

class ShiftListView(LoginRequiredMixin, ListView):
    model = Shift
    template_name = 'Manpower/shift_list.html'
    context_object_name = 'shifts'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Get filter parameters from request
        name_filter = self.request.GET.get('name')
        time_filter = self.request.GET.get('time')
        
        # Apply filters if they exist
        if name_filter:
            queryset = queryset.filter(shift_name__icontains=name_filter)
        if time_filter:
            if time_filter == 'morning':
                queryset = queryset.filter(start_time__hour__lt=12)
            elif time_filter == 'afternoon':
                queryset = queryset.filter(start_time__hour__gte=12, start_time__hour__lt=17)
            elif time_filter == 'evening':
                queryset = queryset.filter(start_time__hour__gte=17)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get unique values for dropdowns
        context['unique_names'] = Shift.objects.all()\
            .order_by('shift_name')\
            .values_list('shift_name', flat=True)\
            .distinct()
            
        return context

class ShiftCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = Shift
    form_class = ShiftForm
    template_name = 'Manpower/shift_form.html'
    
    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except AttributeError:
            return None
    
    def get_success_url(self):
        return reverse_lazy('manpower:shift_list')

@require_POST
@login_required
def delete_shift(request, pk):
    shift = get_object_or_404(Shift, pk=pk)
    shift.delete()
    messages.success(request, f"Shift {shift.shift_code} has been deleted.")
    return JsonResponse({'success': True})

class LaborRequirementListView(LoginRequiredMixin, ListView):
    model = LaborRequirement
    template_name = 'Manpower/labor_requirement_list.html'
    context_object_name = 'requirements'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('skill', 'routing')
        
        # Add filters if needed
        skill_id = self.request.GET.get('skill_id')
        routing_id = self.request.GET.get('routing_id')
        
        if skill_id:
            queryset = queryset.filter(skill_id=skill_id)
        if routing_id:
            queryset = queryset.filter(routing_id=routing_id)
            
        return queryset.order_by('skill__skill_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['skills'] = Skill.objects.all().order_by('skill_name')
        context['routings'] = Routing.objects.all().order_by('id')
        return context

class LaborRequirementCreateView(LoginRequiredMixin, CreateView):
    model = LaborRequirement
    form_class = LaborRequirementForm
    template_name = 'Manpower/labor_requirement_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Add New Labor Requirement"
        return context
    
    def get_success_url(self):
        return reverse_lazy('manpower:labor_requirement_list')

class LaborRequirementUpdateView(LoginRequiredMixin, UpdateView):
    model = LaborRequirement
    form_class = LaborRequirementForm
    template_name = 'Manpower/labor_requirement_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Edit Labor Requirement"
        return context
    
    def get_success_url(self):
        return reverse_lazy('manpower:labor_requirement_list')

@require_POST
@login_required
def delete_labor_requirement(request, pk):
    requirement = get_object_or_404(LaborRequirement, pk=pk)
    requirement.delete()
    messages.success(request, "Labor requirement has been deleted.")
    return JsonResponse({'success': True})
class LaborAssignmentListView(LoginRequiredMixin, ListView):
    model = LaborAssignment
    template_name = 'Manpower/labor_assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('employee', 'shift', 'schedule')
        
        # Get filter parameters
        employee_filter = self.request.GET.get('employee')
        date_filter = self.request.GET.get('date')
        status_filter = self.request.GET.get('status')
        schedule_id = self.request.GET.get('schedule_id')
        
        # Apply filters
        if employee_filter:
            queryset = queryset.filter(employee__employee_name__icontains=employee_filter)
        if date_filter:
            queryset = queryset.filter(date=date_filter)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if schedule_id:
            queryset = queryset.filter(schedule_id=schedule_id)
            
        return queryset.order_by('-date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get unique values for filters
        context['unique_employees'] = Employee.objects.order_by('employee_name').values_list('employee_name', flat=True).distinct()
            
        context['unique_dates'] = LaborAssignment.objects.all().order_by('-date').values_list('date', flat=True).distinct()
            
        context['status_choices'] = LaborAssignment._meta.get_field('status').choices
        
        # Add schedule context if exists
        schedule_id = self.request.GET.get('schedule_id')
        if schedule_id:
            context['schedule'] = get_object_or_404(MachineScheduling, pk=schedule_id)
            
        return context
class LaborAssignmentCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = LaborAssignment
    form_class = LaborAssignmentForm
    template_name = 'Manpower/labor_assignment_form.html'
    
    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except AttributeError:
            return None
    
    def get_success_url(self):
        return reverse_lazy('manpower:labor_assignment_list') + f"?schedule_id={self.object.schedule_id}"

@require_POST
@login_required
def delete_labor_assignment(request, pk):
    assignment = get_object_or_404(LaborAssignment, pk=pk)
    schedule_id = assignment.schedule_id
    assignment.delete()
    messages.success(request, "Labor assignment has been deleted.")
    return JsonResponse({'success': True, 'redirect_url': reverse_lazy('manpower:labor_assignment_list') + f"?schedule_id={schedule_id}"})

# Additional views for EmployeeAvailability, Attendance, LeaveRequest would follow similar patterns

class LeaveRequestListView(LoginRequiredMixin, ListView):
    model = LeaveRequest
    template_name = 'Manpower/leave_request_list.html'
    context_object_name = 'leave_requests'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('employee', 'approved_by')
        status = self.request.GET.get('status')
        leave_type = self.request.GET.get('leave_type')
        employee_id = self.request.GET.get('employee_id')
        
        if status:
            queryset = queryset.filter(status=status)
        if leave_type:
            queryset = queryset.filter(leave_type=leave_type)
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
            
        return queryset.order_by('-start_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employees'] = Employee.objects.all()
        context['status_choices'] = LeaveRequest.STATUS_CHOICES
        context['leave_types'] = LeaveRequest.LEAVE_TYPES
        return context

class LeaveRequestCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'Manpower/leave_request_form.html'
    
    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except AttributeError:
            return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.object:
            context['title'] = "Create Leave Request"
        else:
            context['title'] = f"Edit Leave Request for {self.object.employee.employee_name}"
        return context
    
    def form_valid(self, form):
        if not form.instance.pk and form.instance.status == 'pending':
            form.instance.employee = self.request.user.employee
        messages.success(self.request, "Leave request saved successfully!")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('manpower:leave_request_list')

@login_required
def delete_leave_request(request, pk):
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    leave_request.delete()
    messages.success(request, "Leave request has been deleted.")
    return JsonResponse({'success': True})

@login_required
def approve_leave_request(request, pk):
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    if leave_request.status == 'pending':
        leave_request.status = 'approved'
        leave_request.approved_by = request.user.employee
        leave_request.approval_date = timezone.now()
        leave_request.save()
        messages.success(request, "Leave request has been approved.")
    else:
        messages.warning(request, "Leave request is not in pending status.")
    return JsonResponse({'success': True})

@login_required
def reject_leave_request(request, pk):
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    if leave_request.status == 'pending':
        leave_request.status = 'rejected'
        leave_request.approved_by = request.user.employee
        leave_request.approval_date = timezone.now()
        leave_request.save()
        messages.success(request, "Leave request has been rejected.")
    else:
        messages.warning(request, "Leave request is not in pending status.")
    return JsonResponse({'success': True})

class LeaveRequestListView(LoginRequiredMixin, ListView):
    model = LeaveRequest
    template_name = 'Manpower/leave_request_list.html'
    context_object_name = 'leave_requests'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('employee', 'approved_by')
        status = self.request.GET.get('status')
        leave_type = self.request.GET.get('leave_type')
        employee_id = self.request.GET.get('employee_id')
        
        if status:
            queryset = queryset.filter(status=status)
        if leave_type:
            queryset = queryset.filter(leave_type=leave_type)
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
            
        return queryset.order_by('-start_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employees'] = Employee.objects.all()
        context['status_choices'] = LeaveRequest.STATUS_CHOICES
        context['leave_types'] = LeaveRequest.LEAVE_TYPES
        return context

class LeaveRequestCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'Manpower/leave_request_form.html'
    
    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except AttributeError:
            return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.object:
            context['title'] = "Create Leave Request"
        else:
            context['title'] = f"Edit Leave Request for {self.object.employee.employee_name}"
        return context
    
    def form_valid(self, form):
        if not form.instance.pk and form.instance.status == 'pending':
            form.instance.employee = self.request.user.employee
        messages.success(self.request, "Leave request saved successfully!")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('manpower:leave_request_list')

@require_POST
@login_required
def delete_leave_request(request, pk):
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    leave_request.delete()
    messages.success(request, "Leave request has been deleted.")
    return JsonResponse({'success': True})

@require_POST
@login_required
def approve_leave_request(request, pk):
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    if leave_request.status == 'pending':
        leave_request.status = 'approved'
        leave_request.approved_by = request.user.employee
        leave_request.approval_date = timezone.now()
        leave_request.save()
        messages.success(request, "Leave request has been approved.")
    else:
        messages.warning(request, "Leave request is not in pending status.")
    return JsonResponse({'success': True})

@require_POST
@login_required
def reject_leave_request(request, pk):
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    if leave_request.status == 'pending':
        leave_request.status = 'rejected'
        leave_request.approved_by = request.user.employee
        leave_request.approval_date = timezone.now()
        leave_request.save()
        messages.success(request, "Leave request has been rejected.")
    else:
        messages.warning(request, "Leave request is not in pending status.")
    return JsonResponse({'success': True})


class AttendanceListView(LoginRequiredMixin, ListView):
    model = Attendance
    template_name = 'Manpower/attendance_list.html'
    context_object_name = 'attendances'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('employee', 'shift')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        employee_id = self.request.GET.get('employee_id')
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
            
        return queryset.order_by('-date', 'employee__employee_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employees'] = Employee.objects.all()
        context['shifts'] = Shift.objects.all()
        return context

class AttendanceCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = Attendance
    form_class = AttendanceForm
    template_name = 'Manpower/attendance_form.html'
    
    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except AttributeError:
            return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.object:
            context['title'] = "Add Attendance Record"
        else:
            context['title'] = f"Edit Attendance for {self.object.employee.employee_name}"
        return context
    
    def form_valid(self, form):
        messages.success(self.request, "Attendance record saved successfully!")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('manpower:attendance_list')

@require_POST
@login_required
def delete_attendance(request, pk):
    attendance = get_object_or_404(Attendance, pk=pk)
    attendance.delete()
    messages.success(request, "Attendance record has been deleted.")
    return JsonResponse({'success': True})


class EmployeeAvailabilityCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = EmployeeAvailability
    form_class = EmployeeAvailabilityForm
    template_name = 'Manpower/employee_availability_form.html'
    
    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except AttributeError:
            return None
    
    def get_initial(self):
        initial = super().get_initial()
        employee_pk = self.kwargs.get('employee_pk')
        if employee_pk:
            initial['employee'] = get_object_or_404(Employee, pk=employee_pk)
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.object:
            context['title'] = "Add Availability Record"
        else:
            context['title'] = f"Edit Availability for {self.object.employee.employee_name}"
        return context
    
    def form_valid(self, form):
        messages.success(self.request, "Availability record saved successfully!")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('manpower:employee_detail', kwargs={'pk': self.object.employee.pk})

@require_POST
@login_required
def delete_employee_availability(request, pk):
    availability = get_object_or_404(EmployeeAvailability, pk=pk)
    employee_pk = availability.employee.pk
    availability.delete()
    messages.success(request, "Availability record has been deleted.")
    return JsonResponse({
        'success': True,
        'redirect_url': reverse_lazy('manpower:employee_detail', kwargs={'pk': employee_pk})
    })

class EmployeeSkillCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = EmployeeSkill
    form_class = EmployeeSkillForm
    template_name = 'Manpower/employee_skill_form.html'
    
    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except AttributeError:
            return None
    
    def get_initial(self):
        initial = super().get_initial()
        employee_pk = self.kwargs.get('employee_pk')
        if employee_pk:
            initial['employee'] = get_object_or_404(Employee, pk=employee_pk)
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.object:
            context['title'] = "Add Skill to Employee"
            context['employee'] = get_object_or_404(Employee, pk=self.kwargs.get('employee_pk'))
        else:
            context['title'] = f"Edit {self.object.employee.employee_name}'s Skill"
        return context
    
    def form_valid(self, form):
        messages.success(self.request, "Employee skill saved successfully!")
        return super().form_valid(form)
    
    def get_success_url(self):
        if self.object:
            return reverse_lazy('manpower:employee_detail', kwargs={'pk': self.object.employee.pk})
        return reverse_lazy('manpower:employee_list')

@require_POST
@login_required
def delete_employee_skill(request, pk):
    employee_skill = get_object_or_404(EmployeeSkill, pk=pk)
    employee_pk = employee_skill.employee.pk
    employee_skill.delete()
    messages.success(request, "Employee skill has been removed.")
    return JsonResponse({
        'success': True,
        'redirect_url': reverse_lazy('manpower:employee_detail', kwargs={'pk': employee_pk})
    })


def manpower_dashboard(request):
    # Calculate date ranges
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Employee statistics
    total_employees = Employee.objects.all().count()
    available_today = EmployeeAvailability.objects.filter(
        date=today, 
        is_available=True
    ).count()
    on_leave_today = LeaveRequest.objects.filter(
        start_date__lte=today,
        end_date__gte=today,
        status='approved'
    ).count()
    
    # Skill gaps - now based on Routing's labor requirements
    skill_gaps = LaborRequirement.objects.filter(
        routing__production_order__start_date__gte=today
    ).values('skill__skill_name').annotate(
        total_needed=Sum('employees_needed'),
        assigned=Count('routing', distinct=True)
    ).filter(total_needed__gt=F('assigned'))
    
    # Current assignments - now properly linked through Routing
    today_assignments = LaborAssignment.objects.select_related(
        'employee', 'shift', 'schedule',
    )[:5]  # Limit to 5 for the dashboard
    
    # Shift distribution - now considering Routing connections
    shift_distribution = LaborAssignment.objects.filter(
        date__range=[start_of_week, end_of_week]
    ).values('shift__shift_name').annotate(
        total=Count('id')
    ).order_by('shift__start_time')
    
    # Skill distribution
    skill_distribution = EmployeeSkill.objects.values(
        'skill__skill_name'
    ).annotate(
        total=Count('id'),
        avg_proficiency=Sum('proficiency') / Count('id')
    ).order_by('-total')[:10]
    
    # Attendance status
    attendance_status = Attendance.objects.filter(
        date=today
    ).values('status').annotate(
        count=Count('id')
    )
    
    # Routing-based statistics
    active_routings = MachineScheduling.objects.distinct().count()
    
    context = {
        'today': today,
        'start_of_week': start_of_week,
        'end_of_week': end_of_week,
        'total_employees': total_employees,
        'available_today': available_today,
        'on_leave_today': on_leave_today,
        'unavailable_today': total_employees - available_today - on_leave_today,
        'skill_gaps': skill_gaps,
        'today_assignments': today_assignments,
        'shift_distribution': shift_distribution,
        'skill_distribution': skill_distribution,
        'attendance_status': attendance_status,
        'active_routings': active_routings,
    }
    
    return render(request, 'Manpower/dashboard.html', context)

def daily_assignments(request, date):
    assignments = LaborAssignment.objects.filter(date=date).select_related(
        'employee', 'shift', 'schedule'
    )
    
    context = {
        'date': date,
        'assignments': assignments,
    }
    return render(request, 'Manpower/daily_assignments.html', context)

def skill_gaps_report(request):
    skill_gaps = LaborRequirement.objects.filter(
        routing__production_orders__start_date__gte=timezone.now().date()
    ).values('skill__skill_name', 'skill__skill_code').annotate(
        total_needed=Sum('employees_needed')
    )
    
    context = {
        'skill_gaps': skill_gaps,
    }
    
    return render(request, 'Manpower/skill_gaps.html', context)

def routing_assignments(request, routing_id):
    routing = get_object_or_404(Routing, pk=routing_id)
    assignments = LaborAssignment.objects.filter(
        schedule__routing=routing
    ).select_related(
        'employee', 'shift', 'schedule'
    )
    
    # Calculate total required labor hours
    labor_requirements = LaborRequirement.objects.filter(routing=routing)
    total_required_hours = sum(
        req.employees_needed * req.min_proficiency * 0.2  # Example calculation
        for req in labor_requirements
    )
    
    # Calculate actual assigned hours
    total_assigned_hours = sum(
        float(assignment.hours_allocated)
        for assignment in assignments
    )
    
    context = {
        'routing': routing,
        'assignments': assignments,
        'labor_requirements': labor_requirements,
        'coverage_percentage': (total_assigned_hours / total_required_hours * 100) if total_required_hours else 0,
    }
    
    return render(request, 'Manpower/routing_assignments.html', context)


def upload_attendance(request):
    if request.method == 'POST':
        try:
            # Get the uploaded file
            uploaded_file = request.FILES['attendance_file']
            shift_id = request.POST.get('shift')
            
            if not shift_id:
                return JsonResponse({'success': False, 'error': 'Please select a shift'})
                
            shift = Shift.objects.get(id=shift_id)
            
            # Read the Excel file
            df = pd.read_excel(uploaded_file)
            
            # Validate required columns
            required_columns = ['Employee Name', 'Date', 'Clock In', 'Clock Out']
            for col in required_columns:
                if col not in df.columns:
                    return JsonResponse({'success': False, 'error': f'Missing column: {col}'})
            
            # Process each row
            success_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    employee_name = row['Employee Name']
                    date_str = row['Date']
                    clock_in_str = row['Clock In']
                    clock_out_str = row['Clock Out']
                    
                    # Find employee
                    try:
                        employee = Employee.objects.get(employee_name=employee_name)
                    except Employee.DoesNotExist:
                        errors.append(f"Row {index+1}: Employee '{employee_name}' not found")
                        error_count += 1
                        continue
                    
                    # Parse dates and times
                    try:
                        date = pd.to_datetime(date_str).date()
                        clock_in = pd.to_datetime(clock_in_str) if pd.notna(clock_in_str) else None
                        clock_out = pd.to_datetime(clock_out_str) if pd.notna(clock_out_str) else None
                    except Exception as e:
                        errors.append(f"Row {index+1}: Error parsing date/time - {str(e)}")
                        error_count += 1
                        continue
                    
                    # Create or update attendance record
                    attendance, created = Attendance.objects.update_or_create(
                        employee=employee,
                        date=date,
                        defaults={
                            'shift': shift,
                            'clock_in': clock_in,
                            'clock_out': clock_out,
                            # You might want to add logic to calculate status and overtime here
                        }
                    )
                    
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {index+1}: {str(e)}")
                    error_count += 1
            
            if error_count > 0:
                return JsonResponse({
                    'success': True, 
                    'message': f'Processed {success_count} records successfully, {error_count} errors occurred.',
                    'errors': errors[:10]  # Return first 10 errors
                })
            else:
                return JsonResponse({
                    'success': True, 
                    'message': f'Successfully uploaded {success_count} attendance records'
                })
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def download_attendance_sample(request):
    # Create sample data
    sample_data = {
        'Employee Name': ['John Doe', 'Jane Smith'],
        'Date': ['2023-10-01', '2023-10-01'],
        'Clock In': ['09:00', '08:45'],
        'Clock Out': ['17:00', '17:15']
    }
    
    # Create DataFrame
    df = pd.DataFrame(sample_data)
    
    # Create Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Attendance', index=False)
    
    # Prepare response
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=attendance_sample.xlsx'
    
    return response


def get_employees_with_status(request):
    schedule_id = request.GET.get('schedule_id')
    date = request.GET.get('date')
    
    if not schedule_id or not date:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        schedule = MachineScheduling.objects.get(id=schedule_id)
        routing_id = get_object_or_404(MachineScheduling, id=schedule_id).routing
        requirement = LaborRequirement.objects.get(routing=routing_id)
        
        # Get employees with the required skill and proficiency
        employees = Employee.objects.filter(
            skills__skill=requirement.skill,
            skills__proficiency__name__gte=requirement.min_proficiency
        ).annotate(
            skill_proficiency_level=F('skills__proficiency__name')
        ).distinct()

        # Access the proficiency level
        for employee in employees:
            print(f"{employee.employee_name}")

        
        employee_list = []
        for employee in employees:
            # Check if employee is already assigned on this date
            is_assigned = LaborAssignment.objects.filter(
                employee=employee, 
                date=date
            ).exists()
            
            status = 'Busy' if is_assigned else 'Available'
            
            employee_list.append({
                'id': employee.id,
                'name': employee.employee_name,  # Changed from employee.name to employee.employee_name
                'status': status,
                'proficiency_level': employee.skill_proficiency_level
            })
        
        return JsonResponse({'employees': employee_list})
    
    except MachineScheduling.DoesNotExist:
        return JsonResponse({'error': 'Schedule not found'}, status=404)
    except LaborRequirement.DoesNotExist:
        return JsonResponse({'error': 'Labor requirement not found'}, status=404)
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        fun = tb[0].name if tb else 'unknown'
        print(f"Error in get_employees_with_status: {e}")
        return JsonResponse({'error': str(e)}, status=500)