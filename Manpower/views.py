# views.py
from datetime import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db import models



from .models import (
    Employee, Skill, EmployeeSkill, Shift, LaborRequirement, 
    LaborAssignment, EmployeeAvailability, Attendance, LeaveRequest
)
from .forms import (
    EmployeeForm, SkillForm, EmployeeSkillForm, ShiftForm, 
    LaborRequirementForm, LaborAssignmentForm, EmployeeAvailabilityForm,
    AttendanceForm, LeaveRequestForm
)
from MachinePlan.models import Routing, MachineSchedule

class EmployeeListView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = 'manpower/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                models.Q(employee_code__icontains=search_query) |
                models.Q(employee_name__icontains=search_query)
            )
        return queryset.filter(is_active=True)

class EmployeeCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'manpower/employee_form.html'
    
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

@require_POST
@login_required
def delete_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    employee.is_active = False
    employee.save()
    messages.success(request, f"Employee {employee.employee_name} has been deactivated.")
    return JsonResponse({'success': True})

class EmployeeDetailView(LoginRequiredMixin, DetailView):
    model = Employee
    template_name = 'manpower/employee_detail.html'
    context_object_name = 'employee'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['skills'] = self.object.skills.all().select_related('skill')
        # context['assignments'] = self.object.labor_assignments.all().select_related('schedule', 'shift')
        context['availabilities'] = self.object.availabilities.all().order_by('-date')[:10]
        context['attendances'] = self.object.attendances.all().order_by('-date')[:10]
        return context

# Similar views for other models (Skill, EmployeeSkill, Shift, etc.)
# Following the same pattern as Employee views

class SkillListView(LoginRequiredMixin, ListView):
    model = Skill
    template_name = 'manpower/skill_list.html'
    context_object_name = 'skills'
    paginate_by = 20

class SkillCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = Skill
    form_class = SkillForm
    template_name = 'manpower/skill_form.html'
    
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
    template_name = 'manpower/shift_list.html'
    context_object_name = 'shifts'
    paginate_by = 20

class ShiftCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = Shift
    form_class = ShiftForm
    template_name = 'manpower/shift_form.html'
    
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
    template_name = 'manpower/labor_requirement_list.html'
    context_object_name = 'requirements'
    paginate_by = 20
    
    def get_queryset(self):
        routing_id = self.kwargs.get('routing_id')
        if routing_id:
            return self.model.objects.filter(routing_id=routing_id).select_related('skill')
        return self.model.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['routing'] = get_object_or_404(Routing, pk=self.kwargs.get('routing_id'))
        return context

class LaborRequirementCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = LaborRequirement
    form_class = LaborRequirementForm
    template_name = 'manpower/labor_requirement_form.html'
    
    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except AttributeError:
            return None
    
    def get_initial(self):
        initial = super().get_initial()
        routing_id = self.kwargs.get('routing_id')
        if routing_id:
            initial['routing'] = get_object_or_404(Routing, pk=routing_id)
        return initial
    
    def form_valid(self, form):
        routing_id = self.kwargs.get('routing_id')
        if routing_id and not form.instance.pk:
            form.instance.routing = get_object_or_404(Routing, pk=routing_id)
        messages.success(self.request, "Labor requirement saved successfully!")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('manpower:labor_requirement_list', kwargs={'routing_id': self.object.routing_id})

@require_POST
@login_required
def delete_labor_requirement(request, pk):
    requirement = get_object_or_404(LaborRequirement, pk=pk)
    routing_id = requirement.routing_id
    requirement.delete()
    messages.success(request, "Labor requirement has been deleted.")
    return JsonResponse({'success': True, 'redirect_url': reverse_lazy('manpower:labor_requirement_list', kwargs={'routing_id': routing_id})})

class LaborAssignmentListView(LoginRequiredMixin, ListView):
    model = LaborAssignment
    template_name = 'manpower/labor_assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('employee', 'shift', 'schedule')
        schedule_id = self.request.GET.get('schedule_id')
        if schedule_id:
            queryset = queryset.filter(schedule_id=schedule_id)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        schedule_id = self.request.GET.get('schedule_id')
        if schedule_id:
            context['schedule'] = get_object_or_404(MachineSchedule, pk=schedule_id)
        return context

class LaborAssignmentCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = LaborAssignment
    form_class = LaborAssignmentForm
    template_name = 'manpower/labor_assignment_form.html'
    
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
    template_name = 'manpower/leave_request_list.html'
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
        context['employees'] = Employee.objects.filter(is_active=True)
        context['status_choices'] = LeaveRequest.STATUS_CHOICES
        context['leave_types'] = LeaveRequest.LEAVE_TYPES
        return context

class LeaveRequestCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'manpower/leave_request_form.html'
    
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

class LeaveRequestListView(LoginRequiredMixin, ListView):
    model = LeaveRequest
    template_name = 'manpower/leave_request_list.html'
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
        context['employees'] = Employee.objects.filter(is_active=True)
        context['status_choices'] = LeaveRequest.STATUS_CHOICES
        context['leave_types'] = LeaveRequest.LEAVE_TYPES
        return context

class LeaveRequestCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'manpower/leave_request_form.html'
    
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
    template_name = 'manpower/attendance_list.html'
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
        context['employees'] = Employee.objects.filter(is_active=True)
        return context

class AttendanceCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = Attendance
    form_class = AttendanceForm
    template_name = 'manpower/attendance_form.html'
    
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
    template_name = 'manpower/employee_availability_form.html'
    
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
    template_name = 'manpower/employee_skill_form.html'
    
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