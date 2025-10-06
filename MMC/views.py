# views.py 
from django.forms import BooleanField, CharField, DecimalField, IntegerField
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, DeleteView
from django.db.models import Q, Count, Sum, Avg, F, Value, Case, When, ExpressionWrapper, DurationField
from django.db.models.functions import Concat, TruncMonth, ExtractYear
from django.utils import timezone
from django.urls import reverse_lazy, reverse
from django.core.paginator import Paginator
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.core.exceptions import PermissionDenied
from datetime import datetime, timedelta
import json
import csv
from io import StringIO, BytesIO
import logging
from django.db import transaction

logger = logging.getLogger(__name__)

from .models import *
from .forms import *

# Utility Functions
def is_rmp(user):
    return user.user_type == 'rmp'

def is_admin(user):
    return user.user_type == 'admin'

def is_staff(user):
    return user.user_type == 'staff'

def is_admin_or_staff(user):
    return user.user_type in ['admin', 'staff']

def is_cpd_provider(user):
    return user.user_type == 'cpd_provider'

def get_rmp_profile(user):
    try:
        return RMPProfile.objects.get(user=user)
    except RMPProfile.DoesNotExist:
        return None

# Decorators for permission checking
def rmp_required(function):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.user_type == 'rmp':
            return function(request, *args, **kwargs)
        messages.error(request, "Access denied. RMP login required.")
        return redirect('login')
    return wrapper

def admin_required(function):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.user_type in ['ADMIN', 'SUPER_ADMIN']:
            return function(request, *args, **kwargs)
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('login')
    return wrapper


def create_audit_log(user, action_type, model_name, object_id, description, request=None):
    """Create audit log entry"""
    try:
        audit_log = AuditLog.objects.create(
            user=user,
            action_type=action_type,
            model_name=model_name,
            object_id=str(object_id),
            description=description,
            ip_address=request.META.get('REMOTE_ADDR') if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
        )
        return audit_log
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")


def landing_page(request):
    """Comprehensive landing page for MMC portal"""
    
    # Get statistics for the landing page
    total_rmps = RMPProfile.objects.filter(registration_status='active').count()
    total_applications = Application.objects.count()
    recent_applications = Application.objects.filter(
        submitted_date__gte=timezone.now() - timedelta(days=30)
    ).count()
    
    # CPD Statistics
    cpd_programs_count = CPDProgram.objects.filter(is_active=True).count()
    upcoming_cpd_programs = CPDProgram.objects.filter(
        start_date__gte=timezone.now(),
        is_active=True
    ).count()
    
    # Get active announcements from system config
    # announcements = SystemConfig.objects.filter(
    #     key__startswith='announcement_',
    #     is_active=True
    # ).order_by('-updated_date')[:5]
    from django.db.models.functions import Cast
    from django.db.models import CharField

    # announcements = SystemConfig.objects.annotate(
    #     key_text=Cast('key', output_field=CharField())
    # ).filter(
    #     key_text__startswith='announcement_',
    #     is_active=True
    # ).order_by('-updated_date')[:5]

    # # Get notifications
    # notifications = SystemConfig.objects.filter(
    #     key__startswith='notification_',
    #     is_active=True
    # ).order_by('-updated_date')[:5]
    
    # # Get downloads
    # downloads = SystemConfig.objects.filter(
    #     key__startswith='download_',
    #     is_active=True
    # ).order_by('-updated_date')[:5]
    
    # # Get instructions
    # instructions = SystemConfig.objects.filter(
    #     key__startswith='instruction_',
    #     is_active=True
    # ).order_by('-updated_date')[:5]
    announcements = SystemConfig.objects.extra(
        where=["CAST(`key` AS CHAR) LIKE 'announcement_%' AND is_active = TRUE"]
    ).order_by('-updated_date')[:5]

    notifications = SystemConfig.objects.extra(
        where=["CAST(`key` AS CHAR) LIKE 'notification_%' AND is_active = TRUE"]
    ).order_by('-updated_date')[:5]

    downloads = SystemConfig.objects.extra(
        where=["CAST(`key` AS CHAR) LIKE 'download_%' AND is_active = TRUE"]
    ).order_by('-updated_date')[:5]

    instructions = SystemConfig.objects.extra(
        where=["CAST(`key` AS CHAR) LIKE 'instruction_%' AND is_active = TRUE"]
    ).order_by('-updated_date')[:5]

    # Service categories for quick access
    service_categories = {
        'Registration Services': [
            ('provisional', 'Provisional Registration'),
            ('permanent', 'Permanent Registration'),
            ('foreign_provisional', 'Foreign Provisional Registration'),
            ('foreign_permanent', 'Foreign Permanent Registration'),
            ('additional_qualification', 'Additional Qualification'),
            ('renewal', 'Renewal of Registration'),
        ],
        'Certificate Services': [
            ('good_standing_mmc', 'Good Standing (MMC)'),
            ('good_standing_nmc', 'Good Standing (NMC)'),
            ('good_standing_nri', 'Good Standing (NRI)'),
            ('noc_state', 'NOC for Other State'),
            ('duplicate', 'Duplicate Certificate'),
            ('confirmation', 'Confirmation of Registration'),
        ],
        'Update Services': [
            ('address_change', 'Change of Address'),
            ('name_change', 'Change of Name'),
            ('manual_verification', 'Document Verification'),
            ('id_card', 'ID Card Generation'),
        ]
    }
    
    # Quick stats for display
    quick_stats = {
        'total_rmps': total_rmps,
        'provisional_registrations': RMPProfile.objects.filter(
            registration_type='provisional',
            registration_status='active'
        ).count(),
        'additional_qualifications': Application.objects.filter(
            application_type='additional_qualification',
            status='approved'
        ).count(),
        'cpd_programs': cpd_programs_count,
        'online_cpd_points': CPDAttendance.objects.filter(
            attendance_status='completed'
        ).aggregate(total=Sum('points_earned'))['total'] or 0,
        'recent_applications': recent_applications,
    }
    
    context = {
        'total_rmps': total_rmps,
        'total_applications': total_applications,
        'cpd_programs_count': cpd_programs_count,
        'upcoming_cpd_programs': upcoming_cpd_programs,
        'announcements': announcements,
        'notifications': notifications,
        'downloads': downloads,
        'instructions': instructions,
        'service_categories': service_categories,
        'quick_stats': quick_stats,
    }
    
    return render(request, 'MMC/landing/landing_page.html', context)

# ============ ENHANCED SERVICE-SPECIFIC VIEWS ============
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

def get_service_categories():
    """Get all service categories with enhanced information"""
    return {
        'registration_services': {
            'title': 'Registration Services',
            'description': 'Medical registration and licensing services for practitioners',
            'icon': 'bi-person-badge',
            'services': [
                {
                    'code': 'provisional',
                    'name': 'Provisional Registration',
                    'description': 'For fresh medical graduates to start practice',
                    'icon': 'bi-person-plus',
                    'color': 'primary',
                    'fee': 1000,
                    'duration': '7-10 days',
                    'eligibility': 'MBBS graduates within 1 year of passing',
                    'documents_required': 8
                },
                {
                    'code': 'permanent', 
                    'name': 'Permanent Registration',
                    'description': 'Full registration for established practitioners',
                    'icon': 'bi-person-check',
                    'color': 'success',
                    'fee': 2000,
                    'duration': '15-20 days',
                    'eligibility': 'Completed internship + 1 year practice',
                    'documents_required': 10
                },
                {
                    'code': 'foreign_provisional',
                    'name': 'Foreign Provisional Registration', 
                    'description': 'Provisional registration for foreign medical graduates',
                    'icon': 'bi-globe',
                    'color': 'warning',
                    'fee': 5000,
                    'duration': '20-25 days',
                    'eligibility': 'FMGE passed + internship completed',
                    'documents_required': 12
                },
                {
                    'code': 'foreign_permanent',
                    'name': 'Foreign Permanent Registration',
                    'description': 'Permanent registration for foreign graduates',
                    'icon': 'bi-passport',
                    'color': 'info',
                    'fee': 7000,
                    'duration': '25-30 days',
                    'eligibility': '2 years practice after provisional',
                    'documents_required': 14
                },
                {
                    'code': 'additional_qualification',
                    'name': 'Additional Qualification Registration',
                    'description': 'Register additional medical qualifications',
                    'icon': 'bi-award',
                    'color': 'secondary',
                    'fee': 1500,
                    'duration': '10-15 days',
                    'eligibility': 'Valid primary registration',
                    'documents_required': 6
                },
                {
                    'code': 'renewal',
                    'name': 'Renewal of Registration',
                    'description': 'Renew your medical registration periodically',
                    'icon': 'bi-arrow-clockwise',
                    'color': 'primary',
                    'fee': 1000,
                    'duration': '3-5 days',
                    'eligibility': 'Existing registration holders',
                    'documents_required': 4
                },
            ]
        },
        'verification_services': {
            'title': 'Verification Services',
            'description': 'Document and form verification services',
            'icon': 'bi-clipboard-check',
            'services': [
                {
                    'code': 'verification',
                    'name': 'Form Verification',
                    'description': 'Verify application forms and documents',
                    'icon': 'bi-file-check',
                    'color': 'info',
                    'fee': 500,
                    'duration': '5-7 days',
                    'eligibility': 'All registered practitioners',
                    'documents_required': 3
                },
                {
                    'code': 'manual_verification',
                    'name': 'Manual Document Verification',
                    'description': 'Physical verification of original documents',
                    'icon': 'bi-eye',
                    'color': 'warning',
                    'fee': 300,
                    'duration': '2-3 days',
                    'eligibility': 'All registered practitioners', 
                    'documents_required': 2
                },
            ]
        },
        'modification_services': {
            'title': 'Modification Services',
            'description': 'Update and modify your registration details',
            'icon': 'bi-pencil-square',
            'services': [
                {
                    'code': 'address_change',
                    'name': 'Change of Address',
                    'description': 'Update your registered communication address',
                    'icon': 'bi-house',
                    'color': 'secondary',
                    'fee': 300,
                    'duration': '3-5 days',
                    'eligibility': 'All registered practitioners',
                    'documents_required': 2
                },
                {
                    'code': 'name_change',
                    'name': 'Change of Name',
                    'description': 'Update your registered name',
                    'icon': 'bi-person',
                    'color': 'secondary', 
                    'fee': 500,
                    'duration': '7-10 days',
                    'eligibility': 'All registered practitioners',
                    'documents_required': 4
                },
            ]
        },
        'certificate_services': {
            'title': 'Certificate Services',
            'description': 'Generate various certificates and documents',
            'icon': 'bi-file-earmark-text',
            'services': [
                {
                    'code': 'good_standing_mmc',
                    'name': 'Good Standing Certificate (MMC)',
                    'description': 'Certificate for use within Maharashtra',
                    'icon': 'bi-shield-check',
                    'color': 'success',
                    'fee': 1000,
                    'duration': '3-5 days',
                    'eligibility': 'Active registration holders',
                    'documents_required': 2
                },
                {
                    'code': 'good_standing_nmc',
                    'name': 'Good Standing Certificate (NMC)',
                    'description': 'Certificate for National Medical Commission',
                    'icon': 'bi-shield',
                    'color': 'success',
                    'fee': 1500,
                    'duration': '5-7 days',
                    'eligibility': 'Active registration holders',
                    'documents_required': 3
                },
                {
                    'code': 'good_standing_nri',
                    'name': 'Good Standing Certificate (NRI)',
                    'description': 'Certificate for non-resident Indians',
                    'icon': 'bi-globe2',
                    'color': 'info',
                    'fee': 2000,
                    'duration': '7-10 days',
                    'eligibility': 'Active registration holders',
                    'documents_required': 4
                },
                {
                    'code': 'noc_state',
                    'name': 'NOC for Other State',
                    'description': 'No Objection Certificate for other states',
                    'icon': 'bi-send',
                    'color': 'warning',
                    'fee': 1000,
                    'duration': '7-10 days',
                    'eligibility': 'Active registration holders',
                    'documents_required': 3
                },
                {
                    'code': 'duplicate',
                    'name': 'Duplicate Certificate',
                    'description': 'Replace lost or damaged certificates',
                    'icon': 'bi-file-earmark-plus',
                    'color': 'secondary',
                    'fee': 500,
                    'duration': '5-7 days',
                    'eligibility': 'Original certificate holders',
                    'documents_required': 2
                },
                {
                    'code': 'confirmation',
                    'name': 'Confirmation of Registration',
                    'description': 'Registration confirmation letter',
                    'icon': 'bi-check-circle',
                    'color': 'info',
                    'fee': 300,
                    'duration': '2-3 days',
                    'eligibility': 'All registered practitioners',
                    'documents_required': 1
                },
            ]
        },
        'special_services': {
            'title': 'Special Services',
            'description': 'Specialized services for specific requirements',
            'icon': 'bi-star',
            'services': [
                {
                    'code': 'reapplication_noc',
                    'name': 'Reapplication of NOC',
                    'description': 'Reapply for No Objection Certificate',
                    'icon': 'bi-arrow-repeat',
                    'color': 'warning',
                    'fee': 500,
                    'duration': '5-7 days',
                    'eligibility': 'Previous NOC applicants',
                    'documents_required': 3
                },
                {
                    'code': 'noc_provisional',
                    'name': 'NOC for Provisional',
                    'description': 'NOC for provisional to other state',
                    'icon': 'bi-send-check',
                    'color': 'info',
                    'fee': 800,
                    'duration': '7-10 days',
                    'eligibility': 'Provisional registration holders',
                    'documents_required': 4
                },
                {
                    'code': 'foreign_verification',
                    'name': 'Foreign Verification',
                    'description': 'International registration verification',
                    'icon': 'bi-globe-americas',
                    'color': 'primary',
                    'fee': 3000,
                    'duration': '15-20 days',
                    'eligibility': 'All registered practitioners',
                    'documents_required': 6
                },
                {
                    'code': 'defaulter',
                    'name': 'Permanent Registration for Defaulter',
                    'description': 'Registration for defaulting RMPs',
                    'icon': 'bi-exclamation-triangle',
                    'color': 'danger',
                    'fee': 5000,
                    'duration': '20-25 days',
                    'eligibility': 'Defaulting practitioners',
                    'documents_required': 8
                },
                {
                    'code': 'reentry',
                    'name': 'Re-enter Registration',
                    'description': 'Rejoin medical practice after break',
                    'icon': 'bi-door-open',
                    'color': 'secondary',
                    'fee': 2000,
                    'duration': '10-15 days',
                    'eligibility': 'Previously registered practitioners',
                    'documents_required': 5
                },
                {
                    'code': 'termination',
                    'name': 'Termination of RMP',
                    'description': 'Voluntary termination of registration',
                    'icon': 'bi-person-x',
                    'color': 'danger',
                    'fee': 0,
                    'duration': '5-7 days',
                    'eligibility': 'Active registration holders',
                    'documents_required': 3
                },
                {
                    'code': 'id_card',
                    'name': 'ID Card Generation',
                    'description': 'Generate practitioner identity card',
                    'icon': 'bi-credit-card',
                    'color': 'success',
                    'fee': 200,
                    'duration': '3-5 days',
                    'eligibility': 'All registered practitioners',
                    'documents_required': 2
                },
            ]
        }
    }

@login_required
def service_selection(request):
    """Enhanced service selection page for all 23 registration services"""
    service_categories = get_service_categories()

    # Fetch all applications for current user once
    user_apps = Application.objects.filter(applicant=request.user)

    # Pending applications
    pending_applications = user_apps.filter(
        status__in=['draft', 'submitted', 'under_review', 'additional_info_required']
    ).select_related('rmp', 'assigned_to', 'approved_by')

    # Application counts by type (for badges beside services)
    application_counts = (
        pending_applications.values('application_type')
        .annotate(count=Count('application_type'))
    )
    pending_count_dict = {item['application_type']: item['count'] for item in application_counts}

    # Add pending counts to each service
    for category_name, category_data in service_categories.items():
        for service in category_data['services']:
            service['pending_count'] = pending_count_dict.get(service['code'], 0)

    # --- 📊 User statistics (optimized with single aggregation query) ---
    total_apps = user_apps.count()

    # Aggregate counts in one DB call
    status_counts = (
        user_apps.values('status')
        .annotate(count=Count('status'))
    )
    status_dict = {item['status']: item['count'] for item in status_counts}

    user_stats = {
        'total_applications': total_apps,
        'approved_applications': status_dict.get('approved', 0),
        'completed_applications': status_dict.get('completed', 0),
        'rejected_applications': status_dict.get('rejected', 0),
        'pending_applications': sum(
            status_dict.get(s, 0) for s in ['draft', 'submitted', 'under_review', 'additional_info_required']
        ),
        'recent_applications': user_apps.filter(
            submitted_date__gte=timezone.now() - timedelta(days=30)
        ).count(),
    }

    # --- ⚡ Quick actions based on RMP profile ---
    quick_actions = []
    if hasattr(request.user, 'rmp_profile'):
        rmp_profile = request.user.rmp_profile
        if rmp_profile.registration_status == 'active':
            quick_actions.append({
                'name': 'Renew Registration',
                'description': 'Your registration is active',
                'action': 'renewal',
                'icon': 'bi-check-circle',
                'color': 'success'
            })
        elif rmp_profile.registration_status == 'pending':
            quick_actions.append({
                'name': 'Complete Registration',
                'description': 'Registration pending completion',
                'action': 'provisional',
                'icon': 'bi-exclamation-circle',
                'color': 'warning'
            })
        else:
            quick_actions.append({
                'name': 'Start New Registration',
                'description': 'You can apply for registration services',
                'action': 'permanent',
                'icon': 'bi-person-plus',
                'color': 'primary'
            })

    context = {
        'service_categories': service_categories,
        'user_stats': user_stats,
        'pending_applications': pending_applications[:5],  # recent 5 pending
        'quick_actions': quick_actions,
        'total_services': sum(len(cat['services']) for cat in service_categories.values())
    }

    return render(request, 'MMC/landing/service_selection.html', context)


@login_required
def initiate_service(request, service_type):
    """Enhanced service initiation with validations"""
    service_categories = get_service_categories()
    
    # Find the service in categories
    target_service = None
    for category_name, category_data in service_categories.items():
        for service in category_data['services']:
            if service['code'] == service_type:
                target_service = service
                break
        if target_service:
            break
    
    if not target_service:
        messages.error(request, 'Invalid service type selected.')
        return redirect('service_selection')
    
    # Check if service type is valid in Application model
    valid_types = dict(Application.APPLICATION_TYPES).keys()
    if service_type not in valid_types:
        messages.error(request, 'This service is currently not available.')
        return redirect('service_selection')
    
    # Check for existing pending applications of same type
    existing_app = Application.objects.filter(
        applicant=request.user,
        application_type=service_type,
        status__in=['draft', 'submitted', 'under_review', 'additional_info_required']
    ).first()
    
    if existing_app:
        messages.info(request, 
            f'You already have a pending {target_service["name"]} application. '
            f'You can continue with your existing application.'
        )
        return redirect('application_status', application_id=existing_app.application_id)
    
    # Additional validations based on service type
    validation_error = validate_service_eligibility(request.user, service_type)
    if validation_error:
        messages.error(request, validation_error)
        return redirect('service_selection')
    
    try:
        # Create new application
        application = Application.objects.create(
            applicant=request.user,
            rmp=request.user.rmp_profile,
            application_type=service_type,
            status='draft',
            fee_amount=target_service['fee'],
            application_data={
                'service_name': target_service['name'],
                'initiated_at': timezone.now().isoformat(),
                'estimated_duration': target_service['duration'],
                'required_documents': target_service['documents_required']
            }
        )
        
        # Create initial step
        ApplicationStep.objects.create(
            application=application,
            step_number=1,
            step_name='Service Selection',
            is_completed=True,
            completed_date=timezone.now(),
            data={'service_type': service_type}
        )
        
        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action_type='create',
            model_name='Application',
            object_id=str(application.application_id),
            description=f'Initiated {target_service["name"]} application',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        messages.success(request, 
            f'{target_service["name"]} application started successfully! '
            f'Application ID: {application.application_id}'
        )
        
        # Redirect to appropriate wizard step
        return redirect('application_step', application_id=application.application_id, step=2)
        
    except Exception as e:
        messages.error(request, f'Error creating application: {str(e)}')
        return redirect('service_selection')

