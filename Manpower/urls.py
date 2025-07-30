# urls.py
from django.urls import path
from . import views

app_name = 'manpower'

urlpatterns = [
    # Employee URLs
    path('employees/', views.EmployeeListView.as_view(), name='employee_list'),
    path('employees/add/', views.EmployeeCreateUpdateView.as_view(), name='employee_create'),
    path('employees/<int:pk>/edit/', views.EmployeeCreateUpdateView.as_view(), name='employee_edit'),
    path('employees/<int:pk>/', views.EmployeeDetailView.as_view(), name='employee_detail'),
    path('employees/<int:pk>/delete/', views.delete_employee, name='employee_delete'),
    
    # Employee Skill URLs
    path('employees/<int:employee_pk>/skills/add/', views.EmployeeSkillCreateUpdateView.as_view(), name='employee_skill_add'),
    path('employee-skills/<int:pk>/edit/', views.EmployeeSkillCreateUpdateView.as_view(), name='employee_skill_edit'),
    path('employee-skills/<int:pk>/delete/', views.delete_employee_skill, name='employee_skill_delete'),
    
    # Skill URLs
    path('skills/', views.SkillListView.as_view(), name='skill_list'),
    path('skills/add/', views.SkillCreateUpdateView.as_view(), name='skill_create'),
    path('skills/<int:pk>/edit/', views.SkillCreateUpdateView.as_view(), name='skill_edit'),
    path('skills/<int:pk>/delete/', views.delete_skill, name='skill_delete'),
    
    # Shift URLs
    path('shifts/', views.ShiftListView.as_view(), name='shift_list'),
    path('shifts/add/', views.ShiftCreateUpdateView.as_view(), name='shift_create'),
    path('shifts/<int:pk>/edit/', views.ShiftCreateUpdateView.as_view(), name='shift_edit'),
    path('shifts/<int:pk>/delete/', views.delete_shift, name='shift_delete'),
    
    # Labor Requirement URLs
    path('routing/<int:routing_id>/labor-requirements/', views.LaborRequirementListView.as_view(), name='labor_requirement_list'),
    path('routing/<int:routing_id>/labor-requirements/add/', views.LaborRequirementCreateUpdateView.as_view(), name='labor_requirement_create'),
    path('labor-requirements/<int:pk>/edit/', views.LaborRequirementCreateUpdateView.as_view(), name='labor_requirement_edit'),
    path('labor-requirements/<int:pk>/delete/', views.delete_labor_requirement, name='labor_requirement_delete'),
    
    # Labor Assignment URLs
    path('labor-assignments/', views.LaborAssignmentListView.as_view(), name='labor_assignment_list'),
    path('labor-assignments/add/', views.LaborAssignmentCreateUpdateView.as_view(), name='labor_assignment_create'),
    path('labor-assignments/<int:pk>/edit/', views.LaborAssignmentCreateUpdateView.as_view(), name='labor_assignment_edit'),
    path('labor-assignments/<int:pk>/delete/', views.delete_labor_assignment, name='labor_assignment_delete'),
    
    # Employee Availability URLs
    path('employees/<int:employee_pk>/availability/add/', views.EmployeeAvailabilityCreateUpdateView.as_view(), name='employee_availability_add'),
    path('employee-availability/<int:pk>/edit/', views.EmployeeAvailabilityCreateUpdateView.as_view(), name='employee_availability_edit'),
    path('employee-availability/<int:pk>/delete/', views.delete_employee_availability, name='employee_availability_delete'),
    
    # Attendance URLs
    path('attendance/', views.AttendanceListView.as_view(), name='attendance_list'),
    path('attendance/add/', views.AttendanceCreateUpdateView.as_view(), name='attendance_create'),
    path('attendance/<int:pk>/edit/', views.AttendanceCreateUpdateView.as_view(), name='attendance_edit'),
    path('attendance/<int:pk>/delete/', views.delete_attendance, name='attendance_delete'),
    
    # Leave Request URLs
    path('leave-requests/', views.LeaveRequestListView.as_view(), name='leave_request_list'),
    path('leave-requests/add/', views.LeaveRequestCreateUpdateView.as_view(), name='leave_request_create'),
    path('leave-requests/<int:pk>/edit/', views.LeaveRequestCreateUpdateView.as_view(), name='leave_request_edit'),
    path('leave-requests/<int:pk>/delete/', views.delete_leave_request, name='leave_request_delete'),
    path('leave-requests/<int:pk>/approve/', views.approve_leave_request, name='leave_request_approve'),
    path('leave-requests/<int:pk>/reject/', views.reject_leave_request, name='leave_request_reject'),
]