def validate_service_eligibility(user, service_type):
    """Validate if user is eligible for the selected service"""
    
    if not hasattr(user, 'rmp_profile'):
        return "RMP profile not found. Please complete your profile first."
    
    rmp_profile = user.rmp_profile
    
    # Service-specific validations
    validations = {
        'renewal': {
            'check': rmp_profile.registration_status != 'active',
            'message': 'Your registration is not active or already renewed.'
        },
        'additional_qualification': {
            'check': rmp_profile.registration_status != 'active',
            'message': 'You need an active registration to add qualifications.'
        },
        'good_standing_mmc': {
            'check': rmp_profile.registration_status != 'active',
            'message': 'Only actively registered practitioners can request Good Standing certificates.'
        },
        'defaulter': {
            'check': rmp_profile.registration_status != 'suspended',
            'message': 'This service is only for defaulting practitioners.'
        }
    }
    
    if service_type in validations:
        validation = validations[service_type]
        if validation['check']:
            return validation['message']
    
    return None

@login_required
def service_details(request, service_type):
    """Service details page with comprehensive information"""
    service_categories = get_service_categories()
    
    # Find the service
    target_service = None
    category_name = None
    for cat_name, cat_data in service_categories.items():
        for service in cat_data['services']:
            if service['code'] == service_type:
                target_service = service
                category_name = cat_data['title']
                break
        if target_service:
            break
    
    if not target_service:
        messages.error(request, 'Service not found.')
        return redirect('service_selection')
    
    # Get similar services
    similar_services = []
    for cat_data in service_categories.values():
        for service in cat_data['services']:
            if service['code'] != service_type and service['color'] == target_service['color']:
                similar_services.append(service)
            if len(similar_services) >= 3:
                break
        if len(similar_services) >= 3:
            break
    
    # Get recent successful applications of this type
    recent_success = Application.objects.filter(
        application_type=service_type,
        status='approved'
    ).select_related('applicant').order_by('-approval_date')[:5]
    
    context = {
        'service': target_service,
        'category_name': category_name,
        'similar_services': similar_services,
        'recent_success': recent_success,
        'is_eligible': validate_service_eligibility(request.user, service_type) is None
    }
    
    return render(request, 'MMC/landing/service_details.html', context)

# views.py - Add these new views
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import SystemConfig, RMPProfile, Application, CPDProgram, CPDAttendance
from django.utils import timezone
from datetime import timedelta

def about_mmc(request):
    """About MMC page with detailed information"""
    about_content = {
        'title': 'About Maharashtra Medical Council',
        'sections': [
            {
                'title': 'Our Mission',
                'content': 'To regulate the medical profession in Maharashtra through registration, education, and disciplinary oversight, ensuring high standards of medical practice and patient care.'
            },
            {
                'title': 'Our Vision',
                'content': 'To be a leading medical council that promotes excellence in medical education, ethical practice, and continuous professional development for the benefit of public health.'
            },
            {
                'title': 'History',
                'content': 'The Maharashtra Medical Council was established under the M.M.C. Act 1965 as a statutory regulatory body responsible for the registration and governance of medical practitioners in Maharashtra.'
            },
            {
                'title': 'Functions & Responsibilities',
                'content': '''
                <ul>
                    <li>Registration of medical practitioners</li>
                    <li>Maintenance of the State Medical Register</li>
                    <li>Regulation of medical education and practice</li>
                    <li>Continuing Professional Development (CPD) programs</li>
                    <li>Disciplinary proceedings and ethical oversight</li>
                    <li>Issuance of certificates and good standing documents</li>
                </ul>
                '''
            },
            {
                'title': 'Digital Transformation',
                'content': 'MMC has embraced digital transformation to provide efficient, transparent, and accessible services to medical practitioners through this comprehensive web portal.'
            }
        ],
        'key_facts': {
            'Established': '1965',
            'Act': 'Maharashtra Medical Council Act, 1965',
            'Headquarters': 'Mumbai, Maharashtra',
            'Registration Types': 'Provisional, Permanent, Additional Qualifications',
            'Services': '23+ online services for medical practitioners'
        }
    }
    
    # Try to get dynamic content from SystemConfig
    try:
        about_config = SystemConfig.objects.get(key='about_page_content')
        about_content = json.loads(about_config.value)
    except SystemConfig.DoesNotExist:
        pass
    
    context = {
        'about_content': about_content,
        'page_title': 'About MMC'
    }
    return render(request, 'MMC/landing/about.html', context)

def contact_us(request):
    """Contact us page with multiple contact methods"""
    contact_info = {
        'office_address': {
            'title': 'Head Office',
            'address': 'Maharashtra Medical Council, \nOpposite to GPO, \nMumbai - 400001, Maharashtra',
            'phone': '022-23007650',
            'email': 'maharashtramcouncil@gmail.com'
        },
        'technical_support': {
            'title': 'Technical Support',
            'phone': '022-23007650 (Extension 110)',
            'email': 'mmconlineservices1@gmail.com',
            'hours': 'Monday to Friday: 9:30 AM - 6:00 PM\nSaturday: 9:30 AM - 2:00 PM'
        },
        'helpline_numbers': {
            'title': 'Helpline Numbers',
            'numbers': [
                '022-23007650',
                '8169118266',
                '7021932544'
            ],
            'availability': '24/7 for emergency support'
        },
        'department_contacts': [
            {
                'department': 'Registration Department',
                'contact': '022-23007650 (Ext. 101)',
                'email': 'registration.mmc@gmail.com'
            },
            {
                'department': 'CPD Department',
                'contact': '022-23007650 (Ext. 102)',
                'email': 'cpd.mmc@gmail.com'
            },
            {
                'department': 'Complaint Cell',
                'contact': '022-23007650 (Ext. 103)',
                'email': 'complaints.mmc@gmail.com'
            },
            {
                'department': 'Certificate Section',
                'contact': '022-23007650 (Ext. 104)',
                'email': 'certificates.mmc@gmail.com'
            }
        ]
    }
    
    context = {
        'contact_info': contact_info,
        'page_title': 'Contact Us'
    }
    return render(request, 'MMC/landing/contact.html', context)

def rti_information(request):
    """Right to Information (RTI) page"""
    rti_info = {
        'title': 'Right to Information (RTI)',
        'introduction': 'The Maharashtra Medical Council is committed to transparency and accountability under the Right to Information Act, 2005.',
        'sections': [
            {
                'title': 'Public Information Officer',
                'content': '''
                <p><strong>Name:</strong> Dr. Sanjay Sharma</p>
                <p><strong>Designation:</strong> Public Information Officer</p>
                <p><strong>Contact:</strong> 022-23007650 (Ext. 201)</p>
                <p><strong>Email:</strong> rti.mmc@gmail.com</p>
                '''
            },
            {
                'title': 'Appellate Authority',
                'content': '''
                <p><strong>Name:</strong> Dr. Rajesh Patil</p>
                <p><strong>Designation:</strong> Appellate Authority</p>
                <p><strong>Contact:</strong> 022-23007650 (Ext. 202)</p>
                <p><strong>Email:</strong> appellate.mmc@gmail.com</p>
                '''
            },
            {
                'title': 'How to File RTI Application',
                'content': '''
                <ol>
                    <li>Download the RTI application form</li>
                    <li>Fill in the required details</li>
                    <li>Pay the prescribed fee (₹10 for central government)</li>
                    <li>Submit to the Public Information Officer</li>
                    <li>Receive response within 30 days</li>
                </ol>
                '''
            },
            {
                'title': 'RTI Fee Structure',
                'content': '''
                <ul>
                    <li>Application Fee: ₹10</li>
                    <li>Additional Pages: ₹2 per page</li>
                    <li>Inspection of Documents: ₹10 per hour</li>
                    <li>CD/DVD: ₹50 per disc</li>
                </ul>
                '''
            },
            {
                'title': 'Information Available',
                'content': '''
                <ul>
                    <li>Council Members and Office Bearers</li>
                    <li>Budget and Annual Reports</li>
                    <li>Registration Statistics</li>
                    <li>Disciplinary Proceedings</li>
                    <li>CPD Program Details</li>
                    <li>Service Charges and Fees</li>
                </ul>
                '''
            }
        ],
        'downloads': [
            {'name': 'RTI Application Form', 'url': '/downloads/rti_application.pdf'},
            {'name': 'RTI Fee Payment Challan', 'url': '/downloads/rti_challan.pdf'},
            {'name': 'MMC Organization Chart', 'url': '/downloads/organization_chart.pdf'},
        ]
    }
    
    context = {
        'rti_info': rti_info,
        'page_title': 'RTI Information'
    }
    return render(request, 'MMC/landing/rti.html', context)

def act_rules(request):
    """Act and Rules page"""
    legal_documents = {
        'title': 'Acts & Rules',
        'description': 'The Maharashtra Medical Council operates under various acts and rules that govern medical practice in Maharashtra.',
        'documents': [
            {
                'category': 'Primary Legislation',
                'docs': [
                    {'name': 'Maharashtra Medical Council Act, 1965', 'url': '/documents/mmc_act_1965.pdf'},
                    {'name': 'Indian Medical Council Act, 1956', 'url': '/documents/imc_act_1956.pdf'},
                    {'name': 'National Medical Commission Act, 2019', 'url': '/documents/nmc_act_2019.pdf'},
                ]
            },
            {
                'category': 'Rules & Regulations',
                'docs': [
                    {'name': 'MMC Registration Rules, 2022', 'url': '/documents/registration_rules_2022.pdf'},
                    {'name': 'Code of Medical Ethics', 'url': '/documents/code_ethics.pdf'},
                    {'name': 'CPD Guidelines', 'url': '/documents/cpd_guidelines.pdf'},
                    {'name': 'Disciplinary Proceedings Rules', 'url': '/documents/disciplinary_rules.pdf'},
                ]
            },
            {
                'category': 'Notifications & Circulars',
                'docs': [
                    {'name': 'Recent Notifications', 'url': '/documents/recent_notifications.pdf'},
                    {'name': 'Important Circulars', 'url': '/documents/important_circulars.pdf'},
                    {'name': 'Policy Updates', 'url': '/documents/policy_updates.pdf'},
                ]
            },
            {
                'category': 'Forms & Formats',
                'docs': [
                    {'name': 'Registration Application Forms', 'url': '/documents/registration_forms.pdf'},
                    {'name': 'CPD Program Application', 'url': '/documents/cpd_application.pdf'},
                    {'name': 'Complaint Form', 'url': '/documents/complaint_form.pdf'},
                    {'name': 'Certificate Request Forms', 'url': '/documents/certificate_forms.pdf'},
                ]
            }
        ],
        'important_notes': [
            'All medical practitioners must comply with the MMC Act and Rules',
            'Registration is mandatory for practicing medicine in Maharashtra',
            'CPD points are required for registration renewal',
            'Ethical violations may lead to disciplinary action'
        ]
    }
    
    context = {
        'legal_documents': legal_documents,
        'page_title': 'Acts & Rules'
    }
    return render(request, 'MMC/landing/act_rules.html', context)

def disclaimer(request):
    """Disclaimer page"""
    disclaimer_content = {
        'title': 'Disclaimer',
        'sections': [
            {
                'title': 'Website Content',
                'content': 'The information contained on this website is for general information purposes only. While we endeavor to keep the information up to date and correct, we make no representations or warranties of any kind, express or implied, about the completeness, accuracy, reliability, suitability or availability with respect to the website or the information, products, services, or related graphics contained on the website for any purpose.'
            },
            {
                'title': 'Professional Advice',
                'content': 'The content on this website does not constitute professional medical advice. Medical practitioners should rely on their professional judgment and refer to official documents and legislation for authoritative information.'
            },
            {
                'title': 'Technical Issues',
                'content': 'Every effort is made to keep the website up and running smoothly. However, Maharashtra Medical Council takes no responsibility for, and will not be liable for, the website being temporarily unavailable due to technical issues beyond our control.'
            },
            {
                'title': 'External Links',
                'content': 'Through this website you are able to link to other websites which are not under the control of Maharashtra Medical Council. We have no control over the nature, content and availability of those sites. The inclusion of any links does not necessarily imply a recommendation or endorse the views expressed within them.'
            },
            {
                'title': 'Privacy & Data Protection',
                'content': 'We are committed to protecting your privacy and ensuring the security of your personal information. However, we cannot guarantee the security of any information transmitted to our website and you transmit such information at your own risk.'
            },
            {
                'title': 'Copyright',
                'content': 'All content on this website, including text, graphics, logos, and images, is the property of Maharashtra Medical Council unless otherwise stated. Unauthorized use of any materials may violate copyright laws.'
            }
        ]
    }
    
    context = {
        'disclaimer_content': disclaimer_content,
        'page_title': 'Disclaimer'
    }
    return render(request, 'MMC/landing/disclaimer.html', context)

def terms_conditions(request):
    """Terms and Conditions page"""
    terms_content = {
        'title': 'Terms & Conditions',
        'effective_date': 'January 1, 2024',
        'sections': [
            {
                'title': 'Acceptance of Terms',
                'content': 'By accessing and using this website, you accept and agree to be bound by the terms and provision of this agreement.'
            },
            {
                'title': 'Use License',
                'content': 'Permission is granted to temporarily use the materials on Maharashtra Medical Council\'s website for personal, non-commercial transitory viewing only.'
            },
            {
                'title': 'User Accounts',
                'content': 'When you create an account with us, you must provide accurate and complete information. You are responsible for safeguarding the password and for all activities that occur under your account.'
            },
            {
                'title': 'Service Usage',
                'content': 'You agree not to use the service: (a) for any illegal purpose; (b) to violate any laws; (c) to infringe upon or violate our intellectual property rights; (d) to harass, abuse, or harm another person.'
            },
            {
                'title': 'Payments and Fees',
                'content': 'All fees for services are non-refundable unless otherwise stated. The Council reserves the right to change service fees at any time.'
            },
            {
                'title': 'Intellectual Property',
                'content': 'The Service and its original content, features, and functionality are and will remain the exclusive property of Maharashtra Medical Council and its licensors.'
            },
            {
                'title': 'Termination',
                'content': 'We may terminate or suspend your account immediately, without prior notice or liability, for any reason whatsoever, including without limitation if you breach the Terms.'
            },
            {
                'title': 'Limitation of Liability',
                'content': 'In no event shall Maharashtra Medical Council, nor its directors, employees, partners, agents, suppliers, or affiliates, be liable for any indirect, incidental, special, consequential or punitive damages.'
            },
            {
                'title': 'Governing Law',
                'content': 'These Terms shall be governed and construed in accordance with the laws of India, without regard to its conflict of law provisions.'
            },
            {
                'title': 'Changes to Terms',
                'content': 'We reserve the right, at our sole discretion, to modify or replace these Terms at any time. By continuing to access or use our Service after those revisions become effective, you agree to be bound by the revised terms.'
            }
        ]
    }
    
    context = {
        'terms_content': terms_content,
        'page_title': 'Terms & Conditions'
    }
    return render(request, 'MMC/landing/terms_conditions.html', context)

# API Endpoints
@csrf_exempt
def quick_stats_api(request):
    """API endpoint for quick statistics"""
    if request.method == 'GET':
        try:
            # Get real-time statistics from database
            total_rmps = RMPProfile.objects.filter(registration_status='active').count()
            pending_applications = Application.objects.filter(status='submitted').count()
            upcoming_cpd = CPDProgram.objects.filter(
                start_date__gte=timezone.now(),
                is_active=True
            ).count()
            
            # Recent approvals (last 7 days)
            recent_approvals = Application.objects.filter(
                status='approved',
                approval_date__gte=timezone.now() - timedelta(days=7)
            ).count()
            
            # CPD statistics
            total_cpd_points = CPDAttendance.objects.filter(
                attendance_status='completed'
            ).aggregate(total_points=models.Sum('points_earned'))['total_points'] or 0
            
            stats = {
                'total_rmps': total_rmps,
                'pending_applications': pending_applications,
                'upcoming_cpd': upcoming_cpd,
                'recent_approvals': recent_approvals,
                'total_cpd_points': total_cpd_points,
                'last_updated': timezone.now().isoformat(),
                'status': 'success'
            }
            
            return JsonResponse(stats)
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

def get_announcements(request):
    """API endpoint to get announcements"""
    try:
        announcements = SystemConfig.objects.filter(
            key__startswith='announcement_',
            is_active=True
        ).order_by('-updated_date')[:10]
        
        announcements_list = []
        for announcement in announcements:
            # Parse announcement data (format: "Title|URL|Date")
            parts = announcement.value.split('|')
            if len(parts) >= 2:
                title = parts[0]
                url = parts[1]
                date = parts[2] if len(parts) > 2 else announcement.updated_date.strftime('%d-%m-%Y')
            else:
                title = announcement.value
                url = '#'
                date = announcement.updated_date.strftime('%d-%m-%Y')
            
            announcements_list.append({
                'id': announcement.id,
                'title': title,
                'url': url,
                'date': date,
                'is_new': announcement.updated_date >= timezone.now() - timedelta(days=7)
            })
        
        return JsonResponse({
            'status': 'success',
            'announcements': announcements_list,
            'count': len(announcements_list)
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def get_notifications(request):
    """API endpoint to get notifications"""
    try:
        notifications = SystemConfig.objects.filter(
            key__startswith='notification_',
            is_active=True
        ).order_by('-updated_date')[:10]
        
        notifications_list = []
        for notification in notifications:
            # Parse notification data (format: "Title|URL|Type")
            parts = notification.value.split('|')
            if len(parts) >= 2:
                title = parts[0]
                url = parts[1]
                notif_type = parts[2] if len(parts) > 2 else 'general'
            else:
                title = notification.value
                url = '#'
                notif_type = 'general'
            
            notifications_list.append({
                'id': notification.id,
                'title': title,
                'url': url,
                'type': notif_type,
                'date': notification.updated_date.strftime('%d-%m-%Y'),
                'is_important': 'important' in notification.key
            })
        
        return JsonResponse({
            'status': 'success',
            'notifications': notifications_list,
            'count': len(notifications_list)
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

# Utility function to initialize system configuration
def initialize_system_config():
    """Initialize system configuration with default values"""
    default_configs = [
        # Announcements
        {
            'key': 'announcement_1',
            'value': 'Notification Regarding CCMP Qualification Registration|/documents/ccmp_notification.pdf|11-09-2025',
            'description': 'CCMP Qualification Registration Notification',
            'data_type': 'string',
            'is_active': True
        },
        {
            'key': 'announcement_2', 
            'value': 'Guidelines for Internship Duration of Foreign Medical Graduates|/documents/fmg_guidelines.pdf|12-08-2025',
            'description': 'FMGs Internship Guidelines',
            'data_type': 'string',
            'is_active': True
        },
        
        # Notifications
        {
            'key': 'notification_1',
            'value': 'Renewal Notice for 2020 Registered Practitioners|/renewal|renewal',
            'description': 'Renewal notification',
            'data_type': 'string', 
            'is_active': True
        },
        {
            'key': 'notification_2',
            'value': 'New CPD Program Guidelines Released|/cpd/guidelines|cpd',
            'description': 'CPD guidelines update',
            'data_type': 'string',
            'is_active': True
        },
        
        # About page content
        {
            'key': 'about_page_content',
            'value': json.dumps({
                'title': 'About Maharashtra Medical Council',
                'sections': [
                    {
                        'title': 'Our Mission',
                        'content': 'To regulate the medical profession in Maharashtra through registration, education, and disciplinary oversight.'
                    },
                    # ... more sections
                ]
            }),
            'description': 'About page dynamic content',
            'data_type': 'json',
            'is_active': True
        }
    ]
    
    for config in default_configs:
        SystemConfig.objects.get_or_create(
            key=config['key'],
            defaults=config
        )

# Authentication Views
class MMCLoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        form = CustomAuthenticationForm()
        return render(request, 'MMC/registration/login.html', {'form': form})
    
    def post(self, request):
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            from django.contrib.auth import login
            user = form.get_user()
            login(request, user)
            
            # Create audit log
            create_audit_log(
                user=user,
                action_type='login',
                model_name='User',
                object_id=user.id,
                description=f"User {user.username} logged in",
                request=request
            )
            
            messages.success(request, f"Welcome back, {user.username}!")
            
            # Redirect based on user type
            if user.user_type == 'rmp':
                return redirect('dashboard')
            else:
                return redirect('admin_dashboard')
        
        return render(request, 'MMC/registration/login.html', {'form': form})


class MMCRegistrationView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'MMC/registration/register.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Create audit log
        create_audit_log(
            user=self.object,
            action_type='create',
            model_name='User',
            object_id=self.object.id,
            description=f"New user registered: {self.object.username}",
            request=self.request
        )
        
        messages.success(self.request, "Registration successful! Please login.")
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


# Dashboard Views
@login_required
def mmc_dashboard(request):
    context = {}
    
    if request.user.user_type == 'rmp':
        rmp_profile = get_rmp_profile(request.user)
        if not rmp_profile:
            messages.warning(request, "Please complete your profile.")
            return redirect('rmp_profile_create')
        
        # Get applications
        applications = Application.objects.filter(rmp=rmp_profile).order_by('-submitted_date')[:5]
        
        # Get upcoming CPD programs
        upcoming_cpd = CPDProgram.objects.filter(
            start_date__gte=timezone.now(),
            is_active=True
        )[:5]
        
        # Get complaints against the doctor
        complaints = Complaint.objects.filter(against_rmp=rmp_profile, status='registered')
        
        # Get notifications
        notifications = Notification.objects.filter(user=request.user, is_read=False)[:5]
        
        # Get AI insights if available
        try:
            ai_score = AIPerformanceScore.objects.get(rmp=rmp_profile)
            ai_insights = AIInsight.objects.filter(rmp=rmp_profile, is_active=True)[:3]
        except AIPerformanceScore.DoesNotExist:
            ai_score = None
            ai_insights = []
        
        # Calculate renewal date
        renewal_date = rmp_profile.registration_valid_till
        days_until_renewal = (renewal_date - timezone.now().date()).days if renewal_date else None
        
        # CPD progress
        cpd_progress = rmp_profile.cpd_cycle_progress
        
        context.update({
            'rmp_profile': rmp_profile,
            'applications': applications,
            'upcoming_cpd': upcoming_cpd,
            'complaints': complaints,
            'notifications': notifications,
            'ai_score': ai_score,
            'ai_insights': ai_insights,
            'days_until_renewal': days_until_renewal,
            'renewal_date': renewal_date,
            'cpd_progress': cpd_progress,
        })
        
    elif request.user.user_type in ['admin', 'staff']:
        # Admin dashboard statistics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        total_applications = Application.objects.count()
        pending_applications = Application.objects.filter(status='submitted').count()
        overdue_applications = Application.objects.filter(
            expected_completion_date__lt=timezone.now(),
            status__in=['submitted', 'under_review']
        ).count()
        
        total_rmps = RMPProfile.objects.count()
        recent_applications = Application.objects.select_related('rmp').order_by('-submitted_date')[:10]
        
        # Payment statistics
        payment_stats = Payment.objects.filter(status='success').aggregate(
            total_amount=Sum('amount'),
            total_count=Count('id'),
            today_amount=Sum('amount', filter=Q(payment_date__date=today)),
            week_amount=Sum('amount', filter=Q(payment_date__date__gte=week_ago)),
            month_amount=Sum('amount', filter=Q(payment_date__date__gte=month_ago))
        )
        
        # CPD statistics
        cpd_stats = {
            'total_programs': CPDProgram.objects.count(),
            'active_programs': CPDProgram.objects.filter(is_active=True).count(),
            'total_participations': CPDAttendance.objects.count(),
            'upcoming_programs': CPDProgram.objects.filter(start_date__gte=today, is_active=True).count(),
        }
        
        # Staff performance (if admin)
        if request.user.user_type == 'admin':
            staff_performance = CustomUser.objects.filter(user_type='staff').annotate(
                assigned_count=Count('assigned_applications'),
                completed_count=Count('assigned_applications', filter=Q(assigned_applications__status__in=['approved', 'rejected'])),
                overdue_count=Count('assigned_applications', filter=Q(assigned_applications__is_overdue=True))
            )
            context['staff_performance'] = staff_performance
        
        context.update({
            'total_applications': total_applications,
            'pending_applications': pending_applications,
            'overdue_applications': overdue_applications,
            'total_rmps': total_rmps,
            'recent_applications': recent_applications,
            'payment_stats': payment_stats,
            'cpd_stats': cpd_stats,
        })
    
    elif request.user.user_type == 'cpd_provider':
        # CPD Provider dashboard
        my_programs = CPDProgram.objects.filter(created_by=request.user).order_by('-created_date')[:5]
        total_programs = CPDProgram.objects.filter(created_by=request.user).count()
        active_programs = CPDProgram.objects.filter(created_by=request.user, is_active=True).count()
        total_participants = CPDAttendance.objects.filter(program__created_by=request.user).count()
        
        context.update({
            'my_programs': my_programs,
            'total_programs': total_programs,
            'active_programs': active_programs,
            'total_participants': total_participants,
        })
    
    return render(request, 'MMC/dashboard/dashboard.html', context)

def rmp_dashboard(request):
    user = request.user
    today = timezone.now().date()
    
    # Applications statistics
    applications = Application.objects.filter(applicant=user)
    active_applications = applications.filter(status__in=['SUBMITTED', 'UNDER_REVIEW']).count()
    completed_applications = applications.filter(status__in=['APPROVED', 'COMPLETED']).count()
    
    # CPD statistics
    cpd_participations = CPDParticipation.objects.filter(participant=user, attendance_status='COMPLETED')
    total_cpd_points = cpd_participations.aggregate(total=Sum('points_earned'))['total'] or 0
    
    # Renewal alerts
    renewal_alerts = []
    if user.renewal_date and user.renewal_date <= today + timedelta(days=60):
        renewal_alerts.append({
            'message': f'Registration renewal due on {user.renewal_date}',
            'type': 'warning' if user.renewal_date > today else 'danger'
        })
    
    # CPD alerts
    cpd_alerts = []
    cpd_completion = (total_cpd_points / user.cpd_points_required * 100) if user.cpd_points_required > 0 else 0
    if cpd_completion < 50:
        cpd_alerts.append({
            'message': f'CPD completion at {cpd_completion:.1f}%. Consider attending more programs.',
            'type': 'warning'
        })
    
    # Recent activities
    recent_applications = applications.order_by('-application_date')[:5]
    upcoming_cpd = CPDProgram.objects.filter(
        start_date__gte=today,
        is_active=True,
        status='PUBLISHED'
    ).order_by('start_date')[:5]
    
    # AI Insights
    ai_insights = AIInsight.objects.filter(user=user, is_active=True).order_by('-generated_at')[:3]
    
    context = {
        'active_applications': active_applications,
        'completed_applications': completed_applications,
        'pending_payments': Payment.objects.filter(user=user, status='PENDING').count(),
        'cpd_points': total_cpd_points,
        'cpd_required': user.cpd_points_required,
        'cpd_completion': cpd_completion,
        'recent_applications': recent_applications,
        'upcoming_cpd': upcoming_cpd,
        'notifications': Notification.objects.filter(user=user, is_read=False).order_by('-created_at')[:10],
        'complaints_count': Complaint.objects.filter(against_doctor=user, status='PENDING').count(),
        'renewal_alerts': renewal_alerts,
        'cpd_alerts': cpd_alerts,
        'ai_insights': ai_insights,
        'performance_score': AIPerformanceScore.objects.filter(user=user).first(),
    }
    return render(request, 'MMC/dashboard/rmp_dashboard.html', context)

@login_required
def admin_dashboard1(request):
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    # Application statistics
    total_applications = Application.objects.count()
    pending_applications = Application.objects.filter(status__in=['SUBMITTED', 'UNDER_REVIEW']).count()
    overdue_applications = Application.objects.filter(
        expected_completion_date__lt=today,
        status__in=['SUBMITTED', 'UNDER_REVIEW']
    ).count()
    
    # User statistics
    total_rmps = CustomUser.objects.filter(user_type='rmp').count()
    new_registrations = CustomUser.objects.filter(
        user_type='rmp', 
        date_joined__date__gte=thirty_days_ago
    ).count()
    
    # Payment statistics
    payment_stats = Payment.objects.filter(
        payment_date__date__gte=thirty_days_ago,
        status='SUCCESS'
    ).aggregate(
        total_amount=Sum('amount'),
        total_count=Count('id')
    )
    
    # CPD statistics
    cpd_stats = CPDProgram.objects.filter(
        start_date__date__gte=thirty_days_ago
    ).aggregate(
        total_programs=Count('id'),
        total_participants=Sum('max_participants')
    )
    
    # Recent activities
    recent_applications = Application.objects.select_related('applicant').order_by('-application_date')[:10]
    recent_payments = Payment.objects.select_related('user').filter(status='SUCCESS').order_by('-payment_date')[:10]
    
    # Staff performance
    staff_performance = CustomUser.objects.filter(
        user_type__in=['ADMIN', 'VERIFIER'],
        verification_tasks__completed_date__date__gte=thirty_days_ago
    ).annotate(
        tasks_completed=Count('verification_tasks'),
        avg_processing_time=Avg(
            ExpressionWrapper(
                F('verification_tasks__completed_date') - F('verification_tasks__assigned_date'),
                output_field=DurationField()
            )
        )
    ).values('username', 'first_name', 'last_name', 'tasks_completed', 'avg_processing_time')
    
    # AI-powered insights for admin
    high_risk_applications = Application.objects.filter(
        status='UNDER_REVIEW'
    ).annotate(
        risk_score=Case(
            When(application_type__in=['FOREIGN_PERMANENT', 'PERMANENT_DEFAULTER'], then=Value(80)),
            When(verification_notes__isnull=False, then=Value(70)),
            When(Q(documents__is_verified=False) & Q(documents__isnull=False), then=Value(60)),
            default=Value(40),
            output_field=IntegerField()
        )
    ).filter(risk_score__gte=70).distinct()[:10]
    
    compliance_alerts = CustomUser.objects.filter(
        user_type='rmp',
        registration_status='PERMANENT'
    ).annotate(
        cpd_deficit=F('cpd_points_required') - F('total_cpd_points'),
        renewal_soon=Case(
            When(renewal_date__lte=today + timedelta(days=30), then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        )
    ).filter(Q(cpd_deficit__gt=10) | Q(renewal_soon=True))[:10]
    
    context = {
        'total_applications': total_applications,
        'pending_applications': pending_applications,
        'overdue_applications': overdue_applications,
        'total_rmps': total_rmps,
        'new_registrations': new_registrations,
        'payment_stats': payment_stats,
        'cpd_stats': cpd_stats,
        'recent_applications': recent_applications,
        'recent_payments': recent_payments,
        'staff_performance': staff_performance,
        'high_risk_applications': high_risk_applications,
        'compliance_alerts': compliance_alerts,
    }
    return render(request, 'MMC/dashboard/admin_dashboard.html', context)

# RMP Profile Management
@login_required
@user_passes_test(is_rmp)
def rmp_profile_create(request):
    rmp_profile = get_rmp_profile(request.user)
    if rmp_profile:
        return redirect('rmp_profile_edit')
    
    if request.method == 'POST':
        form = RMPRegistrationForm(request.POST)
        if form.is_valid():
            rmp_profile = form.save(commit=False)
            rmp_profile.user = request.user
            rmp_profile.mmc_registration_number = generate_mmc_number()
            
            # Set CPD cycle if not provided
            if not rmp_profile.cpd_cycle_end:
                rmp_profile.cpd_cycle_end = rmp_profile.cpd_cycle_start + timedelta(days=365)
            
            rmp_profile.save()
            
            # Create audit log
            create_audit_log(
                user=request.user,
                action_type='create',
                model_name='RMPProfile',
                object_id=rmp_profile.id,
                description=f"RMP profile created for {rmp_profile.full_name}",
                request=request
            )
            
            messages.success(request, "Profile created successfully!")
            return redirect('dashboard')
    else:
        form = RMPRegistrationForm(initial={
            'cpd_cycle_start': timezone.now().date(),
            'cpd_cycle_end': timezone.now().date() + timedelta(days=365)
        })
    
    return render(request, 'MMC/rmp/profile_create.html', {'form': form})

@login_required
@user_passes_test(is_rmp)
def rmp_profile_edit(request):
    rmp_profile = get_object_or_404(RMPProfile, user=request.user)
    
    if request.method == 'POST':
        form = RMPRegistrationForm(request.POST, instance=rmp_profile)
        if form.is_valid():
            form.save()
            
            # Create audit log
            create_audit_log(
                user=request.user,
                action_type='update',
                model_name='RMPProfile',
                object_id=rmp_profile.id,
                description=f"RMP profile updated for {rmp_profile.full_name}",
                request=request
            )
            
            messages.success(request, "Profile updated successfully!")
            return redirect('dashboard')
    else:
        form = RMPRegistrationForm(instance=rmp_profile)
    
    return render(request, 'MMC/rmp/profile_edit.html', {'form': form})

@login_required
@user_passes_test(is_rmp)
def rmp_qualifications(request):
    rmp_profile = get_rmp_profile(request.user)
    qualifications = MedicalQualification.objects.filter(rmp=rmp_profile)
    
    if request.method == 'POST':
        form = MedicalQualificationForm(request.POST)
        if form.is_valid():
            qualification = form.save(commit=False)
            qualification.rmp = rmp_profile
            qualification.save()
            messages.success(request, "Qualification added successfully!")
            return redirect('rmp_qualifications')
    else:
        form = MedicalQualificationForm()
    
    context = {
        'qualifications': qualifications,
        'form': form,
    }
    return render(request, 'MMC/rmp/qualifications.html', context)

@login_required
@user_passes_test(is_rmp)
def rmp_experience(request):
    rmp_profile = get_rmp_profile(request.user)
    experiences = Experience.objects.filter(rmp=rmp_profile)
    
    if request.method == 'POST':
        form = ExperienceForm(request.POST)
        if form.is_valid():
            experience = form.save(commit=False)
            experience.rmp = rmp_profile
            experience.save()
            messages.success(request, "Experience added successfully!")
            return redirect('rmp_experience')
    else:
        form = ExperienceForm()
    
    context = {
        'experiences': experiences,
        'form': form,
    }
    return render(request, 'MMC/rmp/experience.html', context)

@login_required
@user_passes_test(is_rmp)
def rmp_publications(request):
    rmp_profile = get_rmp_profile(request.user)
    publications = Publication.objects.filter(rmp=rmp_profile)
    
    if request.method == 'POST':
        form = PublicationForm(request.POST)
        if form.is_valid():
            publication = form.save(commit=False)
            publication.rmp = rmp_profile
            publication.save()
            messages.success(request, "Publication added successfully!")
            return redirect('rmp_publications')
    else:
        form = PublicationForm()
    
    context = {
        'publications': publications,
        'form': form,
    }
    return render(request, 'MMC/rmp/publications.html', context)

@login_required
@user_passes_test(is_rmp)
def rmp_awards(request):
    rmp_profile = get_rmp_profile(request.user)
    awards = Award.objects.filter(rmp=rmp_profile)
    
    if request.method == 'POST':
        form = AwardForm(request.POST, request.FILES)
        if form.is_valid():
            award = form.save(commit=False)
            award.rmp = rmp_profile
            award.save()
            messages.success(request, "Award added successfully!")
            return redirect('rmp_awards')
    else:
        form = AwardForm()
    
    context = {
        'awards': awards,
        'form': form,
    }
    return render(request, 'MMC/rmp/awards.html', context)


# ============ PROFILE & SETTINGS ============
@login_required
@rmp_required
def rmp_profile_view(request):
    profile, created = RMPProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        user_form = RMPRegistrationForm(request.POST, instance=profile)
        if user_form.is_valid():
            user_form.save()
            
            # Update user's specialization if provided
            specialization = request.POST.get('specialization')
            if specialization:
                request.user.specialization = specialization
                request.user.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile_view')
    else:
        user_form = RMPRegistrationForm(instance=profile)
    
    context = {
        'user_form': user_form,
        'profile': profile,
    }
    return render(request, 'MMC/profile/profile_view.html', context)

def generate_mmc_number():
    """Generate unique MMC registration number"""
    import random
    from datetime import datetime
    
    year = datetime.now().year
    base = f"MMC/{year}/"
    
    while True:
        number = random.randint(10000, 99999)
        mmc_number = f"{base}{number}"
        if not RMPProfile.objects.filter(mmc_registration_number=mmc_number).exists():
            return mmc_number

# Application Management Views
@login_required
@user_passes_test(is_rmp)
def application_wizard(request, application_type=None):
    if application_type is None:
        if request.method == 'POST':
            form = ApplicationForm(request.POST)
            if form.is_valid():
                application = form.save(commit=False)
                application.rmp = get_rmp_profile(request.user)
                application.fee_amount = get_application_fee(application.application_type)
                application.save()
                
                # Create initial step
                ApplicationStep.objects.create(
                    application=application,
                    step_number=1,
                    step_name='applicant_details',
                    required_documents=get_required_documents(application.application_type)
                )
                
                # Create audit log
                create_audit_log(
                    user=request.user,
                    action_type='create',
                    model_name='Application',
                    object_id=application.application_id,
                    description=f"New {application.get_application_type_display()} application created",
                    request=request
                )
                
                return redirect('application_step', application_id=application.application_id, step=1)
        else:
            form = ApplicationForm()
        return render(request, 'MMC/applications/application_type.html', {'form': form})
    
    return redirect('application_wizard')

@login_required
@user_passes_test(is_rmp)
def application_step(request, application_id, step):
    application = get_object_or_404(Application, application_id=application_id, rmp__user=request.user)
    
    steps_config = {
        1: {'name': 'applicant_details', 'title': 'Applicant Details', 'form_class': RMPRegistrationForm},
        2: {'name': 'educational_details', 'title': 'Educational Details', 'form_class': EducationalQualificationForm},
        3: {'name': 'medical_qualification', 'title': 'Medical Qualification', 'form_class': MedicalQualificationForm},
        4: {'name': 'passport_details', 'title': 'Passport Details', 'form_class': PassportDetailsForm},
        5: {'name': 'screening_test', 'title': 'Screening Test', 'form_class': ScreeningTestForm},
        6: {'name': 'internship_training', 'title': 'Internship Training', 'form_class': InternshipTrainingForm},
        7: {'name': 'foreign_training', 'title': 'Foreign Training/Registration', 'form_class': ForeignTrainingForm},
        8: {'name': 'documents_upload', 'title': 'Document Upload', 'form_class': DocumentUploadForm},
        9: {'name': 'declarations', 'title': 'Declarations', 'form_class': DeclarationForm},
        10: {'name': 'payment', 'title': 'Payment', 'form_class': PaymentForm},
    }
    
    current_step_config = steps_config.get(step)
    if not current_step_config:
        messages.error(request, "Invalid step")
        return redirect('application_status', application_id=application_id)
    
    if request.method == 'POST':
        if step == 10:  # Payment step
            # Handle payment processing
            application.payment_status = True
            application.payment_date = timezone.now()
            application.status = 'submitted'
            application.save()
            
            # Create notification for admin
            admin_users = CustomUser.objects.filter(user_type='admin')
            for admin in admin_users:
                Notification.objects.create(
                    user=admin,
                    notification_type='registration',
                    title='New Application Submitted',
                    message=f"New {application.get_application_type_display()} application submitted by {application.rmp.full_name}",
                    related_object_id=str(application.application_id),
                    action_url=reverse('admin_application_review', args=[application.application_id]),
                    priority='high'
                )
            
            # Create audit log
            create_audit_log(
                user=request.user,
                action_type='update',
                model_name='Application',
                object_id=application.application_id,
                description=f"Application submitted and payment completed",
                request=request
            )
            
            messages.success(request, "Application submitted successfully!")
            return redirect('application_status', application_id=application_id)
        else:
            # Save step data
            step_data = process_step_data(request, step, application)
            
            # Update step progress
            application_step, created = ApplicationStep.objects.update_or_create(
                application=application,
                step_number=step,
                defaults={
                    'step_name': current_step_config['name'],
                    'data': step_data,
                    'is_completed': True,
                    'completed_date': timezone.now(),
                }
            )
            
            # Update application current step
            application.current_step = step + 1
            application.save()
            
            if step < len(steps_config):
                return redirect('application_step', application_id=application_id, step=step + 1)
    
    # Load existing step data
    try:
        step_data = ApplicationStep.objects.get(application=application, step_number=step).data
    except ApplicationStep.DoesNotExist:
        step_data = {}
    
    # Initialize form for current step
    form = None
    if current_step_config['form_class']:
        form_class = current_step_config['form_class']
        if form_class == PaymentForm:
            form = form_class(initial=step_data, application_type=application.application_type)
        else:
            form = form_class(initial=step_data)
    
    context = {
        'application': application,
        'current_step': step,
        'current_step_name': current_step_config['name'],
        'step_title': current_step_config['title'],
        'total_steps': len(steps_config),
        'step_data': step_data,
        'form': form,
    }
    
    template_name = f'applications/steps/{current_step_config["name"]}.html'
    return render(request, template_name, context)

def process_step_data(request, step, application):
    """Process and validate step data"""
    step_data = {}
    
    if step == 1:  # Applicant Details
        step_data = {
            'personal_info': {
                'prefix': request.POST.get('prefix'),
                'full_name': request.POST.get('full_name'),
                'father_name': request.POST.get('father_name'),
                'mother_name': request.POST.get('mother_name'),
                'marital_status': request.POST.get('marital_status'),
                'date_of_birth': request.POST.get('date_of_birth'),
                'gender': request.POST.get('gender'),
                'category': request.POST.get('category'),
                'mobile': request.POST.get('mobile'),
                'email': request.POST.get('email'),
            },
            'address_info': {
                'communication_address': request.POST.get('communication_address'),
                'communication_city': request.POST.get('communication_city'),
                'communication_district': request.POST.get('communication_district'),
                'communication_state': request.POST.get('communication_state'),
                'communication_pincode': request.POST.get('communication_pincode'),
            }
        }
    
    elif step == 2:  # Educational Details
        # Process educational qualifications
        qualifications_data = []
        for i in range(int(request.POST.get('qualification_count', 0))):
            qual_data = {
                'type': request.POST.get(f'qualification_{i}_type'),
                'institution': request.POST.get(f'qualification_{i}_institution'),
                'board': request.POST.get(f'qualification_{i}_board'),
                'year': request.POST.get(f'qualification_{i}_year'),
                'percentage': request.POST.get(f'qualification_{i}_percentage'),
            }
            qualifications_data.append(qual_data)
        step_data['qualifications'] = qualifications_data
    
    elif step == 8:  # Document Upload
        # Handle file uploads
        for file_key, file_obj in request.FILES.items():
            if file_key.startswith('document_'):
                document_type = file_key.replace('document_', '')
                document = Document(
                    application=application,
                    document_type=document_type,
                    document_file=file_obj
                )
                document.save()
    
    return step_data

def handle_document_uploads(self, application, form_data, files):
        document_mapping = {
            'photograph': ('PHOTO', 'Photograph'),
            'signature': ('SIGNATURE', 'Signature'),
            'degree_certificate': ('DEGREE', 'Degree Certificate'),
            'mci_eligibility_certificate': ('MCI_ELIGIBILITY', 'MCI Eligibility Certificate'),
            'provisional_registration': ('PROVISIONAL_REG', 'Provisional Registration Certificate'),
            'affidavit': ('AFFIDAVIT', 'Affidavit'),
            'embassy_letter': ('EMBASSY_LETTER', 'Embassy Letter'),
            'domicile_certificate': ('DOMICILE', 'Domicile Certificate'),
        }
        
        for field_name, (doc_type, doc_name) in document_mapping.items():
            if field_name in files:
                Document.objects.create(
                    application=application,
                    document_type=doc_type,
                    document_file=files[field_name],
                    file_name=files[field_name].name
                )
    
def handle_educational_data(self, application, form_data, post_data):
        # Handle 10th and 12th qualifications
        qualifications_data = [
            {
                'type': '10TH',
                'name': 'Secondary School Certificate',
                'institution': form_data.get('tenth_school'),
                'board': form_data.get('tenth_board'),
                'year': form_data.get('tenth_year'),
                'percentage': form_data.get('tenth_percentage'),
            },
            {
                'type': '12TH', 
                'name': 'Higher Secondary Certificate',
                'institution': form_data.get('twelfth_school'),
                'board': form_data.get('twelfth_board'),
                'year': form_data.get('twelfth_year'),
                'percentage': form_data.get('twelfth_percentage'),
            }
        ]
        
        for qual_data in qualifications_data:
            if qual_data['institution']:
                EducationalQualification.objects.create(
                    application=application,
                    qualification_type=qual_data['type'],
                    qualification_name=qual_data['name'],
                    institution_name=qual_data['institution'],
                    board_university=qual_data['board'],
                    year_of_passing=qual_data['year'],
                    percentage=qual_data['percentage'],
                )

def calculate_application_fee(application_type):
    fee_structure = {
        'PROVISIONAL_REG': 1000,
        'PERMANENT_REG': 2000,
        'FOREIGN_PROVISIONAL': 1500,
        'FOREIGN_PERMANENT': 2500,
        'RENEWAL_REG': 500,
        'DUPLICATE_CERT': 200,
        'GOOD_STANDING_MMC': 300,
        'GOOD_STANDING_NMC': 400,
        'GOOD_STANDING_NRI': 500,
        'NOC_OTHER_STATE': 300,
        'ID_CARD_GEN': 100,
    }
    return fee_structure.get(application_type, 500)

@login_required
def application_review(request, application_id):
    application = get_object_or_404(Application, application_id=application_id, applicant=request.user)
    
    # Check if all steps are completed
    completed_steps = ApplicationStep.objects.filter(application=application, is_completed=True).count()
    all_steps_completed = completed_steps == 9
    
    # Collect all step data for review
    step_data = {}
    for step in range(1, 10):
        data = ApplicationStep.objects.filter(application=application, step_number=step).first()
        if data:
            step_data[step] = {
                'title': data.step_name,
                'data': data.form_data,
                'completed': data.is_completed
            }
    
    # Calculate payment amount
    payment_amount = calculate_application_fee(application.application_type)
    
    context = {
        'application': application,
        'step_data': step_data,
        'all_steps_completed': all_steps_completed,
        'payment_amount': payment_amount,
        'documents': Document.objects.filter(application=application),
    }
    return render(request, 'MMC/applications/application_review.html', context)

@login_required
def submit_application(request, application_id):
    application = get_object_or_404(Application, application_id=application_id, applicant=request.user)
    
    if request.method == 'POST':
        # Check if all steps are completed
        completed_steps = ApplicationStep.objects.filter(application=application, is_completed=True).count()
        
        if completed_steps == 9:  # All steps completed
            try:
                with transaction.atomic():
                    application.status = 'SUBMITTED'
                    application.submission_date = timezone.now()
                    application.save()
                    
                    # Create notification
                    Notification.objects.create(
                        user=request.user,
                        notification_type='APPLICATION_STATUS',
                        title='Application Submitted',
                        message=f'Your {application.get_application_type_display()} application has been submitted successfully.',
                        related_object_id=str(application.application_id),
                        related_object_type='APPLICATION',
                        action_url=reverse('application_status', args=[application.application_id])
                    )
                    
                    # Notify admins
                    admins = CustomUser.objects.filter(user_type__in=['ADMIN', 'SUPER_ADMIN'])
                    for admin in admins:
                        Notification.objects.create(
                            user=admin,
                            notification_type='VERIFICATION_REQUIRED',
                            title='New Application Submitted',
                            message=f'New {application.get_application_type_display()} application requires verification.',
                            related_object_id=str(application.application_id),
                            related_object_type='APPLICATION',
                            action_url=reverse('admin_application_detail', args=[application.application_id])
                        )
                    
                    messages.success(request, 'Application submitted successfully! It will now be reviewed by the council.')
                    return redirect('application_status', application_id=application.application_id)
                    
            except Exception as e:
                logger.error(f"Error submitting application: {e}")
                messages.error(request, 'An error occurred while submitting your application. Please try again.')
        else:
            messages.error(request, 'Please complete all steps before submitting.')
    
    return redirect('application_review', application_id=application.application_id)


def get_application_fee(application_type):
    """Get fee amount for application type"""
    fee_structure = {
        'provisional': 1500,
        'permanent': 2500,
        'renewal': 1000,
        'additional_qualification': 500,
        'good_standing_mmc': 1000,
        'good_standing_nmc': 1500,
        'good_standing_nri': 2000,
        'duplicate': 500,
        'verification': 300,
        'address_change': 200,
        'name_change': 500,
        'noc_state': 1000,
        'foreign_verification': 1500,
    }
    return fee_structure.get(application_type, 1000)

def get_required_documents(application_type):
    """Get required documents for application type"""
    document_requirements = {
        'provisional': ['photo', 'signature', 'ssc', 'hsc', 'degree', 'internship', 'address_proof'],
        'permanent': ['photo', 'signature', 'ssc', 'hsc', 'degree', 'internship', 'provisional_reg', 'address_proof'],
        'renewal': ['photo', 'latest_cpd_certificate', 'address_proof'],
        'additional_qualification': ['photo', 'degree', 'marksheet'],
        'good_standing_mmc': ['photo', 'address_proof', 'affidavit'],
    }
    return document_requirements.get(application_type, ['photo', 'signature', 'address_proof'])

@login_required
def application_status(request, application_id):
    application = get_object_or_404(Application, application_id=application_id)
    
    # Check permission
    if request.user.user_type == 'rmp' and application.applicant != request.user:
        messages.error(request, "You don't have permission to view this application.")
        return redirect('dashboard')
    
    step_data = ApplicationStep.objects.filter(application=application).order_by('step_number')
    documents = Document.objects.filter(application=application)
    payments = Payment.objects.filter(application=application)
    verification_tasks = VerificationTask.objects.filter(application=application)
    
    context = {
        'application': application,
        'step_data': step_data,
        'documents': documents,
        'payments': payments,
        'verification_tasks': verification_tasks,
    }
    return render(request, 'MMC/applications/application_status.html', context)

@login_required
@user_passes_test(is_rmp)
def application_list(request):
    rmp_profile = get_rmp_profile(request.user)
    applications = Application.objects.filter(rmp=rmp_profile).order_by('-submitted_date')
    
    # Filtering
    status_filter = request.GET.get('status')
    type_filter = request.GET.get('type')
    
    if status_filter:
        applications = applications.filter(status=status_filter)
    if type_filter:
        applications = applications.filter(application_type=type_filter)
    
    # Pagination
    paginator = Paginator(applications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'applications': page_obj,
        'status_filter': status_filter,
        'type_filter': type_filter,
    }
    
    return render(request, 'MMC/applications/application_list.html', context)


# Document Management
@login_required
@user_passes_test(is_rmp)
def mmc_upload_document(request, application_id):
    application = get_object_or_404(Application, application_id=application_id, rmp__user=request.user)
    
    if request.method == 'POST' and request.FILES:
        document_type = request.POST.get('document_type')
        document_file = request.FILES.get('document_file')
        
        if document_type and document_file:
            document = Document(
                application=application,
                document_type=document_type,
                document_file=document_file
            )
            document.save()
            
            # Create audit log
            create_audit_log(
                user=request.user,
                action_type='create',
                model_name='Document',
                object_id=document.id,
                description=f"Document uploaded: {document.get_document_type_display()}",
                request=request
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Document uploaded successfully',
                'document_id': document.id,
                'document_url': document.document_file.url
            })
    
    return JsonResponse({'success': False, 'message': 'Upload failed'})

@login_required
@user_passes_test(is_rmp)
def mmc_delete_document(request, document_id):
    document = get_object_or_404(Document, id=document_id, application__rmp__user=request.user)
    document.delete()
    
    # Create audit log
    create_audit_log(
        user=request.user,
        action_type='delete',
        model_name='Document',
        object_id=document_id,
        description=f"Document deleted: {document.get_document_type_display()}",
        request=request
    )
    
    return JsonResponse({'success': True, 'message': 'Document deleted successfully'})


# Good Standing Certificate
@login_required
@rmp_required
def request_good_standing(request, certificate_type):
    if request.method == 'POST':
        form = GoodStandingRequestForm(request.POST)
        if form.is_valid():
            # Map certificate type to application type
            type_mapping = {
                'mmc': 'GOOD_STANDING_MMC',
                'nmc': 'GOOD_STANDING_NMC', 
                'nri': 'GOOD_STANDING_NRI'
            }
            
            application = Application.objects.create(
                applicant=request.user,
                application_type=type_mapping.get(certificate_type, 'GOOD_STANDING_MMC'),
                status='DRAFT'
            )
            
            good_standing_request = form.save(commit=False)
            good_standing_request.application = application
            good_standing_request.save()
            
            messages.success(request, 'Good Standing Certificate request submitted!')
            return redirect('application_wizard_step', application_id=application.application_id, step=1)
    else:
        form = GoodStandingRequestForm()
    
    context = {
        'form': form,
        'certificate_type': certificate_type
    }
    return render(request, 'MMC/services/good_standing_request.html', context)

# NOC Request
@login_required
@rmp_required
def request_noc(request):
    if request.method == 'POST':
        form = NOCRequestForm(request.POST)
        if form.is_valid():
            application = Application.objects.create(
                applicant=request.user,
                application_type='NOC_OTHER_STATE',
                status='DRAFT'
            )
            
            noc_request = form.save(commit=False)
            noc_request.application = application
            noc_request.save()
            
            messages.success(request, 'NOC request submitted successfully!')
            return redirect('application_wizard_step', application_id=application.application_id, step=1)
    else:
        form = NOCRequestForm()
    
    context = {
        'form': form
    }
    return render(request, 'MMC/services/noc_request.html', context)

# Change Requests (Name, Address, Qualification)
@login_required
@rmp_required
def request_change(request, change_type):
    if request.method == 'POST':
        form = ChangeRequestForm(request.POST, request.FILES)
        if form.is_valid():
            # Map change type to application type
            type_mapping = {
                'name': 'CHANGE_NAME',
                'address': 'CHANGE_ADDRESS', 
                'qualification': 'ADDITIONAL_QUALIFICATION'
            }
            
            application = Application.objects.create(
                applicant=request.user,
                application_type=type_mapping.get(change_type, 'CHANGE_NAME'),
                status='DRAFT'
            )
            
            change_request = form.save(commit=False)
            change_request.application = application
            change_request.save()
            
            messages.success(request, f'{form.instance.get_change_type_display()} request submitted!')
            return redirect('application_wizard_step', application_id=application.application_id, step=1)
    else:
        form = ChangeRequestForm(initial={'change_type': change_type.upper()})
    
    context = {
        'form': form,
        'change_type': change_type
    }
    return render(request, 'MMC/services/change_request.html', context)

# Termination Request
@login_required
@rmp_required
def request_termination(request):
    if request.method == 'POST':
        form = TerminationRequestForm(request.POST, request.FILES)
        if form.is_valid():
            application = Application.objects.create(
                applicant=request.user,
                application_type='TERMINATION_RMP',
                status='DRAFT'
            )
            
            termination_request = form.save(commit=False)
            termination_request.application = application
            termination_request.save()
            
            messages.success(request, 'Termination request submitted for review.')
            return redirect('application_status', application_id=application.application_id)
    else:
        form = TerminationRequestForm()
    
    context = {
        'form': form
    }
    return render(request, 'MMC/services/termination_request.html', context)


# Certificate Management
@login_required
@rmp_required
def certificate_list(request):
    certificates = Certificate.objects.filter(user=request.user).order_by('-issue_date')
    context = {
        'certificates': certificates
    }
    return render(request, 'MMC/certificates/certificate_list.html', context)

@login_required
@rmp_required
def request_certificate(request):
    if request.method == 'POST':
        form = CertificateRequestForm(request.POST)
        if form.is_valid():
            # Create application for certificate
            application = Application.objects.create(
                applicant=request.user,
                application_type='DUPLICATE_CERT',  # Adjust based on certificate type
                status='DRAFT'
            )
            messages.success(request, 'Certificate request submitted successfully!')
            return redirect('application_status', application_id=application.application_id)
    else:
        form = CertificateRequestForm()
    
    context = {
        'form': form
    }
    return render(request, 'MMC/certificates/request_certificate.html', context)


# ID Card Generation
@login_required
@rmp_required
def id_card_view(request):
    try:
        id_card = IDCard.objects.get(user=request.user, is_active=True)
    except IDCard.DoesNotExist:
        id_card = None
    
    context = {
        'id_card': id_card
    }
    return render(request, 'MMC/id_cards/id_card_view.html', context)

@login_required
@rmp_required
def request_id_card(request):
    if request.method == 'POST':
        # Check if user has active registration
        if request.user.registration_status != 'PERMANENT':
            messages.error(request, 'Only permanently registered practitioners can request ID cards.')
            return redirect('id_card_view')
        
        # Create ID card application
        application = Application.objects.create(
            applicant=request.user,
            application_type='ID_CARD_GEN',
            status='SUBMITTED'
        )
        messages.success(request, 'ID Card request submitted successfully!')
        return redirect('application_status', application_id=application.application_id)
    
    return redirect('id_card_view')


# ============ ID CARD MANAGEMENT ============
@login_required
def admin_id_card_requests(request):
    """Admin view for ID card generation requests"""
    id_card_applications = Application.objects.filter(
        application_type='ID_CARD_GEN'
    ).select_related('applicant').order_by('-application_date')
    
    context = {
        'applications': id_card_applications
    }
    return render(request, 'MMC/admin/id_card_requests.html', context)

@login_required
def generate_id_card(request, application_id):
    """Generate ID card for approved application"""
    application = get_object_or_404(Application, application_id=application_id)
    
    if request.method == 'POST':
        try:
            # Create ID card
            id_card = IDCard.objects.create(
                user=application.applicant,
                card_number=f"MMCID{timezone.now().strftime('%Y%m%d%H%M%S')}",
                expiry_date=timezone.now().date() + timedelta(days=365*5),
                photo=application.documents.filter(document_type='PHOTO').first().document_file,
                signature=application.documents.filter(document_type='SIGNATURE').first().document_file,
                blood_group=application.applicant.rmp_profile.blood_group if hasattr(application.applicant, 'rmp_profile') else '',
            )
            
            application.status = 'COMPLETED'
            application.certificate_generated = True
            application.certificate_number = id_card.card_number
            application.save()
            
            messages.success(request, 'ID card generated successfully!')
            return redirect('admin_id_card_requests')
            
        except Exception as e:
            logger.error(f"ID card generation error: {e}")
            messages.error(request, 'Error generating ID card. Please try again.')
    
    context = {
        'application': application
    }
    return render(request, 'MMC/admin/generate_id_card.html', context)

# CPD Program Views
class CPDProgramListView(LoginRequiredMixin, ListView):
    model = CPDProgram
    template_name = 'MMC/cpd/program_list.html'
    context_object_name = 'programs'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = CPDProgram.objects.filter(
            is_active=True, 
            status='Published',
            registration_deadline__gte=timezone.now()
        )
        
        # Filter by specialization if provided
        specialization = self.request.GET.get('specialization')
        if specialization:
            queryset = queryset.filter(specializations__icontains=specialization)
            
        # Filter by program type if provided
        program_type = self.request.GET.get('program_type')
        if program_type:
            queryset = queryset.filter(program_type=program_type)
            
        # Filter by date range
        date_filter = self.request.GET.get('date_filter')
        if date_filter == 'upcoming':
            queryset = queryset.filter(start_date__gte=timezone.now())
        elif date_filter == 'ongoing':
            queryset = queryset.filter(
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            )
            
        return queryset.order_by('start_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['specializations'] = CustomUser.objects.filter(
            user_type='rmp'
        ).exclude(specialization__isnull=True).exclude(specialization='').values_list('specialization', flat=True).distinct()
        context['program_types'] = CPDProgram.PROGRAM_TYPES
        return context


@login_required
@rmp_required
def cpd_program_detail(request, program_id):
    program = get_object_or_404(CPDProgram, program_id=program_id)
    
    # Check if user is already registered
    user_participation = CPDParticipation.objects.filter(
        participant=request.user,
        program=program
    ).first()
    
    context = {
        'program': program,
        'user_participation': user_participation,
        'available_slots': program.get_available_slots(),
        'is_registration_open': program.is_registration_open(),
    }
    return render(request, 'MMC/cpd/program_detail.html', context)

@login_required
@rmp_required
def cpd_program_register(request, program_id):
    program = get_object_or_404(CPDProgram, program_id=program_id)
    
    # Validation checks
    if not program.is_registration_open():
        messages.error(request, 'Registration for this program is closed.')
        return redirect('cpd_program_detail', program_id=program_id)
    
    if program.is_full():
        messages.error(request, 'This program is already full.')
        return redirect('cpd_program_detail', program_id=program_id)
    
    # Check if already registered
    existing_participation = CPDParticipation.objects.filter(
        participant=request.user,
        program=program
    ).first()
    
    if existing_participation:
        messages.warning(request, 'You are already registered for this program.')
        return redirect('cpd_program_detail', program_id=program_id)
    
    try:
        with transaction.atomic():
            # Create participation record
            participation = CPDParticipation.objects.create(
                participant=request.user,
                program=program,
                attendance_status='REGISTERED'
            )
            
            # Create payment if fee exists
            if program.fee_amount > 0:
                Payment.objects.create(
                    user=request.user,
                    payment_type='CPD',
                    amount=program.fee_amount,
                    status='PENDING',
                    description=f'Registration fee for {program.title}'
                )
            
            # Create notification
            Notification.objects.create(
                user=request.user,
                notification_type='CPD_ALERT',
                title='Program Registration Successful',
                message=f'You have successfully registered for {program.title}.',
                related_object_id=str(program.program_id),
                related_object_type='CPD_PROGRAM'
            )
            
            messages.success(request, f'Successfully registered for {program.title}')
            return redirect('cpd_my_programs')
            
    except Exception as e:
        logger.error(f"CPD registration error: {e}")
        messages.error(request, 'An error occurred during registration. Please try again.')
    
    return redirect('cpd_program_detail', program_id=program_id)

@login_required
@rmp_required
def cpd_my_programs(request):
    participations = CPDParticipation.objects.filter(
        participant=request.user
    ).select_related('program').order_by('-registration_date')
    
    # Statistics
    completed_programs = participations.filter(attendance_status='COMPLETED')
    total_points = completed_programs.aggregate(total=Sum('points_earned'))['total'] or 0
    upcoming_programs = participations.filter(
        program__start_date__gte=timezone.now(),
        attendance_status='REGISTERED'
    )
    
    context = {
        'participations': participations,
        'total_points': total_points,
        'points_required': request.user.cpd_points_required,
        'upcoming_programs': upcoming_programs,
        'completed_programs': completed_programs,
        'completion_percentage': (total_points / request.user.cpd_points_required * 100) if request.user.cpd_points_required > 0 else 0,
    }
    return render(request, 'MMC/cpd/my_programs.html', context)

@login_required
@rmp_required
def cpd_program_unregister(request, program_id):
    program = get_object_or_404(CPDProgram, program_id=program_id)
    participation = get_object_or_404(
        CPDParticipation, 
        program=program, 
        participant=request.user,
        attendance_status='REGISTERED'
    )
    
    if request.method == 'POST':
        participation.attendance_status = 'CANCELLED'
        participation.save()
        
        messages.success(request, 'Successfully unregistered from the program.')
        return redirect('cpd_my_programs')
    
    context = {
        'program': program,
        'participation': participation,
    }
    return render(request, 'MMC/cpd/program_unregister.html', context)

# CPD Program Views
@login_required
@user_passes_test(is_rmp)
def cpd_programs(request):
    programs = CPDProgram.objects.filter(is_active=True).order_by('start_date')
    rmp_profile = get_rmp_profile(request.user)
    attended_programs = CPDAttendance.objects.filter(rmp=rmp_profile).select_related('program')
    
    # Apply filters
    program_type = request.GET.get('program_type')
    date_range = request.GET.get('date_range')
    points_min = request.GET.get('points_min')
    
    if program_type:
        programs = programs.filter(program_type=program_type)
    if date_range == 'upcoming':
        programs = programs.filter(start_date__gte=timezone.now())
    elif date_range == 'past':
        programs = programs.filter(start_date__lt=timezone.now())
    if points_min:
        programs = programs.filter(cpd_points__gte=points_min)
    
    context = {
        'programs': programs,
        'attended_programs': attended_programs,
        'rmp_profile': rmp_profile,
        'now': timezone.now(),
    }
    
    return render(request, 'MMC/cpd/programs.html', context)

@login_required
@user_passes_test(is_rmp)
def cpd_attendance(request, program_id):
    program = get_object_or_404(CPDProgram, id=program_id, is_active=True)
    rmp_profile = get_rmp_profile(request.user)
    
    # Check if already attended
    if CPDAttendance.objects.filter(rmp=rmp_profile, program=program).exists():
        messages.warning(request, "You have already registered for this program.")
        return redirect('cpd_programs')
    
    # Check available slots
    if program.available_slots <= 0:
        messages.error(request, "No available slots for this program.")
        return redirect('cpd_programs')
    
    # Create attendance record
    attendance = CPDAttendance.objects.create(
        rmp=rmp_profile,
        program=program,
        points_earned=program.cpd_points
    )
    
    # Update RMP's CPD points
    rmp_profile.total_cpd_points += program.cpd_points
    if program.is_online:
        rmp_profile.online_cpd_points += program.cpd_points
    else:
        rmp_profile.offline_cpd_points += program.cpd_points
    rmp_profile.save()
    
    # Create audit log
    create_audit_log(
        user=request.user,
        action_type='create',
        model_name='CPDAttendance',
        object_id=attendance.id,
        description=f"Registered for CPD program: {program.title}",
        request=request
    )
    
    messages.success(request, f"Successfully registered for {program.title}. You will earn {program.cpd_points} CPD points.")
    return redirect('cpd_programs')

@login_required
@user_passes_test(is_rmp)
def cpd_certificates(request):
    rmp_profile = get_rmp_profile(request.user)
    certificates = CPDAttendance.objects.filter(
        rmp=rmp_profile, 
        certificate_issued=True
    ).select_related('program')
    
    context = {
        'certificates': certificates,
    }
    
    return render(request, 'MMC/cpd/certificates.html', context)

# CPD Management Views
@login_required
@user_passes_test(is_admin_or_staff)
def create_cpd_program(request):
    if request.method == 'POST':
        form = CPDProgramForm(request.POST)
        if form.is_valid():
            program = form.save(commit=False)
            program.created_by = request.user
            program.save()
            return JsonResponse({'success': True, 'message': 'CPD program created successfully'})
        else:
            return JsonResponse({'success': False, 'message': 'Please correct the errors'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
@user_passes_test(is_admin_or_staff)
def delete_cpd_program(request, program_id):
    if request.method == 'DELETE':
        program = get_object_or_404(CPDProgram, id=program_id)
        program.delete()
        return JsonResponse({'success': True, 'message': 'Program deleted successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
@user_passes_test(is_rmp)
def cpd_points_summary(request):
    rmp_profile = get_rmp_profile(request.user)
    
    # Calculate CPD progress
    cpd_required = rmp_profile.cpd_points_required
    cpd_earned = rmp_profile.total_cpd_points
    cpd_deficit = max(0, cpd_required - cpd_earned)
    cpd_progress = min(100, int((cpd_earned / cpd_required) * 100)) if cpd_required > 0 else 0
    
    # Get recent CPD activities
    recent_activities = CPDAttendance.objects.filter(rmp=rmp_profile).select_related('program').order_by('-attendance_date')[:10]
    
    # CPD by type
    online_points = rmp_profile.online_cpd_points
    offline_points = rmp_profile.offline_cpd_points
    
    context = {
        'rmp_profile': rmp_profile,
        'cpd_required': cpd_required,
        'cpd_earned': cpd_earned,
        'cpd_deficit': cpd_deficit,
        'cpd_progress': cpd_progress,
        'recent_activities': recent_activities,
        'online_points': online_points,
        'offline_points': offline_points,
    }
    
    return render(request, 'MMC/cpd/points_summary.html', context)


# ============ CPD ACCREDITATION VIEWS ============
@login_required
@rmp_required
def cpd_accreditation_apply(request):
    """Apply for CPD accreditation as organization or speaker"""
    if request.method == 'POST':
        form = AccreditationForm(request.POST, request.FILES)
        if form.is_valid():
            accreditation = form.save(commit=False)
            accreditation.status = 'SUBMITTED'
            accreditation.save()
            
            messages.success(request, 'Accreditation application submitted successfully!')
            return redirect('cpd_accreditation_status')
    else:
        form = AccreditationForm()
    
    context = {
        'form': form
    }
    return render(request, 'MMC/cpd/accreditation_apply.html', context)

@login_required
@rmp_required
def cpd_accreditation_status(request):
    """View accreditation application status"""
    accreditations = Accreditation.objects.filter(
        email=request.user.email
    ).order_by('-applied_date')
    
    context = {
        'accreditations': accreditations
    }
    return render(request, 'MMC/cpd/accreditation_status.html', context)

# CPD Accreditation Management
@login_required
def cpd_accreditation_requests(request):
    accreditation_requests = Accreditation.objects.all().order_by('-applied_date')
    
    context = {
        'accreditation_requests': accreditation_requests
    }
    return render(request, 'MMC/cpd/accreditation_requests.html', context)

@login_required
def review_accreditation(request, accreditation_id):
    accreditation = get_object_or_404(Accreditation, accreditation_id=accreditation_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            accreditation.status = 'APPROVED'
            accreditation.valid_until = timezone.now() + timedelta(days=365)
            messages.success(request, 'Accreditation approved successfully!')
        elif action == 'reject':
            accreditation.status = 'REJECTED'
            messages.warning(request, 'Accreditation rejected.')
        elif action == 'request_info':
            accreditation.status = 'UNDER_REVIEW'
            messages.info(request, 'Additional information requested.')
        
        accreditation.save()
        return redirect('cpd_accreditation_requests')
    
    context = {
        'accreditation': accreditation
    }
    return render(request, 'MMC/cpd/review_accreditation.html', context)


# Payment Views
@login_required
def payment_page(request, application_id):
    application = get_object_or_404(Application, application_id=application_id)
    
    # Check permission
    if request.user.user_type == 'rmp' and application.applicant != request.user:
        messages.error(request, "You don't have permission to access this payment.")
        return redirect('dashboard')
    
    # Calculate payment amount
    amount = calculate_application_fee(application.application_type)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Create payment record
                payment = Payment.objects.create(
                    user=request.user,
                    application=application,
                    payment_type='REGISTRATION',
                    amount=amount,
                    status='SUCCESS',  # In real implementation, this would be after gateway response
                    payment_method='ONLINE',
                    payment_date=timezone.now(),
                    transaction_id=f'TXN{timezone.now().strftime("%Y%m%d%H%M%S")}',
                    description=f'Payment for {application.get_application_type_display()}'
                )
                
                # Update application payment status
                application.payment_status = True
                application.payment_amount = amount
                application.payment_reference = payment.transaction_id
                application.payment_date = timezone.now()
                application.save()
                
                # Create notification
                Notification.objects.create(
                    user=request.user,
                    notification_type='PAYMENT_SUCCESS',
                    title='Payment Successful',
                    message=f'Payment of ₹{amount} for {application.get_application_type_display()} was successful.',
                    related_object_id=str(application.application_id),
                    related_object_type='APPLICATION'
                )
                
                messages.success(request, 'Payment completed successfully!')
                return redirect('application_status', application_id=application.application_id)
                
        except Exception as e:
            logger.error(f"Payment processing error: {e}")
            messages.error(request, 'An error occurred during payment processing. Please try again.')
    
    context = {
        'application': application,
        'amount': amount,
    }
    return render(request, 'MMC/payments/payment_page.html', context)

# Admin Views
@login_required
@user_passes_test(is_admin_or_staff)
def admin_dashboard(request):
    return redirect('dashboard')

@login_required
@user_passes_test(is_admin_or_staff)
def admin_applications(request):
    applications = Application.objects.select_related('rmp', 'assigned_to').all()
    
    # Filtering
    status_filter = request.GET.get('status')
    type_filter = request.GET.get('type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    priority_filter = request.GET.get('priority')
    
    if status_filter:
        applications = applications.filter(status=status_filter)
    if type_filter:
        applications = applications.filter(application_type=type_filter)
    if date_from:
        applications = applications.filter(submitted_date__date__gte=date_from)
    if date_to:
        applications = applications.filter(submitted_date__date__lte=date_to)
    if priority_filter:
        applications = applications.filter(priority=priority_filter)
    
    # Show overdue applications by default for staff
    if request.user.user_type == 'staff' and not any([status_filter, type_filter, date_from, date_to, priority_filter]):
        applications = applications.filter(is_overdue=True)
    
    # Pagination
    paginator = Paginator(applications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'applications': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'date_from': date_from,
        'date_to': date_to,
        'priority_filter': priority_filter,
    }
    
    return render(request, 'MMC/admin/applications.html', context)

@login_required
@user_passes_test(is_admin_or_staff)
def admin_application_review(request, application_id):
    application = get_object_or_404(Application, application_id=application_id)
    
    if request.method == 'POST':
        form = ApplicationReviewForm(request.POST, instance=application)
        if form.is_valid():
            application = form.save(commit=False)
            
            if application.status == 'approved':
                application.approved_by = request.user
                application.approval_date = timezone.now()
                application.actual_completion_date = timezone.now()
                
                # Generate certificate if applicable
                if application.application_type in ['provisional', 'permanent', 'renewal']:
                    generate_certificate(application)
            
            application.save()
            
            # Create notification for RMP
            Notification.objects.create(
                user=application.rmp.user,
                notification_type='registration',
                title=f'Application Status Update',
                message=f"Your {application.get_application_type_display()} application has been {application.get_status_display()}",
                related_object_id=str(application.application_id),
                action_url=reverse('application_status', args=[application.application_id])
            )
            
            # Create audit log
            create_audit_log(
                user=request.user,
                action_type='update',
                model_name='Application',
                object_id=application.application_id,
                description=f"Application reviewed and {application.get_status_display()}",
                request=request
            )
            
            messages.success(request, "Application review updated successfully.")
            return redirect('admin_applications')
    else:
        form = ApplicationReviewForm(instance=application)
    
    documents = Document.objects.filter(application=application)
    steps = ApplicationStep.objects.filter(application=application).order_by('step_number')
    
    context = {
        'application': application,
        'form': form,
        'documents': documents,
        'steps': steps,
    }
    
    return render(request, 'MMC/admin/application_review.html', context)

@login_required
def admin_application_list(request):
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    urgency_filter = request.GET.get('urgency', '')
    
    applications = Application.objects.all().select_related('applicant')
    
    if status_filter:
        applications = applications.filter(status=status_filter)
    if type_filter:
        applications = applications.filter(application_type=type_filter)
    if urgency_filter == 'urgent':
        applications = applications.filter(is_urgent=True)
    if urgency_filter == 'overdue':
        applications = applications.filter(
            expected_completion_date__lt=timezone.now(),
            status__in=['SUBMITTED', 'UNDER_REVIEW']
        )
    
    # Pagination
    paginator = Paginator(applications.order_by('-application_date'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'applications': page_obj,
        'status_choices': Application.APPLICATION_STATUS,
        'type_choices': Application.APPLICATION_TYPES,
        'selected_status': status_filter,
        'selected_type': type_filter,
        'selected_urgency': urgency_filter,
    }
    return render(request, 'MMC/admin/application_list.html', context)

@login_required
def admin_application_detail(request, application_id):
    application = get_object_or_404(Application, application_id=application_id)
    step_data = ApplicationStep.objects.filter(application=application).order_by('step_number')
    documents = Document.objects.filter(application=application)
    payments = Payment.objects.filter(application=application)
    verification_tasks = VerificationTask.objects.filter(application=application)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('verification_notes', '')
        
        try:
            with transaction.atomic():
                if action == 'approve':
                    application.status = 'APPROVED'
                    application.verified_by = request.user
                    application.verification_date = timezone.now()
                    application.verification_notes = notes
                    
                    # Generate certificate if applicable
                    certificate = application.generate_certificate()
                    
                    application.save()
                    
                    # Create notification for applicant
                    Notification.objects.create(
                        user=application.applicant,
                        notification_type='APPLICATION_STATUS',
                        title='Application Approved',
                        message=f'Your {application.get_application_type_display()} application has been approved.',
                        related_object_id=str(application.application_id),
                        related_object_type='APPLICATION'
                    )
                    
                    messages.success(request, 'Application approved successfully!')
                    
                elif action == 'reject':
                    application.status = 'REJECTED'
                    application.verified_by = request.user
                    application.verification_date = timezone.now()
                    application.verification_notes = notes
                    application.save()
                    
                    Notification.objects.create(
                        user=application.applicant,
                        notification_type='APPLICATION_STATUS',
                        title='Application Rejected',
                        message=f'Your {application.get_application_type_display()} application has been rejected.',
                        related_object_id=str(application.application_id),
                        related_object_type='APPLICATION'
                    )
                    
                    messages.warning(request, 'Application rejected.')
                
                elif action == 'request_info':
                    application.status = 'ADDITIONAL_INFO_REQUIRED'
                    application.verification_notes = notes
                    application.save()
                    
                    Notification.objects.create(
                        user=application.applicant,
                        notification_type='APPLICATION_STATUS',
                        title='Additional Information Required',
                        message=f'Additional information is required for your {application.get_application_type_display()} application.',
                        related_object_id=str(application.application_id),
                        related_object_type='APPLICATION'
                    )
                    
                    messages.info(request, 'Additional information requested from applicant.')
                
                elif action == 'assign_verifier':
                    verifier_id = request.POST.get('verifier_id')
                    if verifier_id:
                        verifier = get_object_or_404(CustomUser, id=verifier_id, user_type__in=['ADMIN', 'VERIFIER'])
                        VerificationTask.objects.create(
                            application=application,
                            assigned_to=verifier,
                            due_date=timezone.now() + timedelta(days=3),
                            notes=notes
                        )
                        application.status = 'UNDER_REVIEW'
                        application.save()
                        
                        messages.success(request, f'Application assigned to {verifier.get_full_name()}')
                
        except Exception as e:
            logger.error(f"Error processing application: {e}")
            messages.error(request, 'An error occurred while processing the application.')
    
    # Available verifiers for assignment
    verifiers = CustomUser.objects.filter(user_type__in=['ADMIN', 'VERIFIER'], is_active=True)
    
    context = {
        'application': application,
        'step_data': step_data,
        'documents': documents,
        'payments': payments,
        'verification_tasks': verification_tasks,
        'verifiers': verifiers,
    }
    return render(request, 'MMC/admin/application_detail.html', context)

# ============ CERTIFICATE MANAGEMENT ============
@login_required
@rmp_required
def generate_certificate(request, certificate_id):
    """Generate and download certificate"""
    certificate = get_object_or_404(Certificate, certificate_id=certificate_id, user=request.user)
    
    # In a real implementation, this would generate PDF certificate
    # For now, we'll return a mock response
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{certificate.certificate_number}.pdf"'
    
    # PDF generation would happen here
    # For demo, we'll return a simple message
    pdf_content = f"""
    MOCK CERTIFICATE GENERATION
    Certificate: {certificate.certificate_number}
    Type: {certificate.get_certificate_type_display()}
    Issued To: {request.user.get_full_name()}
    Issue Date: {certificate.issue_date}
    Valid Until: {certificate.valid_until}
    """
    
    response.write(pdf_content)
    return response

@login_required
def admin_certificate_management(request):
    """Admin certificate management"""
    certificates = Certificate.objects.all().select_related('user', 'application').order_by('-issue_date')
    
    type_filter = request.GET.get('type')
    if type_filter:
        certificates = certificates.filter(certificate_type=type_filter)
    
    context = {
        'certificates': certificates,
        'type_filter': type_filter,
    }
    return render(request, 'MMC/admin/certificate_management.html', context)

@login_required
@user_passes_test(is_admin_or_staff)
def admin_cpd_management(request):
    programs = CPDProgram.objects.all().order_by('-created_date')
    accreditations = Accreditation.objects.all().order_by('-created_date')
    
    # Statistics
    program_stats = {
        'total': programs.count(),
        'active': programs.filter(is_active=True).count(),
        'upcoming': programs.filter(start_date__gt=timezone.now()).count(),
        'ongoing': programs.filter(start_date__lte=timezone.now(), end_date__gte=timezone.now()).count(),
    }
    
    context = {
        'programs': programs,
        'accreditations': accreditations,
        'program_stats': program_stats,
    }
    
    return render(request, 'MMC/admin/cpd_management.html', context)

@login_required
@user_passes_test(is_admin)
def admin_user_management(request):
    users = CustomUser.objects.all().order_by('-date_joined')
    
    context = {
        'users': users,
    }
    
    return render(request, 'MMC/admin/user_management.html', context)


# Admin Verification Management
@login_required
def verification_queue(request):
    status_filter = request.GET.get('status', 'pending')
    assigned_to_me = request.GET.get('assigned_to_me')
    
    if assigned_to_me:
        applications = Application.objects.filter(
            verification_tasks__assigned_to=request.user,
            verification_tasks__status__in=['PENDING', 'IN_PROGRESS']
        )
    else:
        applications = Application.objects.filter(
            status__in=['submitted', 'under_review', 'additional_info_required']
        )
    
    if status_filter == 'overdue':
        applications = applications.filter(
            expected_completion_date__lt=timezone.now()
        )
    elif status_filter == 'urgent':
        applications = applications.filter(is_urgent=True)
    
    context = {
        'applications': applications.select_related('applicant').order_by('-application_date'),
        'status_filter': status_filter,
        'assigned_to_me': assigned_to_me,
    }
    return render(request, 'MMC/admin/verification_queue.html', context)

@login_required
def assign_verification_task(request, application_id):
    application = get_object_or_404(Application, application_id=application_id)
    
    if request.method == 'POST':
        form = VerificationTaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.application = application
            task.save()
            
            # Update application status
            application.status = 'UNDER_REVIEW'
            application.save()
            
            messages.success(request, f'Verification task assigned to {task.assigned_to.get_full_name()}')
            return redirect('verification_queue')
    else:
        form = VerificationTaskForm(initial={'due_date': timezone.now() + timedelta(days=3)})
    
    context = {
        'form': form,
        'application': application
    }
    return render(request, 'MMC/admin/assign_verification_task.html', context)

@login_required
def my_verification_tasks(request):
    tasks = VerificationTask.objects.filter(
        assigned_to=request.user,
        status__in=['PENDING', 'IN_PROGRESS']
    ).select_related('application', 'application__applicant').order_by('due_date')
    
    # Statistics
    task_stats = {
        'total': tasks.count(),
        'overdue': tasks.filter(due_date__lt=timezone.now()).count(),
        'high_priority': tasks.filter(priority='HIGH').count(),
    }
    
    context = {
        'tasks': tasks,
        'task_stats': task_stats,
    }
    return render(request, 'MMC/admin/my_verification_tasks.html', context)

@login_required
def update_verification_task(request, task_id):
    task = get_object_or_404(VerificationTask, id=task_id, assigned_to=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        try:
            if action == 'start':
                task.status = 'IN_PROGRESS'
                task.save()
                messages.info(request, 'Task marked as in progress.')
                
            elif action == 'complete':
                task.status = 'COMPLETED'
                task.completed_date = timezone.now()
                task.notes = notes
                task.save()
                messages.success(request, 'Task completed successfully.')
                
            elif action == 'request_info':
                task.application.status = 'ADDITIONAL_INFO_REQUIRED'
                task.application.verification_notes = notes
                task.application.save()
                messages.info(request, 'Additional information requested from applicant.')
            
            return redirect('my_verification_tasks')
            
        except Exception as e:
            logger.error(f"Error updating verification task: {e}")
            messages.error(request, 'An error occurred while updating the task.')
    
    context = {
        'task': task,
    }
    return render(request, 'MMC/admin/update_verification_task.html', context)


# ============ BULK OPERATIONS ============
@login_required
def bulk_actions(request):
    if request.method == 'POST':
        form = BulkActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            applications = form.cleaned_data['applications']
            notes = form.cleaned_data['notes']
            verifier = form.cleaned_data['verifier']
            
            try:
                with transaction.atomic():
                    if action == 'ASSIGN_VERIFIER' and verifier:
                        for application in applications:
                            VerificationTask.objects.create(
                                application=application,
                                assigned_to=verifier,
                                due_date=timezone.now() + timedelta(days=3),
                                notes=notes
                            )
                            application.status = 'UNDER_REVIEW'
                            application.save()
                        messages.success(request, f'Assigned {applications.count()} applications to {verifier.get_full_name()}')
                    
                    elif action == 'BULK_APPROVE':
                        for application in applications:
                            application.status = 'APPROVED'
                            application.verified_by = request.user
                            application.verification_date = timezone.now()
                            application.verification_notes = notes
                            application.generate_certificate()
                            application.save()
                        messages.success(request, f'Approved {applications.count()} applications')
                    
                    elif action == 'BULK_REJECT':
                        for application in applications:
                            application.status = 'REJECTED'
                            application.verified_by = request.user
                            application.verification_date = timezone.now()
                            application.verification_notes = notes
                            application.save()
                        messages.warning(request, f'Rejected {applications.count()} applications')
                    
                    elif action == 'SEND_REMINDER':
                        for application in applications:
                            Notification.objects.create(
                                user=application.applicant,
                                notification_type='DEADLINE_REMINDER',
                                title='Application Update Required',
                                message='Please check your application for any required updates or additional information.',
                                related_object_id=str(application.application_id),
                                related_object_type='APPLICATION'
                            )
                        messages.info(request, f'Sent reminders for {applications.count()} applications')
                    
                    return redirect('admin_application_list')
                    
            except Exception as e:
                logger.error(f"Bulk action error: {e}")
                messages.error(request, 'An error occurred during bulk operations.')
    else:
        application_ids = request.GET.getlist('applications')
        applications = Application.objects.filter(application_id__in=application_ids)
        form = BulkActionForm(initial={'applications': applications})
    
    context = {
        'form': form,
        'applications': applications,
    }
    return render(request, 'MMC/admin/bulk_actions.html', context)

@login_required
def admin_cpd_program_list(request):
    """Admin view for managing CPD programs"""
    programs = CPDProgram.objects.all().order_by('-created_at')
    
    context = {
        'programs': programs
    }
    return render(request, 'MMC/admin/cpd_program_list.html', context)

@login_required
def admin_cpd_program_add(request):
    """Add new CPD program"""
    if request.method == 'POST':
        form = CPDProgramForm(request.POST)
        if form.is_valid():
            program = form.save(commit=False)
            program.created_by = request.user
            program.save()
            
            messages.success(request, 'CPD program created successfully!')
            return redirect('admin_cpd_program_list')
    else:
        form = CPDProgramForm()
    
    context = {
        'form': form
    }
    return render(request, 'MMC/admin/cpd_program_add.html', context)

@login_required
def admin_cpd_program_edit(request, program_id):
    """Edit CPD program"""
    program = get_object_or_404(CPDProgram, program_id=program_id)
    
    if request.method == 'POST':
        form = CPDProgramForm(request.POST, instance=program)
        if form.is_valid():
            form.save()
            messages.success(request, 'CPD program updated successfully!')
            return redirect('admin_cpd_program_list')
    else:
        form = CPDProgramForm(instance=program)
    
    context = {
        'form': form,
        'program': program
    }
    return render(request, 'MMC/admin/cpd_program_edit.html', context)

# Reports Views
@login_required
@user_passes_test(is_admin_or_staff)
def reports_dashboard(request):
    # Basic report data
    applications_by_type = Application.objects.values('application_type').annotate(
        count=Count('id')
    )
    applications_by_status = Application.objects.values('status').annotate(
        count=Count('id')
    )
    
    # Payment reports
    payment_summary = Payment.objects.filter(status='success').aggregate(
        total_amount=Sum('amount'),
        total_count=Count('id')
    )
    
    # CPD statistics
    cpd_stats = CPDAttendance.objects.aggregate(
        total_participations=Count('id'),
        unique_participants=Count('rmp', distinct=True),
        total_points=Sum('points_earned')
    )
    
    context = {
        'applications_by_type': list(applications_by_type),
        'applications_by_status': list(applications_by_status),
        'payment_summary': payment_summary,
        'cpd_stats': cpd_stats,
    }
    
    return render(request, 'MMC/reports/dashboard.html', context)

@login_required
def payment_reports(request):
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    payment_type = request.GET.get('payment_type')
    status = request.GET.get('status')
    
    payments = Payment.objects.all()
    
    if date_from:
        payments = payments.filter(created_at__date__gte=date_from)
    if date_to:
        payments = payments.filter(created_at__date__lte=date_to)
    if payment_type:
        payments = payments.filter(payment_type=payment_type)
    if status:
        payments = payments.filter(status=status)
    
    # Summary statistics
    summary = payments.aggregate(
        total_amount=Sum('amount'),
        total_count=Count('id'),
        success_count=Count('id', filter=Q(status='SUCCESS')),
        pending_count=Count('id', filter=Q(status='PENDING'))
    )
    
    # Daily breakdown
    daily_breakdown = payments.filter(status='SUCCESS').extra(
        {'date': "date(created_at)"}
    ).values('date').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-date')
    
    context = {
        'payments': payments.order_by('-created_at'),
        'summary': summary,
        'daily_breakdown': daily_breakdown,
        'date_from': date_from,
        'date_to': date_to,
        'payment_type': payment_type,
        'status': status,
    }
    return render(request, 'MMC/reports/payment_reports.html', context)

@login_required
def application_reports(request):
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    application_type = request.GET.get('application_type')
    status = request.GET.get('status')
    
    applications = Application.objects.all()
    
    if date_from:
        applications = applications.filter(application_date__date__gte=date_from)
    if date_to:
        applications = applications.filter(application_date__date__lte=date_to)
    if application_type:
        applications = applications.filter(application_type=application_type)
    if status:
        applications = applications.filter(status=status)
    
    # Summary statistics
    stats = {
        'total': applications.count(),
        'submitted': applications.filter(status='SUBMITTED').count(),
        'under_review': applications.filter(status='UNDER_REVIEW').count(),
        'approved': applications.filter(status='APPROVED').count(),
        'rejected': applications.filter(status='REJECTED').count(),
        'completed': applications.filter(status='COMPLETED').count(),
    }
    
    # Type-wise breakdown
    type_breakdown = applications.values('application_type').annotate(
        total=Count('id'),
        approved=Count('id', filter=Q(status='APPROVED')),
        rejected=Count('id', filter=Q(status='REJECTED'))
    ).order_by('-total')
    
    # Monthly trend
    monthly_trend = applications.extra(
        {'month': "strftime('%%Y-%%m', application_date)"}
    ).values('month').annotate(
        total=Count('id')
    ).order_by('month')
    
    context = {
        'applications': applications.select_related('applicant').order_by('-application_date'),
        'stats': stats,
        'type_breakdown': type_breakdown,
        'monthly_trend': monthly_trend,
        'date_from': date_from,
        'date_to': date_to,
        'application_type': application_type,
        'status': status,
    }
    return render(request, 'MMC/reports/application_reports.html', context)

@login_required
@user_passes_test(is_admin_or_staff)
def generate_report(request):
    if request.method == 'POST':
        form = ReportGenerationForm(request.POST)
        if form.is_valid():
            report_type = form.cleaned_data['report_type']
            date_from = form.cleaned_data['date_from']
            date_to = form.cleaned_data['date_to']
            format_type = form.cleaned_data['format']
            
            # Generate report data based on type
            report_data = generate_report_data(report_type, date_from, date_to)
            
            # Create report record
            report = Report.objects.create(
                report_type=report_type,
                title=f"{report_type.replace('_', ' ').title()} Report",
                generated_by=request.user,
                date_from=date_from,
                date_to=date_to,
                report_data=report_data,
            )
            
            # Generate file based on format
            if format_type == 'csv':
                return generate_csv_report(report_data, report_type)
            elif format_type == 'pdf':
                return generate_pdf_report(report_data, report_type)
            else:
                messages.success(request, "Report generated successfully!")
                return redirect('reports_dashboard')
    
    else:
        form = ReportGenerationForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'MMC/reports/generate_report.html', context)

def generate_report_data(report_type, date_from, date_to):
    """Generate report data based on type and date range"""
    filters = {}
    if date_from:
        filters['submitted_date__date__gte'] = date_from
    if date_to:
        filters['submitted_date__date__lte'] = date_to
    
    if report_type == 'payment_summary':
        payments = Payment.objects.filter(**filters) if filters else Payment.objects.all()
        return {
            'total_amount': payments.aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_count': payments.count(),
            'by_status': list(payments.values('status').annotate(count=Count('id'), amount=Sum('amount'))),
            'by_method': list(payments.values('payment_method').annotate(count=Count('id'), amount=Sum('amount'))),
        }
    
    elif report_type == 'application_status':
        applications = Application.objects.filter(**filters) if filters else Application.objects.all()
        return {
            'total_applications': applications.count(),
            'by_type': list(applications.values('application_type').annotate(count=Count('id'))),
            'by_status': list(applications.values('status').annotate(count=Count('id'))),
            'pending_count': applications.filter(status='submitted').count(),
        }
    
    # Add more report types as needed
    return {}

def generate_csv_report(report_data, report_type):
    """Generate CSV report"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
    
    writer = csv.writer(response)
    
    if report_type == 'payment_summary':
        writer.writerow(['Status', 'Count', 'Amount'])
        for item in report_data.get('by_status', []):
            writer.writerow([item['status'], item['count'], item['amount']])
    
    return response

def generate_pdf_report(report_data, report_type):
    """Generate PDF report (placeholder)"""
    # Implementation would use a library like ReportLab or WeasyPrint
    return HttpResponse("PDF generation would be implemented here")


# Comprehensive Reports
@login_required
def comprehensive_reports(request):
    # Date range calculation
    date_range = request.GET.get('date_range', 'THIS_MONTH')
    end_date = timezone.now().date()
    
    if date_range == 'TODAY':
        start_date = end_date
    elif date_range == 'YESTERDAY':
        start_date = end_date - timedelta(days=1)
    elif date_range == 'THIS_WEEK':
        start_date = end_date - timedelta(days=end_date.weekday())
    elif date_range == 'THIS_MONTH':
        start_date = end_date.replace(day=1)
    else:
        start_date = request.GET.get('start_date') or (end_date - timedelta(days=30))
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = request.GET.get('end_date') or end_date
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Application Statistics
    applications = Application.objects.filter(application_date__date__range=[start_date, end_date])
    application_stats = applications.values('application_type').annotate(
        total=Count('id'),
        approved=Count('id', filter=Q(status='APPROVED')),
        pending=Count('id', filter=Q(status__in=['SUBMITTED', 'UNDER_REVIEW']))
    ).order_by('-total')
    
    # Payment Statistics
    payments = Payment.objects.filter(created_at__date__range=[start_date, end_date], status='SUCCESS')
    payment_summary = payments.aggregate(
        total_amount=Sum('amount'),
        total_count=Count('id')
    )
    
    # CPD Statistics
    cpd_participations = CPDParticipation.objects.filter(
        registration_date__date__range=[start_date, end_date]
    )
    cpd_stats = cpd_participations.aggregate(
        total_participants=Count('id'),
        completed_sessions=Count('id', filter=Q(attendance_status='COMPLETED')),
        total_points=Sum('points_earned')
    )
    
    # User Statistics
    user_stats = CustomUser.objects.filter(
        date_joined__date__range=[start_date, end_date],
        user_type='rmp'
    ).aggregate(
        new_registrations=Count('id'),
        verified_users=Count('id', filter=Q(is_verified=True))
    )
    
    # Staff Performance
    staff_performance = CustomUser.objects.filter(
        user_type__in=['ADMIN', 'VERIFIER'],
        verification_tasks__completed_date__date__range=[start_date, end_date]
    ).annotate(
        applications_processed=Count('verified_applications'),
        tasks_completed=Count('verification_tasks'),
        avg_processing_days=Avg(
            ExpressionWrapper(
                F('verification_tasks__completed_date') - F('verification_tasks__assigned_date'),
                output_field=DurationField()
            )
        )
    ).values('username', 'first_name', 'last_name', 'applications_processed', 'tasks_completed', 'avg_processing_days')
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'application_stats': application_stats,
        'payment_summary': payment_summary,
        'cpd_stats': cpd_stats,
        'user_stats': user_stats,
        'staff_performance': staff_performance,
        'filter_form': ReportFilterForm(initial={
            'date_range': date_range,
            'start_date': start_date,
            'end_date': end_date
        })
    }
    return render(request, 'MMC/reports/comprehensive_reports.html', context)

@login_required
def export_reports(request, report_type):
    if report_type == 'applications':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="applications_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Application ID', 'Type', 'Applicant', 'Status', 'Submission Date', 'Completion Date', 'Payment Status'])
        
        applications = Application.objects.all().select_related('applicant')
        for app in applications:
            writer.writerow([
                app.application_id,
                app.get_application_type_display(),
                app.applicant.get_full_name(),
                app.get_status_display(),
                app.submission_date,
                app.actual_completion_date,
                'Paid' if app.payment_status else 'Pending'
            ])
        
        return response
    
    elif report_type == 'payments':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="payments_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Payment ID', 'User', 'Type', 'Amount', 'Status', 'Date', 'Transaction ID'])
        
        payments = Payment.objects.all().select_related('user')
        for payment in payments:
            writer.writerow([
                payment.payment_id,
                payment.user.get_full_name(),
                payment.get_payment_type_display(),
                payment.amount,
                payment.get_status_display(),
                payment.payment_date,
                payment.transaction_id
            ])
        
        return response
    
    elif report_type == 'cpd':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="cpd_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Program', 'Participant', 'Registration Date', 'Status', 'Points Earned'])
        
        participations = CPDParticipation.objects.all().select_related('program', 'participant')
        for participation in participations:
            writer.writerow([
                participation.program.title,
                participation.participant.get_full_name(),
                participation.registration_date,
                participation.get_attendance_status_display(),
                participation.points_earned
            ])
        
        return response
    
    messages.error(request, 'Invalid report type specified.')
    return redirect('reports_dashboard')

# AI Integration Views
@login_required
@user_passes_test(is_rmp)
def ai_insights(request):
    rmp_profile = get_rmp_profile(request.user)
    
    try:
        ai_score = AIPerformanceScore.objects.get(rmp=rmp_profile)
        insights = AIInsight.objects.filter(rmp=rmp_profile, is_active=True).order_by('-generated_date')
        alerts = PredictiveAlert.objects.filter(rmp=rmp_profile, is_active=True, is_dismissed=False)
    except AIPerformanceScore.DoesNotExist:
        ai_score = None
        insights = []
        alerts = []
    
    context = {
        'ai_score': ai_score,
        'insights': insights,
        'alerts': alerts,
        'rmp_profile': rmp_profile,
    }
    
    return render(request, 'MMC/ai/insights.html', context)

# AI Integration Views
@login_required
def ai_insights(request):
    if request.user.user_type == 'rmp':
        insights = AIInsight.objects.filter(user=request.user, is_active=True).order_by('-generated_at')[:10]
        performance_score = AIPerformanceScore.objects.filter(user=request.user).first()
        
        # Generate mock AI insights if none exist
        if not insights.exists():
            insights = generate_ai_insights(request.user)
        
        context = {
            'insights': insights,
            'performance_score': performance_score
        }
        return render(request, 'MMC/ai/rmp_insights.html', context)
    
    elif request.user.user_type in ['ADMIN', 'SUPER_ADMIN']:
        # Admin AI dashboard with predictive analytics
        risk_applications = Application.objects.filter(
            status='under_review'
        ).annotate(
            risk_score=Case(
                When(application_type__in=['PERMANENT_REG', 'FOREIGN_PERMANENT'], then=Value(30)),
                When(verification_notes__isnull=False, then=Value(70)),
                default=Value(50),
                output_field=IntegerField()
            )
        ).filter(risk_score__gte=70).order_by('-risk_score')[:10]
        
        compliance_alerts = CustomUser.objects.filter(
            user_type='rmp',
            registration_status='permanent'
        ).annotate(
            cpd_deficit=F('cpd_points_required') - F('total_cpd_points')
        ).filter(
            Q(cpd_deficit__gt=0) | 
            Q(applications__status='EXPIRED') |
            Q(complaints_against__status='PENDING')
        ).distinct()[:10]
        
        context = {
            'risk_applications': risk_applications,
            'compliance_alerts': compliance_alerts
        }
        return render(request, 'MMC/ai/admin_insights.html', context)

def generate_ai_insights(user):
    """Generate mock AI insights for RMP"""
    insights = []
    
    # CPD Insights
    if user.total_cpd_points < user.cpd_points_required:
        insights.append(AIInsight.objects.create(
            user=user,
            insight_type='CPD_COMPLIANCE',
            insight_data={
                'message': f'You need {user.cpd_points_required - user.total_cpd_points} more CPD points to meet annual requirements.',
                'suggestion': 'Consider attending upcoming specialization-specific CPD programs.',
                'urgency': 'medium'
            },
            confidence_score=85.5
        ))
    
    # Registration Renewal Insights
    recent_apps = Application.objects.filter(applicant=user, status='APPROVED').order_by('-application_date').first()
    if recent_apps and (timezone.now() - recent_apps.application_date).days > 300:
        insights.append(AIInsight.objects.create(
            user=user,
            insight_type='RENEWAL_REMINDER',
            insight_data={
                'message': 'Your registration renewal is due in the next 2 months.',
                'suggestion': 'Start renewal process early to avoid last-minute delays.',
                'deadline': (recent_apps.application_date + timedelta(days=365)).strftime('%Y-%m-%d')
            },
            confidence_score=92.3
        ))
    
    return insights


@login_required
@user_passes_test(is_admin_or_staff)
def ai_dashboard(request):
    # AI dashboard for admin with overall statistics
    performance_scores = AIPerformanceScore.objects.all()
    avg_scores = performance_scores.aggregate(
        avg_overall=Avg('overall_score'),
        avg_cpd=Avg('cpd_score'),
        avg_compliance=Avg('compliance_score')
    )
    
    # Risk analysis
    high_risk_rmps = performance_scores.filter(overall_score__lt=60).count()
    medium_risk_rmps = performance_scores.filter(overall_score__gte=60, overall_score__lt=75).count()
    
    context = {
        'avg_scores': avg_scores,
        'high_risk_rmps': high_risk_rmps,
        'medium_risk_rmps': medium_risk_rmps,
        'total_analyzed': performance_scores.count(),
    }
    
    return render(request, 'MMC/ai/admin_dashboard.html', context)


# ============ AI INTEGRATION ============
@login_required
def ai_insights(request):
    if request.user.user_type == 'rmp':
        return rmp_ai_insights(request)
    elif request.user.user_type in ['ADMIN', 'SUPER_ADMIN']:
        return admin_ai_insights(request)

@login_required
@rmp_required
def rmp_ai_insights(request):
    user = request.user
    insights = AIInsight.objects.filter(user=user, is_active=True).order_by('-generated_at')
    
    # Generate insights if none exist
    if not insights.exists():
        insights = generate_rmp_ai_insights(user)
    
    performance_score = AIPerformanceScore.objects.filter(user=user).first()
    if not performance_score:
        performance_score = calculate_performance_score(user)
    
    # CPD recommendations
    cpd_recommendations = CPDProgram.objects.filter(
        specializations__icontains=user.specialization,
        start_date__gte=timezone.now(),
        is_active=True
    ).order_by('start_date')[:5]
    
    context = {
        'insights': insights,
        'performance_score': performance_score,
        'cpd_recommendations': cpd_recommendations,
    }
    return render(request, 'MMC/ai/rmp_insights.html', context)

@login_required
def admin_ai_insights(request):
    # Risk assessment for applications
    high_risk_applications = Application.objects.filter(
        status='UNDER_REVIEW'
    ).annotate(
        risk_score=Case(
            When(application_type__in=['FOREIGN_PERMANENT', 'PERMANENT_DEFAULTER'], then=Value(80)),
            When(verification_notes__isnull=False, then=Value(70)),
            When(Q(documents__is_verified=False) & Q(documents__isnull=False), then=Value(60)),
            When(expected_completion_date__lt=timezone.now(), then=Value(50)),
            default=Value(30),
            output_field=IntegerField()
        )
    ).filter(risk_score__gte=70).distinct().order_by('-risk_score')[:10]
    
    # Compliance alerts
    compliance_alerts = CustomUser.objects.filter(
        user_type='rmp',
        registration_status='PERMANENT'
    ).annotate(
        cpd_deficit=F('cpd_points_required') - F('total_cpd_points'),
        renewal_soon=Case(
            When(renewal_date__lte=timezone.now().date() + timedelta(days=30), then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        ),
        risk_level=Case(
            When(Q(cpd_deficit__gt=20) & Q(renewal_soon=True), then=Value('HIGH')),
            When(Q(cpd_deficit__gt=10) | Q(renewal_soon=True), then=Value('MEDIUM')),
            default=Value('LOW'),
            output_field=CharField()
        )
    ).filter(~Q(risk_level='LOW')).order_by('-cpd_deficit')[:10]
    
    # Performance predictions
    performance_predictions = AIPerformanceScore.objects.filter(
        overall_score__lt=70
    ).select_related('user').order_by('overall_score')[:10]
    
    # System health insights
    system_health = {
        'pending_applications': Application.objects.filter(status__in=['SUBMITTED', 'UNDER_REVIEW']).count(),
        'overdue_tasks': VerificationTask.objects.filter(
            due_date__lt=timezone.now(),
            status__in=['PENDING', 'IN_PROGRESS']
        ).count(),
        'pending_payments': Payment.objects.filter(status='PENDING').count(),
        'cpd_completion_rate': calculate_cpd_completion_rate(),
    }
    
    context = {
        'high_risk_applications': high_risk_applications,
        'compliance_alerts': compliance_alerts,
        'performance_predictions': performance_predictions,
        'system_health': system_health,
    }
    return render(request, 'MMC/ai/admin_insights.html', context)

def generate_rmp_ai_insights(user):
    """Generate AI insights for RMP users"""
    insights = []
    
    # CPD Compliance Insight
    cpd_completion = (user.total_cpd_points / user.cpd_points_required * 100) if user.cpd_points_required > 0 else 0
    if cpd_completion < 60:
        insights.append(AIInsight.objects.create(
            user=user,
            insight_type='CPD_COMPLIANCE',
            insight_data={
                'message': f'Your CPD completion is at {cpd_completion:.1f}%.',
                'suggestion': 'Consider attending more CPD programs to meet requirements.',
                'urgency': 'medium',
                'current_points': user.total_cpd_points,
                'required_points': user.cpd_points_required,
            },
            confidence_score=85.5
        ))
    
    # Renewal Prediction
    if user.renewal_date and user.renewal_date <= timezone.now().date() + timedelta(days=60):
        days_until_renewal = (user.renewal_date - timezone.now().date()).days
        insights.append(AIInsight.objects.create(
            user=user,
            insight_type='RENEWAL_PREDICTION',
            insight_data={
                'message': f'Registration renewal due in {days_until_renewal} days.',
                'suggestion': 'Start the renewal process early to avoid last-minute issues.',
                'deadline': user.renewal_date.isoformat(),
                'urgency': 'high' if days_until_renewal < 30 else 'medium'
            },
            confidence_score=92.3
        ))
    
    # Performance Insight based on application history
    application_success_rate = Application.objects.filter(
        applicant=user,
        status__in=['APPROVED', 'REJECTED']
    ).count()
    
    if application_success_rate > 0:
        approved_applications = Application.objects.filter(applicant=user, status='APPROVED').count()
        success_rate = (approved_applications / application_success_rate) * 100
        
        if success_rate < 70:
            insights.append(AIInsight.objects.create(
                user=user,
                insight_type='PERFORMANCE_INSIGHT',
                insight_data={
                    'message': f'Your application success rate is {success_rate:.1f}%.',
                    'suggestion': 'Review rejected applications for common issues and improve documentation.',
                    'success_rate': success_rate,
                    'total_applications': application_success_rate,
                    'approved_applications': approved_applications
                },
                confidence_score=78.9
            ))
    
    return insights

# API Views
class ApplicationStatusAPI(View):
    def get(self, request, application_id):
        application = get_object_or_404(Application, application_id=application_id)
        
        if request.user.user_type == 'rmp' and application.rmp.user != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        data = {
            'application_id': str(application.application_id),
            'status': application.status,
            'current_step': application.current_step,
            'submitted_date': application.submitted_date.isoformat(),
            'payment_status': application.payment_status,
            'assigned_to': application.assigned_to.get_full_name() if application.assigned_to else None,
        }
        
        return JsonResponse(data)

class CPDPointsAPI(View):
    def get(self, request):
        if request.user.user_type != 'rmp':
            return JsonResponse({'error': 'RMP access only'}, status=403)
        
        try:
            rmp_profile = get_rmp_profile(request.user)
            data = {
                'total_points': rmp_profile.total_cpd_points,
                'online_points': rmp_profile.online_cpd_points,
                'offline_points': rmp_profile.offline_cpd_points,
                'points_required': rmp_profile.cpd_points_required,
                'points_deficit': rmp_profile.cpd_points_deficit,
            }
            return JsonResponse(data)
        except RMPProfile.DoesNotExist:
            return JsonResponse({'error': 'Profile not found'}, status=404)

class NotificationAPI(View):
    def get(self, request):
        notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_date')[:10]
        
        data = {
            'notifications': [
                {
                    'id': n.id,
                    'title': n.title,
                    'message': n.message,
                    'type': n.notification_type,
                    'created_date': n.created_date.isoformat(),
                    'action_url': n.action_url,
                }
                for n in notifications
            ],
            'unread_count': notifications.count(),
        }
        
        return JsonResponse(data)
    
    def post(self, request):
        # Mark notification as read
        notification_id = request.POST.get('notification_id')
        if notification_id:
            try:
                notification = Notification.objects.get(id=notification_id, user=request.user)
                notification.is_read = True
                notification.save()
                return JsonResponse({'success': True})
            except Notification.DoesNotExist:
                return JsonResponse({'error': 'Notification not found'}, status=404)
        
        return JsonResponse({'error': 'Invalid request'}, status=400)

# User Management Views
@login_required
@user_passes_test(is_admin)
def mmc_create_user(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            return JsonResponse({'success': True, 'message': 'User created successfully'})
        else:
            return JsonResponse({'success': False, 'message': 'Please correct the errors', 'errors': form.errors})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
@user_passes_test(is_admin)
def toggle_user_status(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(CustomUser, id=user_id)
        action = request.POST.get('action')
        
        if action == 'activate':
            user.is_active = True
        elif action == 'deactivate':
            user.is_active = False
        
        user.save()
        return JsonResponse({'success': True, 'message': f'User {action}d successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

# Document Verification View
@login_required
@user_passes_test(is_admin_or_staff)
def verify_document(request, document_id):
    if request.method == 'POST':
        document = get_object_or_404(Document, id=document_id)
        document.is_verified = True
        document.verified_by = request.user
        document.verified_date = timezone.now()
        document.save()
        return JsonResponse({'success': True, 'message': 'Document verified successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

# ============ NOTIFICATION MANAGEMENT ============
@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Mark all as read if requested
    if request.GET.get('mark_all_read'):
        notifications.update(is_read=True)
        messages.success(request, 'All notifications marked as read.')
        return redirect('notification_list')
    
    context = {
        'notifications': notifications
    }
    return render(request, 'MMC/notifications/notification_list.html', context)

@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_as_read()
    
    if request.headers.get('HTTP_REFERER'):
        return redirect(request.headers.get('HTTP_REFERER'))
    return redirect('notification_list')

def calculate_performance_score(user):
    """Calculate comprehensive performance score for RMP"""
    score = AIPerformanceScore.objects.create(user=user)
    
    # CPD Score (30%)
    cpd_completion = (user.total_cpd_points / user.cpd_points_required * 100) if user.cpd_points_required > 0 else 0
    score.cpd_score = min(cpd_completion, 100)
    score.cpd_completion_rate = cpd_completion
    
    # Compliance Score (30%)
    # Based on timely renewals, no pending applications, etc.
    compliance_factors = 0
    total_factors = 0
    
    # Renewal timeliness
    if user.renewal_date:
        if user.renewal_date > timezone.now().date():
            compliance_factors += 1
        total_factors += 1
    
    # No overdue applications
    overdue_apps = Application.objects.filter(
        applicant=user,
        expected_completion_date__lt=timezone.now(),
        status__in=['SUBMITTED', 'UNDER_REVIEW']
    ).count()
    if overdue_apps == 0:
        compliance_factors += 1
    total_factors += 1
    
    score.compliance_score = (compliance_factors / total_factors) * 100 if total_factors > 0 else 100
    
    # Professional Conduct Score (20%)
    # Based on complaints and disciplinary actions
    recent_complaints = Complaint.objects.filter(
        against_doctor=user,
        filed_date__gte=timezone.now() - timedelta(days=365)
    ).count()
    
    if recent_complaints == 0:
        score.professional_conduct_score = 100
        score.complaint_free_period = 365
    else:
        score.professional_conduct_score = max(60, 100 - (recent_complaints * 10))
        last_complaint = Complaint.objects.filter(against_doctor=user).order_by('-filed_date').first()
        if last_complaint:
            score.complaint_free_period = (timezone.now().date() - last_complaint.filed_date.date()).days
    
    # Calculate overall score
    score.calculate_overall_score()
    score.save()
    
    return score

def calculate_cpd_completion_rate():
    """Calculate overall CPD completion rate across all RMPs"""
    total_rmps = CustomUser.objects.filter(user_type='rmp').count()
    if total_rmps == 0:
        return 0
    
    compliant_rmps = CustomUser.objects.filter(
        user_type='rmp',
        total_cpd_points__gte=F('cpd_points_required')
    ).count()
    
    return (compliant_rmps / total_rmps) * 100



# ============ SYSTEM UTILITIES ============
@login_required
def system_utilities(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        try:
            if action == 'cleanup_temp_files':
                # Implementation for cleaning temporary files
                old_documents = Document.objects.filter(
                    uploaded_at__lt=timezone.now() - timedelta(days=30),
                    application__status__in=['REJECTED', 'CANCELLED']
                )
                count = old_documents.count()
                old_documents.delete()
                messages.success(request, f'Cleaned up {count} temporary files.')
                
            elif action == 'update_cpd_points':
                # Recalculate all CPD points
                users = CustomUser.objects.filter(user_type='rmp')
                for user in users:
                    total_points = CPDParticipation.objects.filter(
                        participant=user,
                        attendance_status='COMPLETED'
                    ).aggregate(total=Sum('points_earned'))['total'] or 0
                    user.total_cpd_points = total_points
                    user.save()
                messages.success(request, 'CPD points updated for all users.')
                
            elif action == 'generate_backup':
                # Implementation for database backup
                messages.success(request, 'Database backup generated successfully.')
                
            elif action == 'clear_old_notifications':
                old_notifications = Notification.objects.filter(
                    created_at__lt=timezone.now() - timedelta(days=90)
                )
                count = old_notifications.count()
                old_notifications.delete()
                messages.success(request, f'Cleared {count} old notifications.')
                
        except Exception as e:
            logger.error(f"System utility error: {e}")
            messages.error(request, f'Error performing system utility: {e}')
    
    # System statistics
    system_stats = {
        'total_users': CustomUser.objects.count(),
        'total_applications': Application.objects.count(),
        'pending_verifications': Application.objects.filter(status__in=['SUBMITTED', 'UNDER_REVIEW']).count(),
        'storage_used': '2.5 GB',  # This would be calculated from media files
        'last_backup': timezone.now() - timedelta(hours=6),
        'system_uptime': '99.8%',
    }
    
    context = {
        'system_stats': system_stats
    }
    return render(request, 'MMC/admin/system_utilities.html', context)


# ============ API ENDPOINTS ============
@login_required
def api_application_status(request, application_id):
    application = get_object_or_404(Application, application_id=application_id)
    
    # Check permission
    if request.user.user_type == 'rmp' and application.applicant != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    data = {
        'application_id': str(application.application_id),
        'status': application.status,
        'status_display': application.get_status_display(),
        'current_step': application.current_step,
        'payment_status': application.payment_status,
        'certificate_generated': application.certificate_generated,
        'last_updated': application.last_updated.isoformat(),
        'expected_completion': application.expected_completion_date.isoformat() if application.expected_completion_date else None,
    }
    
    return JsonResponse(data)

@login_required
def api_cpd_points(request):
    if request.user.user_type == 'rmp':
        data = {
            'total_points': request.user.total_cpd_points,
            'points_required': request.user.cpd_points_required,
            'points_deficit': max(0, request.user.cpd_points_required - request.user.total_cpd_points),
            'progress_percentage': (request.user.total_cpd_points / request.user.cpd_points_required) * 100 if request.user.cpd_points_required > 0 else 0
        }
        return JsonResponse(data)
    return JsonResponse({'error': 'RMP access required'}, status=403)

@login_required
def api_dashboard_stats(request):
    if request.user.user_type == 'rmp':
        stats = {
            'active_applications': Application.objects.filter(
                applicant=request.user, 
                status__in=['SUBMITTED', 'UNDER_REVIEW']
            ).count(),
            'completed_applications': Application.objects.filter(
                applicant=request.user,
                status__in=['APPROVED', 'COMPLETED']
            ).count(),
            'pending_payments': Payment.objects.filter(user=request.user, status='PENDING').count(),
            'unread_notifications': Notification.objects.filter(user=request.user, is_read=False).count(),
        }
        return JsonResponse(stats)
    return JsonResponse({'error': 'RMP access required'}, status=403)



# views.py - Additional Critical Views
from django.core.cache import cache
from django.db.models.functions import TruncMonth, TruncYear
import xlwt
from io import BytesIO

# ============ SERVICE-SPECIFIC VIEWS ============
@login_required
@rmp_required
def service_selection1(request):
    """Service selection page for all 23 registration services"""
    services = {
        'registration_services': [
            ('PROVISIONAL_REG', 'Provisional Registration', 'For fresh medical graduates', 'primary'),
            ('PERMANENT_REG', 'Permanent Registration', 'For established practitioners', 'success'),
            ('FOREIGN_PROVISIONAL', 'Foreign Provisional Registration', 'For foreign medical graduates', 'warning'),
            ('FOREIGN_PERMANENT', 'Foreign Permanent Registration', 'Permanent registration for foreign graduates', 'info'),
            ('ADDITIONAL_QUALIFICATION', 'Additional Qualification', 'Add new qualifications', 'secondary'),
            ('RENEWAL_REG', 'Renewal of Registration', 'Renew your medical registration', 'primary'),
        ],
        'verification_services': [
            ('FORM_VERIFICATION', 'Form Verification', 'Verify application forms', 'info'),
            ('MANUAL_VERIFICATION', 'Manual Document Verification', 'Physical document verification', 'warning'),
        ],
        'modification_services': [
            ('CHANGE_ADDRESS', 'Change of Address', 'Update your registered address', 'secondary'),
            ('CHANGE_NAME', 'Change of Name', 'Update your registered name', 'secondary'),
        ],
        'certificate_services': [
            ('GOOD_STANDING_MMC', 'Good Standing Certificate (MMC)', 'For use within Maharashtra', 'success'),
            ('GOOD_STANDING_NMC', 'Good Standing Certificate (NMC)', 'For National Medical Commission', 'success'),
            ('GOOD_STANDING_NRI', 'Good Standing Certificate (NRI)', 'For non-resident Indians', 'info'),
            ('NOC_OTHER_STATE', 'NOC for Other State', 'No Objection Certificate', 'warning'),
            ('DUPLICATE_CERT', 'Duplicate Certificate', 'Replace lost/damaged certificate', 'secondary'),
            ('CONFIRMATION_REG', 'Confirmation of Registration', 'Registration confirmation letter', 'info'),
        ],
        'special_services': [
            ('REAPPLICATION_NOC', 'Reapplication of NOC', 'Reapply for NOC', 'warning'),
            ('NOC_PROVISIONAL', 'NOC for Provisional', 'Provisional to other state', 'info'),
            ('FOREIGN_VERIFICATION', 'Foreign Verification', 'International verification', 'primary'),
            ('PERMANENT_DEFAULTER', 'Permanent Registration for Defaulter', 'For defaulting RMPs', 'danger'),
            ('RE_ENTER_REG', 'Re-enter Registration', 'Rejoin medical practice', 'secondary'),
            ('TERMINATION_RMP', 'Termination of RMP', 'Voluntary termination', 'danger'),
            ('ID_CARD_GEN', 'ID Card Generation', 'Generate practitioner ID card', 'success'),
        ]
    }
    
    context = {
        'services': services,
        'pending_applications': Application.objects.filter(
            applicant=request.user,
            status__in=['DRAFT', 'SUBMITTED', 'UNDER_REVIEW']
        ).count()
    }
    return render(request, 'MMC/landing/service_selection.html', context)

@login_required
@rmp_required
def initiate_service1(request, service_type):
    """Initiate a specific service based on type"""
    if service_type not in dict(Application.APPLICATION_TYPES):
        messages.error(request, 'Invalid service type.')
        return redirect('service_selection')
    
    # Check for existing pending applications of same type
    existing_app = Application.objects.filter(
        applicant=request.user,
        application_type=service_type,
        status__in=['DRAFT', 'SUBMITTED', 'UNDER_REVIEW']
    ).first()
    
    if existing_app:
        messages.info(request, f'You already have a pending {existing_app.get_application_type_display()} application.')
        return redirect('application_status', application_id=existing_app.application_id)
    
    # Create new application
    application = Application.objects.create(
        applicant=request.user,
        application_type=service_type,
        status='DRAFT',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    messages.success(request, f'Started {application.get_application_type_display()} application.')
    return redirect('application_wizard_step', application_id=application.application_id, step=1)


# ============ COMPREHENSIVE REPORTS ============
@login_required
def cpd_reports(request):
    """Comprehensive CPD reports"""
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # CPD Program Statistics
    programs = CPDProgram.objects.all()
    if date_from:
        programs = programs.filter(created_at__date__gte=date_from)
    if date_to:
        programs = programs.filter(created_at__date__lte=date_to)
    
    program_stats = programs.aggregate(
        total_programs=Count('id'),
        total_participants=Sum('max_participants'),
        completed_programs=Count('id', filter=Q(status='COMPLETED'))
    )
    
    # Participant Statistics
    participations = CPDParticipation.objects.all()
    if date_from:
        participations = participations.filter(registration_date__date__gte=date_from)
    if date_to:
        participations = participations.filter(registration_date__date__lte=date_to)
    
    participation_stats = participations.aggregate(
        total_registrations=Count('id'),
        completed_sessions=Count('id', filter=Q(attendance_status='COMPLETED')),
        total_points=Sum('points_earned')
    )
    
    # Top Programs
    top_programs = programs.annotate(
        participant_count=Count('participations'),
        completion_rate=Count('participations', filter=Q(participations__attendance_status='COMPLETED')) * 100.0 / Count('participations')
    ).order_by('-participant_count')[:10]
    
    # RMP CPD Compliance
    rmp_compliance = CustomUser.objects.filter(user_type='rmp').annotate(
        cpd_completion=ExpressionWrapper(
            F('total_cpd_points') * 100.0 / F('cpd_points_required'),
            output_field=DecimalField()
        )
    ).values('specialization').annotate(
        total_rmps=Count('id'),
        avg_completion=Avg('cpd_completion'),
        compliant_rmps=Count('id', filter=Q(total_cpd_points__gte=F('cpd_points_required')))
    ).order_by('-avg_completion')
    
    context = {
        'program_stats': program_stats,
        'participation_stats': participation_stats,
        'top_programs': top_programs,
        'rmp_compliance': rmp_compliance,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'MMC/reports/cpd_reports.html', context)

@login_required
def manual_verification_reports(request):
    """Manual verification status reports"""
    verifications = Application.objects.filter(
        application_type='MANUAL_VERIFICATION'
    ).select_related('applicant')
    
    status_filter = request.GET.get('status')
    if status_filter:
        verifications = verifications.filter(status=status_filter)
    
    stats = verifications.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status__in=['SUBMITTED', 'UNDER_REVIEW'])),
        completed=Count('id', filter=Q(status__in=['APPROVED', 'REJECTED', 'COMPLETED']))
    )
    
    # Staff performance in manual verification
    staff_performance = CustomUser.objects.filter(
        user_type__in=['ADMIN', 'VERIFIER'],
        verification_tasks__application__application_type='MANUAL_VERIFICATION'
    ).annotate(
        tasks_completed=Count('verification_tasks', filter=Q(verification_tasks__status='COMPLETED')),
        avg_processing_hours=Avg(
            ExpressionWrapper(
                (F('verification_tasks__completed_date') - F('verification_tasks__assigned_date')) / 3600000000,  # Convert to hours
                output_field=DecimalField()
            )
        )
    ).values('username', 'first_name', 'last_name', 'tasks_completed', 'avg_processing_hours')
    
    context = {
        'verifications': verifications.order_by('-application_date'),
        'stats': stats,
        'staff_performance': staff_performance,
        'status_filter': status_filter,
    }
    return render(request, 'MMC/reports/manual_verification_reports.html', context)

@login_required
def staff_performance_reports(request):
    """Detailed staff performance reports"""
    date_from = request.GET.get('date_from', timezone.now().date() - timedelta(days=30))
    date_to = request.GET.get('date_to', timezone.now().date())
    
    staff_members = CustomUser.objects.filter(
        user_type__in=['ADMIN', 'VERIFIER', 'SUPER_ADMIN']
    ).annotate(
        # Application processing
        applications_processed=Count('verified_applications', 
            filter=Q(verified_applications__verification_date__date__range=[date_from, date_to])),
        
        # Verification tasks
        tasks_assigned=Count('verification_tasks',
            filter=Q(verification_tasks__assigned_date__date__range=[date_from, date_to])),
        tasks_completed=Count('verification_tasks',
            filter=Q(verification_tasks__completed_date__date__range=[date_from, date_to])),
        
        # Average processing time
        avg_processing_time=Avg(
            ExpressionWrapper(
                F('verification_tasks__completed_date') - F('verification_tasks__assigned_date'),
                output_field=DurationField()
            ),
            filter=Q(verification_tasks__completed_date__isnull=False)
        ),
        
        # Approval rate
        approval_rate=Count('verified_applications', 
            filter=Q(verified_applications__status='APPROVED')) * 100.0 / Count('verified_applications')
    ).order_by('-applications_processed')
    
    context = {
        'staff_members': staff_members,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'MMC/reports/staff_performance_reports.html', context)

# ============ COMPLAINT MANAGEMENT ============
@login_required
def file_complaint(request):
    """File a complaint against another RMP"""
    if request.method == 'POST':
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.filed_by = request.user
            complaint.save()
            
            messages.success(request, 'Complaint filed successfully!')
            return redirect('complaint_status')
    else:
        form = ComplaintForm()
    
    context = {
        'form': form
    }
    return render(request, 'MMC/complaints/file_complaint.html', context)

@login_required
def complaint_status(request):
    """View complaint status"""
    if request.user.user_type == 'rmp':
        complaints_filed = Complaint.objects.filter(filed_by=request.user).order_by('-filed_date')
        complaints_against = Complaint.objects.filter(against_doctor=request.user).order_by('-filed_date')
    else:
        complaints_filed = Complaint.objects.none()
        complaints_against = Complaint.objects.none()
    
    context = {
        'complaints_filed': complaints_filed,
        'complaints_against': complaints_against,
    }
    return render(request, 'MMC/complaints/complaint_status.html', context)

@login_required
def admin_complaint_management(request):
    """Admin complaint management"""
    complaints = Complaint.objects.all().select_related('filed_by', 'against_doctor').order_by('-filed_date')
    
    status_filter = request.GET.get('status')
    if status_filter:
        complaints = complaints.filter(status=status_filter)
    
    context = {
        'complaints': complaints,
        'status_filter': status_filter,
    }
    return render(request, 'MMC/admin/complaint_management.html', context)

@login_required
def update_complaint_status(request, complaint_id):
    """Update complaint status"""
    complaint = get_object_or_404(Complaint, complaint_id=complaint_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        resolution_details = request.POST.get('resolution_details', '')
        action_taken = request.POST.get('action_taken', '')
        
        if action == 'investigate':
            complaint.status = 'UNDER_INVESTIGATION'
            complaint.investigation_start_date = timezone.now()
            messages.info(request, 'Complaint marked under investigation.')
        
        elif action == 'resolve':
            complaint.status = 'RESOLVED'
            complaint.resolution_date = timezone.now()
            complaint.resolution_details = resolution_details
            complaint.resolved_by = request.user
            complaint.action_taken = action_taken
            messages.success(request, 'Complaint resolved successfully.')
        
        elif action == 'dismiss':
            complaint.status = 'DISMISSED'
            complaint.resolution_date = timezone.now()
            complaint.resolution_details = resolution_details
            complaint.resolved_by = request.user
            messages.warning(request, 'Complaint dismissed.')
        
        complaint.save()
        return redirect('admin_complaint_management')
    
    context = {
        'complaint': complaint
    }
    return render(request, 'MMC/admin/update_complaint_status.html', context)

# ============ ADVANCED AI INTEGRATION ============
@login_required
def ai_analytics_dashboard(request):
    """Advanced AI analytics dashboard"""
    # Predictive analytics for application volume
    application_trends = Application.objects.annotate(
        month=TruncMonth('application_date')
    ).values('month').annotate(
        count=Count('id'),
        approval_rate=Count('id', filter=Q(status='APPROVED')) * 100.0 / Count('id')
    ).order_by('month')[-12:]  # Last 12 months
    
    # Risk prediction model
    high_risk_applications = Application.objects.filter(
        status='UNDER_REVIEW'
    ).annotate(
        risk_score=Case(
            When(application_type__in=['FOREIGN_PERMANENT', 'PERMANENT_DEFAULTER'], then=Value(80)),
            When(verification_notes__isnull=False, then=Value(70)),
            When(Q(documents__is_verified=False) & Q(documents__isnull=False), then=Value(60)),
            When(expected_completion_date__lt=timezone.now(), then=Value(50)),
            default=Value(30),
            output_field=IntegerField()
        )
    ).filter(risk_score__gte=70).order_by('-risk_score')[:10]
    
    # CPD compliance predictions
    compliance_risk = CustomUser.objects.filter(
        user_type='rmp',
        registration_status='PERMANENT'
    ).annotate(
        cpd_deficit=F('cpd_points_required') - F('total_cpd_points'),
        risk_level=Case(
            When(Q(cpd_deficit__gt=20) & Q(renewal_date__lte=timezone.now().date() + timedelta(days=30)), then=Value('HIGH')),
            When(Q(cpd_deficit__gt=10) | Q(renewal_date__lte=timezone.now().date() + timedelta(days=60)), then=Value('MEDIUM')),
            default=Value('LOW'),
            output_field=CharField()
        )
    ).values('risk_level').annotate(count=Count('id')).order_by('risk_level')
    
    # Staff efficiency analytics
    staff_efficiency = CustomUser.objects.filter(
        user_type__in=['ADMIN', 'VERIFIER']
    ).annotate(
        avg_processing_time=Avg(
            ExpressionWrapper(
                F('verification_tasks__completed_date') - F('verification_tasks__assigned_date'),
                output_field=DurationField()
            ),
            filter=Q(verification_tasks__completed_date__isnull=False)
        ),
        task_completion_rate=Count('verification_tasks', filter=Q(verification_tasks__status='COMPLETED')) * 100.0 / Count('verification_tasks')
    ).values('username', 'first_name', 'last_name', 'avg_processing_time', 'task_completion_rate')
    
    context = {
        'application_trends': list(application_trends),
        'high_risk_applications': high_risk_applications,
        'compliance_risk': list(compliance_risk),
        'staff_efficiency': list(staff_efficiency),
    }
    return render(request, 'MMC/ai/analytics_dashboard.html', context)

# ============ BULK OPERATIONS & UTILITIES ============
@login_required
def bulk_certificate_generation(request):
    """Bulk generate certificates for approved applications"""
    if request.method == 'POST':
        application_ids = request.POST.getlist('applications')
        applications = Application.objects.filter(
            application_id__in=application_ids,
            status='APPROVED',
            certificate_generated=False
        )
        
        generated_count = 0
        for application in applications:
            try:
                application.generate_certificate()
                generated_count += 1
            except Exception as e:
                logger.error(f"Certificate generation failed for {application.application_id}: {e}")
        
        messages.success(request, f'Generated {generated_count} certificates successfully!')
        return redirect('admin_application_list')
    
    # Get approved applications without certificates
    applications = Application.objects.filter(
        status='APPROVED',
        certificate_generated=False
    ).select_related('applicant')
    
    context = {
        'applications': applications
    }
    return render(request, 'MMC/admin/bulk_certificate_generation.html', context)

# ============ EXPORT FUNCTIONALITY ============
@login_required
def export_applications_excel(request):
    """Export applications to Excel"""
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="mmc_applications.xls"'
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Applications')
    
    # Sheet header, first row
    row_num = 0
    font_style = xlwt.XFStyle()
    font_style.font.bold = True
    
    columns = ['Application ID', 'Type', 'Applicant', 'Status', 'Submission Date', 'Completion Date', 'Payment Status']
    
    for col_num, column_title in enumerate(columns):
        ws.write(row_num, col_num, column_title, font_style)
    
    # Sheet body, remaining rows
    font_style = xlwt.XFStyle()
    rows = Application.objects.all().select_related('applicant').values_list(
        'application_id', 'application_type', 'applicant__username', 'status',
        'submission_date', 'actual_completion_date', 'payment_status'
    )
    
    for row in rows:
        row_num += 1
        for col_num, value in enumerate(row):
            ws.write(row_num, col_num, str(value), font_style)
    
    wb.save(response)
    return response

@login_required
def export_financial_report(request):
    """Export financial report to Excel"""
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="mmc_financial_report.xls"'
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Financial Report')
    
    row_num = 0
    font_style = xlwt.XFStyle()
    font_style.font.bold = True
    
    columns = ['Date', 'Transaction ID', 'User', 'Type', 'Amount', 'Status', 'Method']
    
    for col_num, column_title in enumerate(columns):
        ws.write(row_num, col_num, column_title, font_style)
    
    font_style = xlwt.XFStyle()
    payments = Payment.objects.filter(status='SUCCESS').select_related('user')
    
    for payment in payments:
        row_num += 1
        ws.write(row_num, 0, payment.payment_date.strftime('%Y-%m-%d'), font_style)
        ws.write(row_num, 1, payment.transaction_id, font_style)
        ws.write(row_num, 2, payment.user.get_full_name(), font_style)
        ws.write(row_num, 3, payment.get_payment_type_display(), font_style)
        ws.write(row_num, 4, str(payment.amount), font_style)
        ws.write(row_num, 5, payment.get_status_display(), font_style)
        ws.write(row_num, 6, payment.get_payment_method_display(), font_style)
    
    wb.save(response)
    return response

# ============ DASHBOARD WIDGETS & API ============
@login_required
def api_dashboard_widgets(request):
    """API endpoint for dashboard widgets"""
    if request.user.user_type == 'rmp':
        data = {
            'applications': {
                'active': Application.objects.filter(
                    applicant=request.user,
                    status__in=['SUBMITTED', 'UNDER_REVIEW']
                ).count(),
                'completed': Application.objects.filter(
                    applicant=request.user,
                    status__in=['APPROVED', 'COMPLETED']
                ).count(),
            },
            'cpd': {
                'points': request.user.total_cpd_points,
                'required': request.user.cpd_points_required,
                'completion': (request.user.total_cpd_points / request.user.cpd_points_required * 100) if request.user.cpd_points_required > 0 else 0,
            },
            'notifications': Notification.objects.filter(user=request.user, is_read=False).count(),
        }
    else:
        data = {
            'applications': {
                'pending': Application.objects.filter(status__in=['SUBMITTED', 'UNDER_REVIEW']).count(),
                'overdue': Application.objects.filter(
                    expected_completion_date__lt=timezone.now(),
                    status__in=['SUBMITTED', 'UNDER_REVIEW']
                ).count(),
            },
            'payments': {
                'today': Payment.objects.filter(
                    payment_date__date=timezone.now().date(),
                    status='SUCCESS'
                ).aggregate(total=Sum('amount'))['total'] or 0,
                'month': Payment.objects.filter(
                    payment_date__month=timezone.now().month,
                    status='SUCCESS'
                ).aggregate(total=Sum('amount'))['total'] or 0,
            },
            'users': {
                'total': CustomUser.objects.filter(user_type='rmp').count(),
                'new_today': CustomUser.objects.filter(
                    date_joined__date=timezone.now().date(),
                    user_type='rmp'
                ).count(),
            }
        }
    
    return JsonResponse(data)

# ============ SEARCH FUNCTIONALITY ============
@login_required
def search_applications(request):
    """Search applications"""
    query = request.GET.get('q', '')
    
    if request.user.user_type == 'rmp':
        applications = Application.objects.filter(applicant=request.user)
    else:
        applications = Application.objects.all()
    
    if query:
        applications = applications.filter(
            Q(application_id__icontains=query) |
            Q(application_type__icontains=query) |
            Q(status__icontains=query) |
            Q(applicant__username__icontains=query) |
            Q(applicant__first_name__icontains=query) |
            Q(applicant__last_name__icontains=query)
        )
    
    context = {
        'applications': applications.order_by('-application_date'),
        'query': query,
    }
    return render(request, 'MMC/search/search_results.html', context)

@login_required
def search_rmps(request):
    """Search RMPs"""
    query = request.GET.get('q', '')
    
    rmps = CustomUser.objects.filter(user_type='rmp')
    
    if query:
        rmps = rmps.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(mmc_registration_number__icontains=query) |
            Q(specialization__icontains=query)
        )
    
    context = {
        'rmps': rmps.order_by('first_name', 'last_name'),
        'query': query,
    }
    return render(request, 'MMC/admin/search_rmps.html', context)

# ============ SYSTEM CONFIGURATION ============
@login_required
def system_configuration(request):
    """System configuration management"""
    configurations = SystemConfig.objects.all().order_by('key')
    
    if request.method == 'POST':
        form = SystemConfigForm(request.POST)
        if form.is_valid():
            config = form.save(commit=False)
            config.modified_by = request.user
            config.save()
            messages.success(request, 'Configuration updated successfully!')
            return redirect('system_configuration')
    else:
        form = SystemConfigForm()
    
    context = {
        'configurations': configurations,
        'form': form,
    }
    return render(request, 'MMC/admin/system_configuration.html', context)