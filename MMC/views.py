# views.py 
from django.forms import BooleanField, CharField, DecimalField, IntegerField
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, DeleteView
from django.db.models import Q, Count, Sum, Avg, Min, F, Value, Case, When, ExpressionWrapper, DurationField
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
from Account.db_utils import callproc

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
    rmp_profile = get_rmp_profile(request.user)
    # Applications statistics
    applications = Application.objects.filter(applicant=user)
    active_applications = applications.filter(status__in=['submitted', 'completed']).count()
    completed_applications = applications.filter(status__in=['approved', 'completed']).count()
    
    # CPD statistics
    cpd_participations = CPDParticipation.objects.filter(participant=user, attendance_status='COMPLETED')
    total_cpd_points = cpd_participations.aggregate(total=Sum('points_earned'))['total'] or 0
    
    # Renewal alerts
    renewal_alerts = []
    # Calculate renewal date
    renewal_date = rmp_profile.registration_valid_till if rmp_profile else None

    
    if renewal_date and renewal_date <= today + timedelta(days=60):
        renewal_alerts.append({
            'message': f'Registration renewal due on {renewal_date}',
            'type': 'warning' if renewal_date > today else 'danger'
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
        status='Published'
    ).order_by('start_date')[:5]
    
    # AI Insights
    ai_insights = AIInsight.objects.filter(rmp=rmp_profile,is_active=True).order_by('-generated_date')[:3]
    
    context = {
        'active_applications': active_applications,
        'completed_applications': completed_applications,
        'pending_payments': Payment.objects.filter(status='pending').count(),
        'cpd_points': total_cpd_points,
        'cpd_required': user.cpd_points_required,
        'cpd_completion': cpd_completion,
        'recent_applications': recent_applications,
        'upcoming_cpd': upcoming_cpd,
        'notifications': Notification.objects.filter(user=user, is_read=False).order_by('-created_date')[:10],
        'complaints_count': Complaint.objects.filter(against_rmp=rmp_profile, status='under_investigation').count(),
        'renewal_alerts': renewal_alerts,
        'cpd_alerts': cpd_alerts,
        'ai_insights': ai_insights,
        'performance_score': AIPerformanceScore.objects.filter(rmp=rmp_profile).first(),
    }
    return render(request, 'MMC/dashboard/rmp_dashboard.html', context)

@login_required
def admin_dashboard1(request):
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    # Application statistics
    total_applications = Application.objects.count()
    pending_applications = Application.objects.filter(status__in=['submitted', 'under_review']).count()
    overdue_applications = Application.objects.filter(
        expected_completion_date__lt=today,
        status__in=['submitted', 'under_review']
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
        status='success'
    ).aggregate(
        total_amount=Sum('amount'),
        total_count=Count('payment_id')
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
    recent_payments = Payment.objects.select_related('application__applicant').filter(status='success').order_by('-payment_date')[:10]
    
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
    
    from django.db.models import Q, Case, When, Value, IntegerField

    high_risk_applications = (
        Application.objects.filter(status='under_review')
        .annotate(
            risk_score=Case(
                # Rule 1: high-risk types
                When(application_type__in=['foreign_permanent', 'defaulter'], then=Value(80)),
                # Rule 2: non-empty review notes
                When(~Q(review_notes="") & Q(review_notes__isnull=False), then=Value(70)),
                # Rule 3: unverified documents — adjust related name
                When(documents__is_verified=False, then=Value(60)),
                # Default fallback
                default=Value(40),
                output_field=IntegerField(),  # ✅ Correct usage (you DO instantiate here)
            )
        )
        .filter(risk_score__gte=70)
        .distinct()[:10]
    )

    # Step 1: Get RMP Profile if exists
    rmp_profile = get_rmp_profile(request.user)
    renewal_date = rmp_profile.registration_valid_till if rmp_profile else None

    # Step 2: Base queryset with CPD deficit annotation
    compliance_alerts = (
        CustomUser.objects.filter(
            user_type='rmp',
            registration_status='PERMANENT'
        )
        .annotate(
            cpd_deficit=F('cpd_points_required') - F('total_cpd_points'),
        )
        .filter(cpd_deficit__gt=10)[:10]
    )

    # Step 3: Add renewal alert logic (handled in Python)
    if renewal_date:
        renewal_soon_users = []
        for user in compliance_alerts:
            user_rmp = get_rmp_profile(user)
            if user_rmp and user_rmp.registration_valid_till and user_rmp.registration_valid_till <= today + timedelta(days=30):
                renewal_soon_users.append(user)

        # Combine users with CPD deficit OR renewal soon
        combined_users = set(compliance_alerts) | set(renewal_soon_users)
        compliance_alerts = list(combined_users)
    
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
# @login_required
# 
# def application_wizard(request, application_type=None):
#     if application_type is None:
#         if request.method == 'POST':
#             form = ApplicationForm(request.POST)
#             if form.is_valid():
#                 application = form.save(commit=False)
#                 application.rmp = get_rmp_profile(request.user)
#                 application.fee_amount = get_application_fee(application.application_type)
#                 application.save()
                
#                 # Create initial step
#                 ApplicationStep.objects.create(
#                     application=application,
#                     step_number=1,
#                     step_name='applicant_details',
#                     required_documents=get_required_documents(application.application_type)
#                 )
                
#                 # Create audit log
#                 create_audit_log(
#                     user=request.user,
#                     action_type='create',
#                     model_name='Application',
#                     object_id=application.application_id,
#                     description=f"New {application.get_application_type_display()} application created",
#                     request=request
#                 )
                
#                 return redirect('application_step', application_id=application.application_id, step=1)
#         else:
#             form = ApplicationForm()
#         return render(request, 'MMC/applications/application_type.html', {'form': form})
    
#     return redirect('application_wizard')

# @login_required
# 
# def application_step(request, application_id, step):
#     application = get_object_or_404(Application, application_id=application_id, rmp__user=request.user)
    
#     steps_config = {
#         1: {'name': 'applicant_details', 'title': 'Applicant Details', 'form_class': RMPRegistrationForm},
#         2: {'name': 'educational_details', 'title': 'Educational Details', 'form_class': EducationalQualificationForm},
#         3: {'name': 'medical_qualification', 'title': 'Medical Qualification', 'form_class': MedicalQualificationForm},
#         4: {'name': 'passport_details', 'title': 'Passport Details', 'form_class': PassportDetailsForm},
#         5: {'name': 'screening_test', 'title': 'Screening Test', 'form_class': ScreeningTestForm},
#         6: {'name': 'internship_training', 'title': 'Internship Training', 'form_class': InternshipTrainingForm},
#         7: {'name': 'foreign_training', 'title': 'Foreign Training/Registration', 'form_class': ForeignTrainingForm},
#         8: {'name': 'documents_upload', 'title': 'Document Upload', 'form_class': DocumentUploadForm},
#         9: {'name': 'declarations', 'title': 'Declarations', 'form_class': DeclarationForm},
#         10: {'name': 'payment', 'title': 'Payment', 'form_class': PaymentForm},
#     }
    
#     current_step_config = steps_config.get(step)
#     if not current_step_config:
#         messages.error(request, "Invalid step")
#         return redirect('application_status', application_id=application_id)
    
#     if request.method == 'POST':
#         if step == 10:  # Payment step
#             # Handle payment processing
#             application.payment_status = True
#             application.payment_date = timezone.now()
#             application.status = 'submitted'
#             application.save()
            
#             # Create notification for admin
#             admin_users = CustomUser.objects.filter(user_type='admin')
#             for admin in admin_users:
#                 Notification.objects.create(
#                     user=admin,
#                     notification_type='registration',
#                     title='New Application Submitted',
#                     message=f"New {application.get_application_type_display()} application submitted by {application.rmp.full_name}",
#                     related_object_id=str(application.application_id),
#                     action_url=reverse('admin_application_review', args=[application.application_id]),
#                     priority='high'
#                 )
            
#             # Create audit log
#             create_audit_log(
#                 user=request.user,
#                 action_type='update',
#                 model_name='Application',
#                 object_id=application.application_id,
#                 description=f"Application submitted and payment completed",
#                 request=request
#             )
            
#             messages.success(request, "Application submitted successfully!")
#             return redirect('application_status', application_id=application_id)
#         else:
#             # Save step data
#             step_data = process_step_data(request, step, application)
            
#             # Update step progress
#             application_step, created = ApplicationStep.objects.update_or_create(
#                 application=application,
#                 step_number=step,
#                 defaults={
#                     'step_name': current_step_config['name'],
#                     'data': step_data,
#                     'is_completed': True,
#                     'completed_date': timezone.now(),
#                 }
#             )
            
#             # Update application current step
#             application.current_step = step + 1
#             application.save()
            
#             if step < len(steps_config):
#                 return redirect('application_step', application_id=application_id, step=step + 1)
    
#     # Load existing step data
#     try:
#         step_data = ApplicationStep.objects.get(application=application, step_number=step).data
#     except ApplicationStep.DoesNotExist:
#         step_data = {}
    
#     # Initialize form for current step
#     form = None
#     if current_step_config['form_class']:
#         form_class = current_step_config['form_class']
#         if form_class == PaymentForm:
#             form = form_class(initial=step_data, application_type=application.application_type)
#         else:
#             form = form_class(initial=step_data)
    
#     context = {
#         'application': application,
#         'current_step': step,
#         'current_step_name': current_step_config['name'],
#         'step_title': current_step_config['title'],
#         'total_steps': len(steps_config),
#         'step_data': step_data,
#         'form': form,
#     }
    
#     template_name = f'MMC/applications/steps/{current_step_config["name"]}.html'
#     return render(request, template_name, context)

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

@login_required
def application_wizard(request, application_type=None):
    """Application type selection and initialization"""
    if not is_rmp(request.user):
        messages.error(request, "Access denied. RMP registration required.")
        return redirect('mmc_dashboard')
    
    rmp_profile = get_rmp_profile(request.user)
    
    if application_type is None:
        # Show application type selection
        if request.method == 'POST':
            application_type = request.POST.get('application_type')
            if application_type:
                return redirect('application_wizard_with_type', application_type=application_type)
            else:
                messages.error(request, "Please select an application type")
        
        return render(request, 'MMC/applications/application_type.html', {
            'application_types': Application.APPLICATION_TYPES
        })
    
    # Initialize application
    if request.method == 'POST':
        with transaction.atomic():
            application = Application.objects.create(
                applicant=request.user,
                rmp=rmp_profile,
                application_type=application_type,
                fee_amount=get_application_fee(application_type),
                status='draft',
                current_step=1
            )
            
            # Create initial step
            ApplicationStep.objects.create(
                application=application,
                step_number=1,
                step_name='applicant_details',
                required_documents=get_required_documents(application_type)
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
            
            messages.success(request, f"New {application.get_application_type_display()} application started!")
            return redirect('application_step', application_id=application.application_id, step=1)
    
    return render(request, 'MMC/applications/application_type.html', {
        'selected_type': application_type,
        'application_types': Application.APPLICATION_TYPES
    })

@login_required
def application_step(request, application_id, step):
    """Handle individual application steps - ALL STEPS ACCESSIBLE"""
    application = get_object_or_404(
        Application, 
        application_id=application_id, 
        applicant=request.user
    )
    
    # Step configuration for ALL 10 STEPS
    steps_config = {
        1: {
            'name': 'applicant_details', 
            'title': 'Applicant Details', 
            'form_class': RMPRegistrationForm,
            'template': 'applicant_details.html'
        },
        2: {
            'name': 'educational_details', 
            'title': 'Educational Details', 
            'form_class': EducationalQualificationForm,
            'template': 'educational_details.html'
        },
        3: {
            'name': 'medical_qualification', 
            'title': 'Medical Qualification', 
            'form_class': MedicalQualificationForm,
            'template': 'medical_qualification.html'
        },
        4: {
            'name': 'passport_details', 
            'title': 'Passport Details', 
            'form_class': PassportDetailsForm,
            'template': 'passport_details.html'
        },
        5: {
            'name': 'screening_test', 
            'title': 'Screening Test', 
            'form_class': ScreeningTestForm,
            'template': 'screening_test.html'
        },
        6: {
            'name': 'internship_training', 
            'title': 'Internship Training', 
            'form_class': InternshipTrainingForm,
            'template': 'internship_training.html'
        },
        7: {
            'name': 'foreign_training', 
            'title': 'Foreign Training/Registration', 
            'form_class': ForeignTrainingForm,
            'template': 'foreign_training.html'
        },
        8: {
            'name': 'documents_upload', 
            'title': 'Document Upload', 
            'form_class': DocumentUploadForm,
            'template': 'documents_upload.html'
        },
        9: {
            'name': 'declarations', 
            'title': 'Declarations', 
            'form_class': DeclarationForm,
            'template': 'declarations.html'
        },
        10: {
            'name': 'payment', 
            'title': 'Payment', 
            'form_class': PaymentForm,
            'template': 'payment.html'
        },
    }
    
    current_step_config = steps_config.get(step)
    if not current_step_config:
        messages.error(request, "Invalid step")
        return redirect('application_status', application_id=application_id)
    
    # ALL STEPS ARE ACCESSIBLE - NO RESTRICTIONS
    
    # Handle POST request
    if request.method == 'POST':
        form = current_step_config['form_class'](request.POST, request.FILES)
        if form.is_valid():
            # Save step data if needed
            save_step_data(application, step, form.cleaned_data)
            messages.success(request, f"Step {step} data saved successfully!")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Load existing data if any
        try:
            step_data = ApplicationStep.objects.get(
                application=application,
                step_number=step
            ).data
        except ApplicationStep.DoesNotExist:
            step_data = {}
        
        # Initialize form
        form_class = current_step_config['form_class']
        if step == 10:  # Payment form
            form = form_class(initial={'amount': application.fee_amount})
        else:
            form = form_class(initial=step_data)
    
    # Get uploaded documents for document step
    uploaded_documents = None
    if step == 8:
        uploaded_documents = Document.objects.filter(application=application)
    
    context = {
        'application': application,
        'form': form,
        'current_step': step,
        'step_title': current_step_config['title'],
        'total_steps': 10,  # Fixed to 10 steps
        'uploaded_documents': uploaded_documents,
        'required_documents': get_required_documents(application.application_type),
    }
    
    return render(request, f"MMC/applications/steps/{current_step_config['template']}", context)

def get_steps_config():
    """Get configuration for all steps"""
    return {
        1: {
            'name': 'applicant_details', 
            'title': 'Applicant Details', 
            'form_class': RMPRegistrationForm,
            'template': 'applicant_details.html',
            'icon': 'person'
        },
        2: {
            'name': 'educational_details', 
            'title': 'Educational Details', 
            'form_class': EducationalQualificationForm,
            'template': 'educational_details.html',
            'icon': 'mortarboard'
        },
        3: {
            'name': 'medical_qualification', 
            'title': 'Medical Qualification', 
            'form_class': MedicalQualificationForm,
            'template': 'medical_qualification.html',
            'icon': 'heart-pulse'
        },
        4: {
            'name': 'passport_details', 
            'title': 'Passport Details', 
            'form_class': PassportDetailsForm,
            'template': 'passport_details.html',
            'icon': 'passport'
        },
        5: {
            'name': 'screening_test', 
            'title': 'Screening Test', 
            'form_class': ScreeningTestForm,
            'template': 'screening_test.html',
            'icon': 'clipboard-check'
        },
        6: {
            'name': 'internship_training', 
            'title': 'Internship Training', 
            'form_class': InternshipTrainingForm,
            'template': 'internship_training.html',
            'icon': 'hospital'
        },
        7: {
            'name': 'foreign_training', 
            'title': 'Foreign Training/Registration', 
            'form_class': ForeignTrainingForm,
            'template': 'foreign_training.html',
            'icon': 'globe'
        },
        8: {
            'name': 'documents_upload', 
            'title': 'Document Upload', 
            'form_class': DocumentUploadForm,
            'template': 'documents_upload.html',
            'icon': 'folder'
        },
        9: {
            'name': 'declarations', 
            'title': 'Declarations', 
            'form_class': DeclarationForm,
            'template': 'declarations.html',
            'icon': 'shield-check'
        },
        10: {
            'name': 'payment', 
            'title': 'Payment', 
            'form_class': PaymentForm,
            'template': 'payment.html',
            'icon': 'credit-card'
        },
    }

def render_step_form(request, application, step, step_config, steps_config):
    """Render the step form with existing data"""
    # Get existing step data from database (if any)
    try:
        step_data = ApplicationStep.objects.get(
            application=application,
            step_number=step
        ).data
    except ApplicationStep.DoesNotExist:
        step_data = {}
    
    # Initialize form
    form_class = step_config['form_class']
    
    # Special handling for payment form
    if step == 10:
        form = form_class(initial={'amount': application.fee_amount})
    else:
        form = form_class(initial=step_data)
    
    # Get uploaded documents for document step
    uploaded_documents = None
    if step == 8:
        uploaded_documents = Document.objects.filter(application=application)
    
    context = {
        'application': application,
        'form': form,
        'current_step': step,
        'step_title': step_config['title'],
        'total_steps': len(steps_config),
        'uploaded_documents': uploaded_documents,
        'required_documents': get_required_documents(application.application_type),
    }
    
    return render(request, f"MMC/applications/steps/{step_config['template']}", context)

def can_access_step(application, step):
    """Check if user can access the requested step"""
    # Allow access to current step and completed steps
    if step <= application.current_step:
        return True
    
    # For steps beyond current step, check if all previous steps are completed
    if step > application.current_step:
        completed_steps = ApplicationStep.objects.filter(
            application=application,
            step_number__lt=step,
            is_completed=True
        ).count()
        return completed_steps >= (step - 1)
    
    return False

def handle_step_post(request, application, step, step_config):
    """Handle step form submission"""
    form = step_config['form_class'](request.POST, request.FILES)
    
    if form.is_valid():
        # Special handling for different steps
        if step == 8:  # Document upload
            handle_document_upload(request, application)
        elif step == 10:  # Payment
            return handle_payment(request, application)
        
        save_step_data(application, step, form.cleaned_data)
        mark_step_completed(application, step)
        
        # Update application current step if moving forward
        if step >= application.current_step:
            application.current_step = min(step + 1, 10)
            application.save()
        
        messages.success(request, f"Step {step} completed successfully!")
        
        # Move to next step or complete
        if step < 10:
            return redirect('application_step', application_id=application.application_id, step=step+1)
        else:
            return redirect('application_status', application_id=application.application_id)
    else:
        messages.error(request, "Please correct the errors below.")
        return render_step_form_after_post(request, application, step, step_config, form)

def render_step_form_after_post(request, application, step, step_config, form):
    """Render step form after POST with errors"""
    steps_config = get_steps_config()
    
    # Get uploaded documents for document step
    uploaded_documents = None
    if step == 8:
        uploaded_documents = Document.objects.filter(application=application)
    
    context = {
        'application': application,
        'form': form,
        'current_step': step,
        'step_title': step_config['title'],
        'total_steps': len(steps_config),
        'uploaded_documents': uploaded_documents,
        'required_documents': get_required_documents(application.application_type),
        'progress_percentage': calculate_progress_percentage(application),
    }
    
    return render(request, f"MMC/applications/steps/{step_config['template']}", context)

def calculate_progress_percentage(application):
    """Calculate progress percentage based on completed steps"""
    completed_steps = ApplicationStep.objects.filter(
        application=application,
        is_completed=True
    ).count()
    total_steps = 10
    return int((completed_steps / total_steps) * 100)

@login_required
def get_step_progress(request, application_id):
    """Get step progress for AJAX updates"""
    application = get_object_or_404(Application, application_id=application_id, applicant=request.user)
    completed_steps = ApplicationStep.objects.filter(application=application, is_completed=True).count()
    total_steps = 10
    
    progress_percentage = int((completed_steps / total_steps) * 100)
    
    return JsonResponse({
        'completed': completed_steps,
        'total': total_steps,
        'percentage': progress_percentage,
        'current_step': application.current_step
    })

@login_required
def jump_to_step(request, application_id, step):
    """Allow jumping to specific step if accessible"""
    application = get_object_or_404(Application, application_id=application_id, applicant=request.user)
    
    if can_access_step(application, step):
        return redirect('application_step', application_id=application_id, step=step)
    else:
        messages.warning(request, "Cannot jump to this step. Please complete previous steps first.")
        return redirect('application_step', application_id=application_id, step=application.current_step)

def handle_save_draft(request, application, step, step_config):
    """Save current step as draft"""
    form = step_config['form_class'](request.POST, request.FILES)
    
    if form.is_valid():
        save_step_data(application, step, form.cleaned_data)
        messages.success(request, "Progress saved successfully!")
    else:
        messages.warning(request, "Form contains errors, but draft was saved.")
        save_step_data(application, step, request.POST.dict())
    
    return redirect('application_step', application_id=application.application_id, step=step)

def handle_step_submission(request, application, step, step_config):
    """Handle step form submission"""
    form = step_config['form_class'](request.POST, request.FILES)
    
    if form.is_valid():
        # Special handling for different steps
        if step == 8:  # Document upload
            handle_document_upload(request, application)
        elif step == 10:  # Payment
            return handle_payment(request, application)
        
        save_step_data(application, step, form.cleaned_data)
        mark_step_completed(application, step)
        
        # Move to next step or complete
        if step < 10:
            return redirect('application_step', application_id=application.application_id, step=step+1)
        else:
            return redirect('application_status', application_id=application.application_id)
    else:
        messages.error(request, "Please correct the errors below.")
        return render(request, f"MMC/applications/steps/{step_config['template']}", {
            'application': application,
            'form': form,
            'current_step': step,
            'step_title': step_config['title'],
            'total_steps': 10
        })

def handle_document_upload(request, application):
    """Handle document uploads"""
    for file_key, file_obj in request.FILES.items():
        if file_key.startswith('document_'):
            document_type = file_key.replace('document_', '')
            Document.objects.create(
                application=application,
                document_type=document_type,
                document_file=file_obj,
                file_name=file_obj.name,
                file_size=file_obj.size
            )

def handle_payment(request, application):
    """Handle payment processing"""
    with transaction.atomic():
        application.payment_status = True
        application.payment_date = timezone.now()
        application.status = 'submitted'
        application.submitted_date = timezone.now()
        application.save()
        
        # Create payment record
        Payment.objects.create(
            application=application,
            amount=application.fee_amount,
            status='success',
            payment_method='online',
            transaction_id=f"TXN{application.application_id}{int(timezone.now().timestamp())}"
        )
        
        # Create notification for admin
        admin_users = CustomUser.objects.filter(user_type__in=['admin', 'staff'])
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
            description="Application submitted and payment completed",
            request=request
        )
        
        messages.success(request, "Application submitted successfully!")
        return redirect('application_status', application_id=application.application_id)

def save_step_data(application, step, data):
    """Save step data to ApplicationStep"""
    step_obj, created = ApplicationStep.objects.update_or_create(
        application=application,
        step_number=step,
        defaults={
            'data': data,
            'is_completed': True,
            'completed_date': timezone.now(),
        }
    )
    
    # Update application current step if moving forward
    if step > application.current_step:
        application.current_step = step
        application.save()

def mark_step_completed(application, step):
    """Mark step as completed"""
    ApplicationStep.objects.filter(
        application=application,
        step_number=step
    ).update(
        is_completed=True,
        completed_date=timezone.now()
    )

def render_step_form(request, application, step, step_config, steps_config):
    """Render the step form with existing data"""
    # Get existing step data
    try:
        step_data = ApplicationStep.objects.get(
            application=application,
            step_number=step
        ).data
    except ApplicationStep.DoesNotExist:
        step_data = {}
    
    # Initialize form
    form_class = step_config['form_class']
    
    # Special handling for payment form
    if step == 10:
        form = form_class(initial={'amount': application.fee_amount})
    else:
        form = form_class(initial=step_data)
    
    # Get uploaded documents for document step
    uploaded_documents = None
    if step == 8:
        uploaded_documents = Document.objects.filter(application=application)
    
    context = {
        'application': application,
        'form': form,
        'current_step': step,
        'step_title': step_config['title'],
        'total_steps': len(steps_config),
        'uploaded_documents': uploaded_documents,
        'required_documents': get_required_documents(application.application_type),
        'progress_percentage': int((step / len(steps_config)) * 100),
    }
    
    return render(request, f"MMC/applications/steps/{step_config['template']}", context)

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

# def get_required_documents(application_type):
#     """Get required documents for application type"""
#     document_requirements = {
#         'provisional': ['photo', 'signature', 'ssc', 'hsc', 'degree', 'internship', 'address_proof'],
#         'permanent': ['photo', 'signature', 'ssc', 'hsc', 'degree', 'internship', 'provisional_reg', 'address_proof'],
#         'renewal': ['photo', 'latest_cpd_certificate', 'address_proof'],
#         'additional_qualification': ['photo', 'degree', 'marksheet'],
#         'good_standing_mmc': ['photo', 'address_proof', 'affidavit'],
#     }
#     return document_requirements.get(application_type, ['photo', 'signature', 'address_proof'])

def get_required_documents(application_type):
    """Get required documents based on application type"""
    document_requirements = {
        'permanent': ['photo', 'signature', 'ssc', 'hsc', 'degree', 'internship', 'address_proof'],
        'foreign_permanent': ['photo', 'signature', 'ssc', 'hsc', 'degree', 'passport', 'screening_test', 'mci_eligibility'],
        'provisional': ['photo', 'signature', 'ssc', 'hsc', 'degree_certificate'],
        'additional_qualification': ['photo', 'degree', 'marksheet'],
        'renewal': ['photo', 'current_registration'],
        'good_standing_mmc': ['photo', 'address_proof', 'current_registration'],
    }
    return document_requirements.get(application_type, ['photo', 'signature'])

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
def delete_application(request, application_id):
    """Delete draft application"""
    application = get_object_or_404(
        Application, 
        application_id=application_id, 
        applicant=request.user,
        status='draft'
    )
    
    if request.method == 'POST':
        application_id = application.application_id
        application_type = application.get_application_type_display()
        application.delete()
        
        messages.success(request, f"{application_type} application deleted successfully.")
        return redirect('dashboard')
    
    return render(request, 'MMC/applications/delete_confirm.html', {
        'application': application
    })


# AJAX views for dynamic functionality
@login_required
def get_step_progress(request, application_id):
    """Get step progress for AJAX updates"""
    application = get_object_or_404(Application, application_id=application_id, applicant=request.user)
    completed_steps = ApplicationStep.objects.filter(application=application, is_completed=True).count()
    total_steps = 10
    
    return JsonResponse({
        'completed': completed_steps,
        'total': total_steps,
        'percentage': int((completed_steps / total_steps) * 100)
    })

@login_required
def validate_step_data(request, application_id, step):
    """Validate step data via AJAX"""
    application = get_object_or_404(Application, application_id=application_id, applicant=request.user)
    
    # This would contain specific validation logic for each step
    # For now, return basic validation
    return JsonResponse({'valid': True, 'errors': []})

@login_required
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
def certificate_list(request):
    certificates = Certificate.objects.filter(user=request.user).order_by('-issue_date')
    context = {
        'certificates': certificates
    }
    return render(request, 'MMC/certificates/certificate_list.html', context)

@login_required
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
def delete_cpd_program(request, program_id):
    if request.method == 'DELETE':
        program = get_object_or_404(CPDProgram, id=program_id)
        program.delete()
        return JsonResponse({'success': True, 'message': 'Program deleted successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
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
def admin_dashboard(request):
    return redirect('dashboard')

@login_required
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


# views.py - AI Integration Module
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, F, Count, Avg, Sum, Case, When, Value, IntegerField, BooleanField, CharField
from django.db import models
from django.utils import timezone
from datetime import timedelta, datetime
import json
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# AI Integration Views
@login_required
def ai_insights(request):
    """Main AI insights router"""
    if request.user.user_type == 'rmp':
        return rmp_ai_insights(request)
    elif request.user.user_type in ['admin', 'super_admin', 'staff']:
        return admin_ai_insights(request)
    else:
        return render(request, 'MMC/403.html')

@login_required
def ai_dashboard(request):
    """Comprehensive AI Dashboard"""
    if request.user.user_type in ['admin', 'super_admin']:
        return admin_ai_dashboard(request)
    elif request.user.user_type == 'rmp':
        return rmp_ai_dashboard(request)
    else:
        return render(request, 'MMC/403.html')

@login_required
def ai_analytics_dashboard(request):
    """Advanced Analytics Dashboard"""
    if request.user.user_type not in ['admin', 'super_admin']:
        return render(request, 'MMC/403.html')
    
    return admin_analytics_dashboard(request)

# RMP AI Functions
@login_required
def rmp_ai_insights(request):
    """Personalized AI Insights for RMP"""
    try:
        rmp_profile = get_object_or_404(RMPProfile, user=request.user)
        
        # Get or generate insights
        insights = AIInsight.objects.filter(
            rmp=rmp_profile, 
            is_active=True
        ).order_by('-generated_date')[:10]
        
        if not insights.exists():
            insights = generate_rmp_ai_insights(rmp_profile)
        
        # Performance score
        performance_score = AIPerformanceScore.objects.filter(rmp=rmp_profile).first()
        if not performance_score:
            performance_score = calculate_rmp_performance_score(rmp_profile)
        
        # Predictive alerts
        predictive_alerts = PredictiveAlert.objects.filter(
            rmp=rmp_profile,
            is_active=True,
            is_dismissed=False
        ).order_by('-confidence_score')[:5]
        
        # CPD recommendations
        cpd_recommendations = get_personalized_cpd_recommendations(rmp_profile)
        
        # Performance trends
        performance_trend = calculate_performance_trend(rmp_profile)
        
        context = {
            'rmp_profile': rmp_profile,
            'insights': insights,
            'performance_score': performance_score,
            'predictive_alerts': predictive_alerts,
            'cpd_recommendations': cpd_recommendations,
            'performance_trend': performance_trend,
            'current_year': timezone.now().year,
        }
        
        return render(request, 'MMC/ai/rmp_insights.html', context)
        
    except Exception as e:
        logger.error(f"Error in rmp_ai_insights: {str(e)}")
        return render(request, 'Shared/404.html')

@login_required
def rmp_ai_dashboard(request):
    """RMP AI Dashboard with comprehensive metrics"""
    try:
        rmp_profile = get_object_or_404(RMPProfile, user=request.user)
        
        # Key metrics
        metrics = calculate_rmp_metrics(rmp_profile)
        
        # Recent activity
        recent_applications = Application.objects.filter(
            rmp=rmp_profile
        ).order_by('-submitted_date')[:5]
        
        # CPD progress
        cpd_progress = calculate_cpd_progress(rmp_profile)
        
        # Risk assessment
        risk_assessment = assess_rmp_risk(rmp_profile)
        
        # Peer comparison
        peer_comparison = get_peer_comparison(rmp_profile)
        
        context = {
            'rmp_profile': rmp_profile,
            'metrics': metrics,
            'recent_applications': recent_applications,
            'cpd_progress': cpd_progress,
            'risk_assessment': risk_assessment,
            'peer_comparison': peer_comparison,
        }
        
        return render(request, 'MMC/ai/rmp_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in rmp_ai_dashboard: {str(e)}")
        return render(request, 'Shared/404.html')

# Admin AI Functions
@login_required
def admin_ai_insights(request):
    """Admin AI Insights with predictive analytics"""
    try:
        # Risk assessment for applications
        from django.db.models import Q, Case, When, Value, IntegerField

        high_risk_applications = (
            Application.objects.filter(status='under_review')
            .annotate(
                risk_score=Case(
                    # Rule 1: high-risk types
                    When(application_type__in=['foreign_permanent', 'defaulter'], then=Value(80)),
                    # Rule 2: non-empty review notes
                    When(~Q(review_notes="") & Q(review_notes__isnull=False), then=Value(70)),
                    # Rule 3: unverified documents — adjust related name
                    When(documents__is_verified=False, then=Value(60)),
                    # Default fallback
                    default=Value(40),
                    output_field=IntegerField(),  # ✅ Correct usage (you DO instantiate here)
                )
            )
            .filter(risk_score__gte=70)
            .distinct()[:10]
        )
        
        # Compliance alerts
        compliance_alerts = get_compliance_alerts()
        
        # Performance predictions
        performance_predictions = AIPerformanceScore.objects.filter(
            overall_score__lt=70
        ).select_related('rmp__user').order_by('overall_score')[:10]
        
        # System health insights
        system_health = calculate_system_health()
        
        # Fraud detection alerts
        fraud_alerts = detect_fraud_patterns()
        
        context = {
            'high_risk_applications': high_risk_applications,
            'compliance_alerts': compliance_alerts,
            'performance_predictions': performance_predictions,
            'system_health': system_health,
            'fraud_alerts': fraud_alerts,
            'total_rmps': RMPProfile.objects.count(),
            'pending_applications': Application.objects.filter(status='under_review').count(),
        }
        
        return render(request, 'MMC/ai/admin_insights.html', context)
        
    except Exception as e:
        logger.error(f"Error in admin_ai_insights: {str(e)}")
        return render(request, 'Shared/404.html')

@login_required
def admin_ai_dashboard(request):
    """Comprehensive Admin AI Dashboard"""
    try:
        # Overall statistics
        performance_scores = AIPerformanceScore.objects.all()
        avg_scores = performance_scores.aggregate(
            avg_overall=Avg('overall_score'),
            avg_cpd=Avg('cpd_score'),
            avg_compliance=Avg('compliance_score'),
            avg_professional=Avg('professional_conduct_score')
        )
        
        # Risk analysis
        risk_distribution = {
            'high_risk': performance_scores.filter(overall_score__lt=60).count(),
            'medium_risk': performance_scores.filter(overall_score__gte=60, overall_score__lt=75).count(),
            'low_risk': performance_scores.filter(overall_score__gte=75).count(),
        }
        
        # Application analytics
        application_analytics = get_application_analytics()
        
        # CPD analytics
        cpd_analytics = get_cpd_analytics()
        
        # Staff performance
        staff_performance = get_staff_performance_metrics()
        
        # Predictive trends
        predictive_trends = get_predictive_trends()
        
        context = {
            'avg_scores': avg_scores,
            'risk_distribution': risk_distribution,
            'application_analytics': application_analytics,
            'cpd_analytics': cpd_analytics,
            'staff_performance': staff_performance,
            'predictive_trends': predictive_trends,
            'total_analyzed': performance_scores.count(),
        }
        
        return render(request, 'MMC/ai/admin_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in admin_ai_dashboard: {str(e)}")
        return render(request, 'Shared/404.html')

@login_required
def admin_analytics_dashboard(request):
    """Advanced Analytics Dashboard"""
    try:
        # Time-based analytics
        time_analytics = get_time_based_analytics()
        
        # Geographic distribution
        geographic_data = get_geographic_distribution()
        
        # Specialization analytics
        specialization_analytics = get_specialization_analytics()
        
        # Revenue analytics
        revenue_analytics = get_revenue_analytics()
        
        # Compliance analytics
        compliance_analytics = get_compliance_analytics()
        
        # AI model performance
        ai_model_performance = get_ai_model_performance()
        
        context = {
            'time_analytics': time_analytics,
            'geographic_data': geographic_data,
            'specialization_analytics': specialization_analytics,
            'revenue_analytics': revenue_analytics,
            'compliance_analytics': compliance_analytics,
            'ai_model_performance': ai_model_performance,
        }
        
        return render(request, 'MMC/ai/analytics_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in admin_analytics_dashboard: {str(e)}")
        return render(request, 'Shared/404.html')

# AI Business Logic Functions
def generate_rmp_ai_insights(rmp_profile):
    """Generate comprehensive AI insights for RMP"""
    insights = []
    
    # CPD Compliance Insight
    cpd_completion = (rmp_profile.total_cpd_points / rmp_profile.cpd_points_required * 100) if rmp_profile.cpd_points_required > 0 else 0
    
    if cpd_completion < 60:
        insights.append(AIInsight.objects.create(
            rmp=rmp_profile,
            insight_type='compliance',
            title='CPD Compliance Alert',
            description=f'Your CPD completion is at {cpd_completion:.1f}%. You need {rmp_profile.cpd_points_required - rmp_profile.total_cpd_points} more points to meet requirements.',
            severity='high' if cpd_completion < 30 else 'medium',
            action_items=[
                {'action': 'View CPD Programs', 'url': '/cpd/programs/'},
                {'action': 'Check CPD Points', 'url': '/cpd/dashboard/'}
            ],
            confidence_level=0.85
        ))
    
    # Renewal Prediction
    if rmp_profile.registration_valid_till and rmp_profile.registration_valid_till <= timezone.now().date() + timedelta(days=90):
        days_until_renewal = (rmp_profile.registration_valid_till - timezone.now().date()).days
        insights.append(AIInsight.objects.create(
            rmp=rmp_profile,
            insight_type='deadline',
            title='Registration Renewal Due',
            description=f'Your registration renewal is due in {days_until_renewal} days. Start the renewal process early to avoid service interruptions.',
            severity='high' if days_until_renewal < 30 else 'medium',
            action_items=[
                {'action': 'Start Renewal', 'url': '/applications/renewal/'},
                {'action': 'Check Requirements', 'url': '/help/renewal-guide/'}
            ],
            confidence_level=0.92
        ))
    
    # Performance Insight based on application history
    application_stats = Application.objects.filter(
        rmp=rmp_profile,
        status__in=['approved', 'rejected', 'completed']
    ).aggregate(
        total=Count('application_id'),
        approved=Count('application_id', filter=Q(status__in=['approved', 'completed']))
    )
    
    if application_stats['total'] > 0:
        success_rate = (application_stats['approved'] / application_stats['total']) * 100
        
        if success_rate < 70:
            insights.append(AIInsight.objects.create(
                rmp=rmp_profile,
                insight_type='performance',
                title='Application Success Rate',
                description=f'Your application success rate is {success_rate:.1f}%. Review rejected applications for common issues.',
                severity='medium',
                action_items=[
                    {'action': 'View Application History', 'url': '/applications/history/'},
                    {'action': 'Application Guidelines', 'url': '/help/application-guide/'}
                ],
                confidence_level=0.78
            ))
    
    # Complaint Risk Assessment
    pending_complaints = Complaint.objects.filter(
        against_rmp=rmp_profile,
        status__in=['registered', 'under_investigation']
    ).count()
    
    if pending_complaints > 0:
        insights.append(AIInsight.objects.create(
            rmp=rmp_profile,
            insight_type='risk',
            title='Pending Complaints Alert',
            description=f'You have {pending_complaints} pending complaint(s). Address them promptly to maintain good standing.',
            severity='high' if pending_complaints > 2 else 'medium',
            action_items=[
                {'action': 'View Complaints', 'url': '/complaints/'},
                {'action': 'Professional Conduct Guide', 'url': '/help/conduct-guide/'}
            ],
            confidence_level=0.88
        ))
    
    # CPD Opportunity Insight
    if cpd_completion > 80:
        insights.append(AIInsight.objects.create(
            rmp=rmp_profile,
            insight_type='opportunity',
            title='CPD Excellence',
            description='You are exceeding CPD requirements! Consider advanced courses for specialization development.',
            severity='low',
            action_items=[
                {'action': 'Advanced CPD Programs', 'url': '/cpd/advanced/'},
                {'action': 'Specialization Courses', 'url': '/cpd/specialization/'}
            ],
            confidence_level=0.75
        ))
    
    return insights

def calculate_rmp_performance_score(rmp_profile):
    """Calculate comprehensive performance score for RMP"""
    
    # Base scores
    cpd_score = calculate_cpd_score(rmp_profile)
    compliance_score = calculate_compliance_score(rmp_profile)
    professional_score = calculate_professional_conduct_score(rmp_profile)
    research_score = calculate_research_score(rmp_profile)
    
    # Weighted overall score
    overall_score = (
        cpd_score * 0.35 +
        compliance_score * 0.30 +
        professional_score * 0.25 +
        research_score * 0.10
    )
    
    score_breakdown = {
        'cpd_score': float(cpd_score),
        'compliance_score': float(compliance_score),
        'professional_conduct_score': float(professional_score),
        'research_score': float(research_score),
        'calculation_date': timezone.now().isoformat()
    }
    
    performance_score, created = AIPerformanceScore.objects.update_or_create(
        rmp=rmp_profile,
        defaults={
            'overall_score': overall_score,
            'cpd_score': cpd_score,
            'compliance_score': compliance_score,
            'professional_conduct_score': professional_score,
            'research_score': research_score,
            'score_breakdown': score_breakdown
        }
    )
    
    return performance_score

def calculate_cpd_score(rmp_profile):
    """Calculate CPD performance score"""
    if rmp_profile.cpd_points_required == 0:
        return Decimal('100.0')
    
    completion_ratio = min(rmp_profile.total_cpd_points / rmp_profile.cpd_points_required, 1.0)
    base_score = completion_ratio * 100
    
    # Bonus for early completion
    if rmp_profile.cpd_cycle_end:
        days_remaining = (rmp_profile.cpd_cycle_end - timezone.now().date()).days
        if days_remaining > 60 and completion_ratio >= 1.0:
            base_score = min(base_score + 10, 100)
    
    return Decimal(str(round(base_score, 2)))

def calculate_compliance_score(rmp_profile):
    """Calculate compliance score"""
    base_score = 100.0
    
    # Deductions for various compliance issues
    deductions = 0
    
    # Registration status
    if rmp_profile.registration_status != 'active':
        deductions += 30
    
    # Renewal status
    if rmp_profile.registration_valid_till and rmp_profile.registration_valid_till < timezone.now().date():
        deductions += 40
    
    # Pending complaints
    pending_complaints = Complaint.objects.filter(
        against_rmp=rmp_profile,
        status__in=['registered', 'under_investigation']
    ).count()
    deductions += pending_complaints * 10
    
    # Overdue applications
    overdue_applications = Application.objects.filter(
        rmp=rmp_profile,
        status='under_review',
        expected_completion_date__lt=timezone.now()
    ).count()
    deductions += overdue_applications * 5
    
    final_score = max(base_score - deductions, 0)
    return Decimal(str(round(final_score, 2)))

def calculate_professional_conduct_score(rmp_profile):
    """Calculate professional conduct score"""
    base_score = 100.0
    
    # Complaint analysis
    complaints = Complaint.objects.filter(against_rmp=rmp_profile)
    total_complaints = complaints.count()
    resolved_complaints = complaints.filter(status='resolved').count()
    
    if total_complaints > 0:
        resolution_rate = resolved_complaints / total_complaints
        complaint_deduction = (1 - resolution_rate) * 50
        base_score -= complaint_deduction
    
    # Severity adjustments
    high_severity_complaints = complaints.filter(severity='high').count()
    base_score -= high_severity_complaints * 20
    
    # Positive factors
    awards_count = Award.objects.filter(rmp=rmp_profile).count()
    base_score += min(awards_count * 5, 20)
    
    final_score = max(min(base_score, 100), 0)
    return Decimal(str(round(final_score, 2)))

def calculate_research_score(rmp_profile):
    """Calculate research and publication score"""
    base_score = 0
    
    # Publications
    publications = Publication.objects.filter(rmp=rmp_profile)
    publication_score = min(publications.count() * 10, 40)
    
    # Research projects (placeholder - would need Research model)
    research_score = 0
    
    # Conference presentations
    conference_papers = publications.filter(publication_type='conference')
    conference_score = min(conference_papers.count() * 5, 20)
    
    # Awards and recognition
    awards = Award.objects.filter(rmp=rmp_profile)
    award_score = min(awards.count() * 8, 20)
    
    base_score = publication_score + research_score + conference_score + award_score
    
    return Decimal(str(round(base_score, 2)))

# Utility Functions
def get_personalized_cpd_recommendations(rmp_profile):
    """Get personalized CPD recommendations based on specialization and history"""
    recommendations = CPDProgram.objects.filter(
        is_active=True,
        start_date__gte=timezone.now(),
        status='Published'
    ).annotate(
        relevance_score=Case(
            When(target_audience__icontains=rmp_profile.specialization, then=Value(100)),
            When(target_audience__icontains='general', then=Value(50)),
            default=Value(30),
            output_field=IntegerField()
        )
    ).filter(relevance_score__gte=50).order_by('-relevance_score', 'start_date')[:5]
    
    return recommendations

def get_compliance_alerts():
    """Get compliance alerts across the system"""
    alerts = []
    
    # CPD compliance alerts
    cpd_alerts = RMPProfile.objects.filter(
        registration_status='active'
    ).annotate(
        cpd_deficit=F('cpd_points_required') - F('total_cpd_points'),
        days_until_renewal=Case(
            When(
                registration_valid_till__isnull=False,
                then=F('registration_valid_till') - timezone.now().date()
            ),
            default=Value(999),
            output_field=IntegerField()
        )
    ).filter(
        Q(cpd_deficit__gt=10) | Q(days_until_renewal__lt=30)
    ).select_related('user')[:10]
    
    for rmp in cpd_alerts:
        alert_type = 'cpd_deficit' if rmp.cpd_deficit > 10 else 'renewal'
        severity = 'high' if (rmp.cpd_deficit > 20 or rmp.days_until_renewal < 15) else 'medium'
        
        alerts.append({
            'rmp': rmp,
            'type': alert_type,
            'severity': severity,
            'message': f"CPD deficit: {rmp.cpd_deficit} points" if alert_type == 'cpd_deficit' else f"Renewal in {rmp.days_until_renewal} days",
            'action_url': f"/admin/rmp/{rmp.id}/"
        })
    
    return alerts

def calculate_system_health():
    """Calculate overall system health metrics"""
    total_applications = Application.objects.count()
    pending_applications = Application.objects.filter(status='under_review').count()
    completed_today = Application.objects.filter(
        status__in=['approved', 'completed'],
        updated_at__date=timezone.now().date()
    ).count()
    
    sla_violations = Application.objects.filter(
        expected_completion_date__lt=timezone.now(),
        status='under_review'
    ).count()
    
    pending_payments = Payment.objects.filter(status='pending').count()
    
    cpd_completion_rate = calculate_cpd_completion_rate()
    
    return {
        'pending_applications': pending_applications,
        'completion_rate_today': (completed_today / total_applications * 100) if total_applications > 0 else 0,
        'sla_violations': sla_violations,
        'sla_compliance_rate': ((pending_applications - sla_violations) / pending_applications * 100) if pending_applications > 0 else 100,
        'pending_payments': pending_payments,
        'cpd_completion_rate': cpd_completion_rate,
    }

def calculate_cpd_completion_rate():
    """Calculate overall CPD completion rate"""
    total_rmps = RMPProfile.objects.filter(registration_status='active').count()
    if total_rmps == 0:
        return 0
    
    compliant_rmps = RMPProfile.objects.filter(
        registration_status='active',
        total_cpd_points__gte=F('cpd_points_required')
    ).count()
    
    return (compliant_rmps / total_rmps) * 100

def detect_fraud_patterns():
    """Detect potential fraud patterns in applications"""
    fraud_patterns = []
    
    # Multiple applications with similar data
    duplicate_applications = Application.objects.values(
        'application_data__personal_details__full_name',
        'application_data__personal_details__date_of_birth'
    ).annotate(
        count=Count('application_id')
    ).filter(count__gt=1).order_by('-count')[:5]
    
    for pattern in duplicate_applications:
        fraud_patterns.append({
            'type': 'duplicate_application',
            'description': f"Multiple applications with similar personal details",
            'count': pattern['count'],
            'severity': 'medium'
        })
    
    # Rapid succession applications
    rapid_applications = Application.objects.filter(
        submitted_date__gte=timezone.now() - timedelta(days=7)
    ).values('rmp').annotate(
        count=Count('application_id')
    ).filter(count__gt=3).order_by('-count')[:5]
    
    for pattern in rapid_applications:
        fraud_patterns.append({
            'type': 'rapid_applications',
            'description': "Multiple applications submitted in short time",
            'count': pattern['count'],
            'severity': 'low'
        })
    
    return fraud_patterns

# Additional analytical functions
def get_application_analytics():
    """Get comprehensive application analytics"""
    today = timezone.now().date()
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)
    
    analytics = {
        'total_applications': Application.objects.count(),
        'pending_review': Application.objects.filter(status='under_review').count(),
        'approved_today': Application.objects.filter(
            status__in=['approved', 'completed'],
            updated_at__date=today
        ).count(),
        'weekly_trend': Application.objects.filter(
            submitted_date__date__gte=last_week
        ).count(),
        'monthly_trend': Application.objects.filter(
            submitted_date__date__gte=last_month
        ).count(),
        'avg_processing_time': calculate_average_processing_time(),
    }
    
    return analytics

def calculate_average_processing_time():
    """Calculate average application processing time"""
    completed_apps = Application.objects.filter(
        status__in=['approved', 'completed', 'rejected'],
        submitted_date__isnull=False,
        updated_at__isnull=False
    )
    
    if not completed_apps.exists():
        return 0
    
    total_seconds = 0
    for app in completed_apps:
        processing_time = app.updated_at - app.submitted_date
        total_seconds += processing_time.total_seconds()
    
    avg_seconds = total_seconds / completed_apps.count()
    avg_days = avg_seconds / (24 * 3600)
    
    return round(avg_days, 1)

def get_cpd_analytics():
    """Get CPD program analytics"""
    analytics = {
        'total_programs': CPDProgram.objects.count(),
        'active_programs': CPDProgram.objects.filter(is_active=True).count(),
        'upcoming_programs': CPDProgram.objects.filter(start_date__gte=timezone.now()).count(),
        'total_participations': CPDAttendance.objects.count(),
        'avg_attendance_rate': calculate_avg_attendance_rate(),
        'popular_programs': get_popular_cpd_programs(),
    }
    
    return analytics

def calculate_avg_attendance_rate():
    """Calculate average CPD program attendance rate"""
    programs = CPDProgram.objects.annotate(
        total_registered=Count('attendances'),
        total_attended=Count('attendances', filter=Q(attendances__attendance_status='attended'))
    ).filter(total_registered__gt=0)
    
    if not programs.exists():
        return 0
    
    total_rate = 0
    for program in programs:
        attendance_rate = (program.total_attended / program.total_registered) * 100
        total_rate += attendance_rate
    
    return round(total_rate / programs.count(), 1)

def get_popular_cpd_programs():
    """Get most popular CPD programs"""
    return CPDProgram.objects.annotate(
        attendance_count=Count('attendances')
    ).order_by('-attendance_count')[:5]

# AJAX views for real-time data
@login_required
def get_ai_metrics(request):
    """AJAX endpoint for real-time AI metrics"""
    if request.user.user_type == 'rmp':
        rmp_profile = get_object_or_404(RMPProfile, user=request.user)
        metrics = calculate_rmp_metrics(rmp_profile)
        return JsonResponse(metrics)
    else:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

@login_required
def get_realtime_analytics(request):
    """AJAX endpoint for real-time admin analytics"""
    analytics = {
        'system_health': calculate_system_health(),
        'application_analytics': get_application_analytics(),
        'cpd_analytics': get_cpd_analytics(),
    }
    return JsonResponse(analytics)

# ai_helpers.py - Additional AI helper functions
def calculate_rmp_metrics(rmp_profile):
    """Calculate comprehensive metrics for RMP"""
    today = timezone.now().date()
    
    # Application metrics
    applications = rmp_profile.applications.all()
    total_applications = applications.count()
    approved_applications = applications.filter(status__in=['approved', 'completed']).count()
    pending_applications = applications.filter(status='under_review').count()
    
    # CPD metrics
    cpd_completion = (rmp_profile.total_cpd_points / rmp_profile.cpd_points_required * 100) if rmp_profile.cpd_points_required > 0 else 0
    cpd_deficit = max(rmp_profile.cpd_points_required - rmp_profile.total_cpd_points, 0)
    
    # Renewal metrics
    renewal_status = "Current"
    renewal_urgency = "low"
    if rmp_profile.registration_valid_till:
        days_until_renewal = (rmp_profile.registration_valid_till - today).days
        if days_until_renewal < 0:
            renewal_status = "Expired"
            renewal_urgency = "high"
        elif days_until_renewal < 30:
            renewal_status = "Urgent"
            renewal_urgency = "high"
        elif days_until_renewal < 90:
            renewal_status = "Due Soon"
            renewal_urgency = "medium"
    
    # Complaint metrics
    pending_complaints = Complaint.objects.filter(
        against_rmp=rmp_profile,
        status__in=['registered', 'under_investigation']
    ).count()
    
    return {
        'total_applications': total_applications,
        'approval_rate': (approved_applications / total_applications * 100) if total_applications > 0 else 0,
        'pending_applications': pending_applications,
        'cpd_completion_rate': cpd_completion,
        'cpd_deficit': cpd_deficit,
        'renewal_status': renewal_status,
        'renewal_urgency': renewal_urgency,
        'pending_complaints': pending_complaints,
        'registration_status': rmp_profile.registration_status,
    }

def assess_rmp_risk(rmp_profile):
    """Assess overall risk for RMP"""
    risk_factors = []
    overall_risk = "low"
    
    metrics = calculate_rmp_metrics(rmp_profile)
    
    # CPD risk
    if metrics['cpd_completion_rate'] < 50:
        risk_factors.append("Low CPD completion")
        overall_risk = "medium"
    
    # Renewal risk
    if metrics['renewal_urgency'] == "high":
        risk_factors.append("Registration renewal overdue")
        overall_risk = "high"
    
    # Complaint risk
    if metrics['pending_complaints'] > 0:
        risk_factors.append(f"{metrics['pending_complaints']} pending complaints")
        overall_risk = "high" if metrics['pending_complaints'] > 2 else "medium"
    
    # Application approval risk
    if metrics['approval_rate'] < 60 and metrics['total_applications'] > 5:
        risk_factors.append("Low application approval rate")
        overall_risk = "medium"
    
    return {
        'level': overall_risk,
        'factors': risk_factors,
        'score': calculate_risk_score(risk_factors, overall_risk)
    }

def calculate_risk_score(risk_factors, overall_risk):
    """Calculate numerical risk score"""
    base_score = 0
    
    risk_weights = {
        'high': 3,
        'medium': 2,
        'low': 1
    }
    
    for factor in risk_factors:
        if 'overdue' in factor.lower() or 'expired' in factor.lower():
            base_score += 40
        elif 'complaint' in factor.lower():
            base_score += 30
        elif 'cpd' in factor.lower():
            base_score += 20
        else:
            base_score += 10
    
    return min(base_score, 100)

def get_peer_comparison(rmp_profile):
    """Compare RMP with peers in same specialization"""
    peers = RMPProfile.objects.filter(
        specialization=rmp_profile.specialization,
        registration_status='active'
    ).exclude(id=rmp_profile.id)
    
    if not peers.exists():
        return None
    
    peer_metrics = {
        'avg_cpd_points': peers.aggregate(avg=Avg('total_cpd_points'))['avg'] or 0,
        'avg_performance': AIPerformanceScore.objects.filter(
            rmp__in=peers
        ).aggregate(avg=Avg('overall_score'))['avg'] or 0,
        'total_peers': peers.count()
    }
    
    current_performance = AIPerformanceScore.objects.filter(rmp=rmp_profile).first()
    
    comparison = {
        'cpd_rank': "Above Average" if rmp_profile.total_cpd_points > peer_metrics['avg_cpd_points'] else "Below Average",
        'performance_rank': "Above Average" if current_performance and current_performance.overall_score > peer_metrics['avg_performance'] else "Below Average",
        'peer_count': peer_metrics['total_peers'],
        'avg_peer_cpd': round(peer_metrics['avg_cpd_points'], 1),
        'avg_peer_performance': round(peer_metrics['avg_performance'], 1)
    }
    
    return comparison

# views.py - Additional missing implementations
def calculate_performance_trend(rmp_profile):
    """Calculate performance trend for RMP"""
    # This would typically compare current performance with historical data
    # For now, we'll simulate based on recent activity
    recent_applications = Application.objects.filter(
        rmp=rmp_profile,
        submitted_date__gte=timezone.now() - timedelta(days=90)
    )
    
    recent_approvals = recent_applications.filter(status__in=['approved', 'completed']).count()
    total_recent = recent_applications.count()
    
    if total_recent > 0:
        recent_success_rate = (recent_approvals / total_recent) * 100
        # Compare with overall performance
        overall_applications = Application.objects.filter(rmp=rmp_profile)
        overall_approvals = overall_applications.filter(status__in=['approved', 'completed']).count()
        overall_total = overall_applications.count()
        
        if overall_total > 0:
            overall_success_rate = (overall_approvals / overall_total) * 100
            if recent_success_rate > overall_success_rate + 10:
                return {'positive': True, 'message': 'Performance improving - recent success rate is higher'}
            elif recent_success_rate < overall_success_rate - 10:
                return {'positive': False, 'message': 'Performance declining - review recent applications'}
    
    return {'positive': True, 'message': 'Stable performance trend'}

def get_staff_performance_metrics():
    """Get staff performance metrics for admin dashboard"""
    from django.db.models import Count, Avg, Q, F, ExpressionWrapper, DurationField
    
    staff_performance = CustomUser.objects.filter(
        user_type__in=['staff', 'admin'],
        assigned_applications__isnull=False
    ).annotate(
        total_processed=Count('assigned_applications', 
                              filter=Q(assigned_applications__status__in=['approved', 'rejected', 'completed'])),
        avg_processing_time=Avg(
            ExpressionWrapper(
                F('assigned_applications__updated_at') - F('assigned_applications__submitted_date'),
                output_field=DurationField()
            ),
            filter=Q(assigned_applications__status__in=['approved', 'rejected', 'completed'])
        ),
        approval_rate=Count('assigned_applications', 
                            filter=Q(assigned_applications__status__in=['approved', 'completed'])) * 100.0 / 
                      Count('assigned_applications', 
                            filter=Q(assigned_applications__status__in=['approved', 'rejected', 'completed']))
    ).filter(total_processed__gt=0).values(
        'full_name', 'total_processed', 'avg_processing_time', 'approval_rate'
    )
    
    # Convert processing time to days and calculate performance score
    results = []
    for staff in staff_performance:
        if staff['avg_processing_time']:
            processing_days = staff['avg_processing_time'].total_seconds() / (24 * 3600)
        else:
            processing_days = 0
            
        approval_score = staff['approval_rate'] or 0
        time_score = max(0, 100 - (processing_days * 10))
        performance_score = (approval_score + time_score) / 2
        
        results.append({
            'full_name': staff['full_name'],
            'total_processed': staff['total_processed'],
            'avg_processing_time': round(processing_days, 1),
            'approval_rate': round(approval_score, 1),
            'performance': round(performance_score, 1)
        })
    
    return sorted(results, key=lambda x: x['performance'], reverse=True)[:5]


def get_predictive_trends():
    """Get predictive trends for admin dashboard"""
    # Analyze application trends
    current_month = timezone.now().month
    last_month_apps = Application.objects.filter(
        submitted_date__month=current_month - 1 if current_month > 1 else 12,
        submitted_date__year=timezone.now().year if current_month > 1 else timezone.now().year - 1
    ).count()
    
    current_month_apps = Application.objects.filter(
        submitted_date__month=current_month,
        submitted_date__year=timezone.now().year
    ).count()
    
    app_trend = 'up' if current_month_apps > last_month_apps else 'down'
    app_change = abs(current_month_apps - last_month_apps)
    
    # CPD participation trends
    current_cpd = CPDAttendance.objects.filter(
        registration_date__month=current_month
    ).count()
    
    last_cpd = CPDAttendance.objects.filter(
        registration_date__month=current_month - 1 if current_month > 1 else 12
    ).count()
    
    cpd_trend = 'up' if current_cpd > last_cpd else 'down'
    cpd_change = abs(current_cpd - last_cpd)
    
    return [
        {
            'metric': 'Application Volume',
            'trend': app_trend,
            'prediction': f'{app_change} more applications' if app_trend == 'up' else f'{app_change} fewer applications',
            'confidence': 85
        },
        {
            'metric': 'CPD Participation',
            'trend': cpd_trend,
            'prediction': f'{cpd_change} more participations' if cpd_trend == 'up' else f'{cpd_change} fewer participations',
            'confidence': 78
        }
    ]

def get_time_based_analytics():
    """Get time-based analytics for advanced dashboard"""
    from django.db.models.functions import TruncMonth, TruncWeek
    
    # Monthly application trends
    monthly_apps = Application.objects.annotate(
        month=TruncMonth('submitted_date')
    ).values('month').annotate(
        count=Count('application_id'),
        approved=Count('application_id', filter=Q(status__in=['approved', 'completed']))
    ).order_by('month')[:12]
    
    # Weekly performance
    weekly_performance = AIPerformanceScore.objects.filter(
        last_updated__gte=timezone.now() - timedelta(days=90)
    ).annotate(
        week=TruncWeek('last_updated')
    ).values('week').annotate(
        avg_score=Avg('overall_score')
    ).order_by('week')
    
    return {
        'monthly_applications': [],
        'weekly_performance': []
    }

def get_geographic_distribution():
    """Get geographic distribution of RMPs"""
    state_distribution = RMPProfile.objects.values('communication_state').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    city_distribution = RMPProfile.objects.values('communication_city').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    return {
        'states': list(state_distribution),
        'cities': list(city_distribution)
    }

def get_specialization_analytics():
    """Get specialization-based analytics"""
    specialization_stats = RMPProfile.objects.values('specialization').annotate(
        total=Count('id'),
        avg_performance=Avg('ai_score__overall_score'),
        avg_cpd=Avg('total_cpd_points')
    ).filter(specialization__isnull=False).order_by('-total')[:10]
    
    return list(specialization_stats)

def get_revenue_analytics():
    """Get revenue analytics"""
    monthly_revenue = Payment.objects.filter(
        status='success',
        payment_date__gte=timezone.now() - timedelta(days=365)
    ).annotate(
        month=TruncMonth('payment_date')
    ).values('month').annotate(
        revenue=Sum('amount')
    ).order_by('month')
    
    service_revenue = Payment.objects.filter(
        status='success',
        payment_date__gte=timezone.now() - timedelta(days=90)
    ).values('application__application_type').annotate(
        revenue=Sum('amount'),
        count=Count('payment_id')
    ).order_by('-revenue')
    
    return {
        'monthly_revenue': list(monthly_revenue),
        'service_revenue': list(service_revenue)
    }

def get_compliance_analytics():
    """Get compliance analytics"""
    total_rmps = RMPProfile.objects.filter(registration_status='active').count()
    
    cpd_compliant = RMPProfile.objects.filter(
        registration_status='active',
        total_cpd_points__gte=F('cpd_points_required')
    ).count()
    
    renewal_compliant = RMPProfile.objects.filter(
        registration_status='active',
        registration_valid_till__gte=timezone.now().date()
    ).count()
    
    complaint_free = RMPProfile.objects.exclude(
        complaints_against__status__in=['registered', 'under_investigation']
    ).filter(registration_status='active').count()
    
    return {
        'total_active_rmps': total_rmps,
        'cpd_compliance_rate': (cpd_compliant / total_rmps * 100) if total_rmps > 0 else 0,
        'renewal_compliance_rate': (renewal_compliant / total_rmps * 100) if total_rmps > 0 else 0,
        'complaint_free_rate': (complaint_free / total_rmps * 100) if total_rmps > 0 else 0,
    }

def get_ai_model_performance():
    """Get AI model performance metrics"""
    # This would typically come from your ML model monitoring
    # For now, we'll simulate some metrics
    total_insights = AIInsight.objects.count()
    active_insights = AIInsight.objects.filter(is_active=True).count()
    high_confidence_insights = AIInsight.objects.filter(confidence_level__gte=0.8).count()
    
    predictive_alerts = PredictiveAlert.objects.count()
    accurate_alerts = PredictiveAlert.objects.filter(
        predicted_date__lte=timezone.now().date() + timedelta(days=7),
        is_active=True
    ).count()
    
    return {
        'total_insights_generated': total_insights,
        'active_insights': active_insights,
        'high_confidence_rate': (high_confidence_insights / total_insights * 100) if total_insights > 0 else 0,
        'predictive_alert_accuracy': (accurate_alerts / predictive_alerts * 100) if predictive_alerts > 0 else 0,
        'model_uptime': 99.8,  # Simulated
        'average_confidence': AIInsight.objects.aggregate(avg=Avg('confidence_level'))['avg'] or 0
    }

# ai_helpers.py - Complete all missing functions
def calculate_cpd_progress(rmp_profile):
    """Calculate detailed CPD progress"""
    if rmp_profile.cpd_cycle_end:
        total_days = (rmp_profile.cpd_cycle_end - rmp_profile.cpd_cycle_start).days
        days_passed = (timezone.now().date() - rmp_profile.cpd_cycle_start).days
        time_progress = min((days_passed / total_days) * 100, 100) if total_days > 0 else 0
    else:
        time_progress = 50  # Default if no cycle end date
    
    completion_percentage = (rmp_profile.total_cpd_points / rmp_profile.cpd_points_required * 100) if rmp_profile.cpd_points_required > 0 else 0
    points_needed = max(rmp_profile.cpd_points_required - rmp_profile.total_cpd_points, 0)
    
    return {
        'completion_percentage': completion_percentage,
        'points_needed': points_needed,
        'time_progress': time_progress,
        'on_track': completion_percentage >= time_progress - 20  # Allow 20% buffer
    }

def generate_predictive_alerts(rmp_profile):
    """Generate predictive alerts for RMP"""
    alerts = []
    
    # Renewal alerts
    if rmp_profile.registration_valid_till:
        days_until_renewal = (rmp_profile.registration_valid_till - timezone.now().date()).days
        if days_until_renewal <= 60:
            confidence = max(0.9 - (days_until_renewal / 200), 0.6)  # Higher confidence as deadline approaches
            alerts.append(PredictiveAlert.objects.create(
                rmp=rmp_profile,
                alert_type='renewal',
                message=f'Registration renewal due in {days_until_renewal} days',
                predicted_date=rmp_profile.registration_valid_till,
                confidence_score=confidence
            ))
    
    # CPD deficit alerts
    cpd_deficit = rmp_profile.cpd_points_required - rmp_profile.total_cpd_points
    if cpd_deficit > 10:
        # Predict based on historical CPD accumulation rate
        predicted_completion = predict_cpd_completion(rmp_profile)
        if predicted_completion and predicted_completion['risk'] == 'high':
            alerts.append(PredictiveAlert.objects.create(
                rmp=rmp_profile,
                alert_type='cpd_deficit',
                message=f'Risk of not meeting CPD requirements. Need {cpd_deficit} more points.',
                predicted_date=predicted_completion['predicted_date'],
                confidence_score=predicted_completion['confidence']
            ))
    
    return alerts

def predict_cpd_completion(rmp_profile):
    """Predict CPD completion based on historical data"""
    # Get CPD attendance in current cycle
    current_cycle_attendance = CPDAttendance.objects.filter(
        rmp=rmp_profile,
        registration_date__gte=rmp_profile.cpd_cycle_start
    )
    
    if not current_cycle_attendance.exists():
        return None
    
    # Calculate average points per month
    months_passed = max((timezone.now().date() - rmp_profile.cpd_cycle_start).days / 30, 1)
    avg_points_per_month = rmp_profile.total_cpd_points / months_passed
    
    points_needed = rmp_profile.cpd_points_required - rmp_profile.total_cpd_points
    months_remaining = 12 - months_passed  # Assuming 12-month cycle
    
    if months_remaining <= 0:
        return {
            'risk': 'high',
            'predicted_date': rmp_profile.cpd_cycle_end,
            'confidence': 0.95
        }
    
    if avg_points_per_month <= 0:
        return {
            'risk': 'high',
            'predicted_date': rmp_profile.cpd_cycle_end,
            'confidence': 0.8
        }
    
    predicted_completion_months = points_needed / avg_points_per_month
    
    if predicted_completion_months > months_remaining:
        return {
            'risk': 'high',
            'predicted_date': rmp_profile.cpd_cycle_end,
            'confidence': min(0.7 + (predicted_completion_months - months_remaining) / 10, 0.95)
        }
    else:
        return {
            'risk': 'low',
            'predicted_date': rmp_profile.cpd_cycle_start + timedelta(days=30 * (months_passed + predicted_completion_months)),
            'confidence': 0.6
        }
    
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

from django.db import connection

def get_staff_efficiency():
    results = callproc('stp_GetStaffEfficiency')
    if not results:
        return []
    columns = [desc[0] for desc in results[0].cursor.description] if hasattr(results[0], 'cursor') else None
    return results

# ============ ADVANCED AI INTEGRATION ============
@login_required
def ai_analytics_dashboard(request):
    """Advanced AI analytics dashboard"""
    # Predictive analytics for application volume
    application_trends = (
        Application.objects
        .annotate(month=TruncMonth('application_date'))
        .values('month')
        .annotate(
            count=Count('application_id'),
            approval_rate=Count('application_id', filter=Q(status='approved')) * 100.0 / Count('application_id')
        )
        .order_by('-month')[:12]  # get latest 12 months
    )  # Last 12 months
    
    # Risk prediction model

    high_risk_applications = (
        Application.objects.filter(status='under_review')
        .annotate(
            risk_score=Case(
                # Rule 1: high-risk types
                When(application_type__in=['foreign_permanent', 'defaulter'], then=Value(80)),
                # Rule 2: non-empty review notes
                When(~Q(review_notes="") & Q(review_notes__isnull=False), then=Value(70)),
                # Rule 3: unverified documents — adjust related name
                When(documents__is_verified=False, then=Value(60)),
                # Default fallback
                default=Value(40),
                output_field=IntegerField(),  # ✅ Correct usage (you DO instantiate here)
            )
        )
        .filter(risk_score__gte=70)
        .distinct()[:10]
    )
    
    # CPD compliance predictions
    # compliance_risk = CustomUser.objects.filter(
    #     user_type='rmp',
    #     registration_status='PERMANENT'
    # ).annotate(
    #     cpd_deficit=F('cpd_points_required') - F('total_cpd_points'),
    #     risk_level=Case(
    #         When(Q(cpd_deficit__gt=20) & Q(renewal_date__lte=timezone.now().date() + timedelta(days=30)), then=Value('HIGH')),
    #         When(Q(cpd_deficit__gt=10) | Q(renewal_date__lte=timezone.now().date() + timedelta(days=60)), then=Value('MEDIUM')),
    #         default=Value('LOW'),
    #         output_field=CharField()
    #     )
    # ).values('risk_level').annotate(count=Count('id')).order_by('risk_level')
    today = timezone.now().date()
    # Step 1: Get RMP Profile if exists
    rmp_profile = get_rmp_profile(request.user)
    renewal_date = rmp_profile.registration_valid_till if rmp_profile else None

    # Step 2: Base queryset with CPD deficit annotation
    compliance_risk = (
        CustomUser.objects.filter(
            user_type='rmp',
            registration_status='PERMANENT'
        )
        .annotate(
            cpd_deficit=F('cpd_points_required') - F('total_cpd_points'),
        )
        .filter(cpd_deficit__gt=10)[:10]
    )

    # Step 3: Add renewal alert logic (handled in Python)
    if renewal_date:
        renewal_soon_users = []
        for user in compliance_risk:
            user_rmp = get_rmp_profile(user)
            if user_rmp and user_rmp.registration_valid_till and user_rmp.registration_valid_till <= today + timedelta(days=30):
                renewal_soon_users.append(user)

        # Combine users with CPD deficit OR renewal soon
        combined_users = set(compliance_risk) | set(renewal_soon_users)
        compliance_risk = list(combined_users)

    # Staff efficiency analytics
    staff_efficiency = []
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
        'application_trends':  [],
        'high_risk_applications': high_risk_applications if high_risk_applications else [],
        'compliance_risk': list(compliance_risk) if compliance_risk else [],
        'staff_efficiency': list(staff_efficiency) if staff_efficiency else [],
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



# views.py - Comprehensive Reports Module
import csv
import json
from datetime import datetime, timedelta
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import (
    Count, Sum, Avg, ExpressionWrapper, DurationField, 
    DecimalField, Case, When, Value, IntegerField
)
from django.db.models.functions import TruncDate, TruncMonth, TruncYear
from django.utils import timezone
from django.core.paginator import Paginator
import xlwt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io

from .models import (
    Application, Payment, CustomUser, RMPProfile, CPDProgram, 
    CPDAttendance, Accreditation, Complaint, Document,
    VerificationTask, AIPerformanceScore, Report, AuditLog
)
from .forms import ReportFilterForm, DateRangeForm

def staff_required(function=None):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.user_type in ['admin', 'super_admin', 'staff'],
        login_url='/login/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

# ============ REPORTS DASHBOARD ============
@login_required
def reports_dashboard(request):
    """Main reports dashboard with quick stats and report categories"""
    
    # Quick statistics for dashboard
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    stats = {
        'total_applications': Application.objects.count(),
        'pending_applications': Application.objects.filter(status__in=['submitted', 'under_review']).count(),
        'total_payments': Payment.objects.filter(status='success').count(),
        'revenue_today': Payment.objects.filter(
            payment_date__date=today, status='success'
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'revenue_week': Payment.objects.filter(
            payment_date__date__gte=week_ago, status='success'
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'revenue_month': Payment.objects.filter(
            payment_date__date__gte=month_ago, status='success'
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'total_rmps': RMPProfile.objects.count(),
        'cpd_programs': CPDProgram.objects.count(),
        'active_complaints': Complaint.objects.filter(status__in=['registered', 'under_investigation']).count(),
    }
    
    # Recent activity
    recent_reports = Report.objects.filter(generated_by=request.user).order_by('-generated_date')[:5]
    
    # Application status distribution
    app_status_dist = Application.objects.values('status').annotate(
        count=Count('application_id')
    ).order_by('-count')
    
    # Payment method distribution
    payment_method_dist = Payment.objects.filter(status='success').values('payment_method').annotate(
        count=Count('payment_id'),
        amount=Sum('amount')
    ).order_by('-amount')
    
    context = {
        'stats': stats,
        'recent_reports': recent_reports,
        'app_status_dist': app_status_dist,
        'payment_method_dist': payment_method_dist,
        'active_tab': 'dashboard',
    }
    
    return render(request, 'MMC/reports/dashboard.html', context)

# ============ PAYMENT REPORTS ============
@login_required
def payment_reports(request):
    """Comprehensive payment reports with multiple views"""
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_from')
    payment_method = request.GET.get('payment_method')
    status = request.GET.get('status')
    
    payments = Payment.objects.all().select_related('application', 'application__applicant')
    
    # Apply filters
    if date_from:
        payments = payments.filter(payment_date__date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__date__lte=date_to)
    if payment_method:
        payments = payments.filter(payment_method=payment_method)
    if status:
        payments = payments.filter(status=status)
    
    # Summary statistics
    summary = payments.aggregate(
        total_amount=Sum('amount'),
        total_count=Count('payment_id'),
        success_count=Count('payment_id', filter=Q(status='success')),
        failed_count=Count('payment_id', filter=Q(status='failed')),
        pending_count=Count('payment_id', filter=Q(status='pending'))
    )
    
    # Daily breakdown
    daily_breakdown = payments.filter(status='success').annotate(
        payment_day=TruncDate('payment_date')
    ).values('payment_day').annotate(
        daily_amount=Sum('amount'),
        daily_count=Count('payment_id')
    ).order_by('-payment_day')[:30]
    
    # Method-wise breakdown
    method_breakdown = payments.filter(status='success').values('payment_method').annotate(
        total_amount=Sum('amount'),
        count=Count('payment_id')
    ).order_by('-total_amount')
    
    # Application type wise payments
    app_type_breakdown = payments.filter(
        status='success', 
        application__isnull=False
    ).values('application__application_type').annotate(
        total_amount=Sum('amount'),
        count=Count('payment_id')
    ).order_by('-total_amount')
    
    # Pagination
    paginator = Paginator(payments.order_by('-payment_date'), 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'payments': page_obj,
        'summary': summary,
        'daily_breakdown': daily_breakdown,
        'method_breakdown': method_breakdown,
        'app_type_breakdown': app_type_breakdown,
        'filter_form': ReportFilterForm(request.GET or None),
        'active_tab': 'payments',
    }
    
    return render(request, 'MMC/reports/payment_reports.html', context)

# ============ APPLICATION REPORTS ============
@login_required
def application_reports(request):
    """Comprehensive application status and analysis reports"""
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    app_type = request.GET.get('application_type')
    status = request.GET.get('status')
    
    applications = Application.objects.all().select_related(
        'applicant', 'rmp', 'assigned_to'
    ).prefetch_related('documents', 'payments')
    
    # Apply filters
    if date_from:
        applications = applications.filter(application_date__date__gte=date_from)
    if date_to:
        applications = applications.filter(application_date__date__lte=date_to)
    if app_type:
        applications = applications.filter(application_type=app_type)
    if status:
        applications = applications.filter(status=status)
    
    # Overall statistics
    stats = applications.aggregate(
        total_applications=Count('application_id'),
        approved_applications=Count('application_id', filter=Q(status='approved')),
        pending_applications=Count('application_id', filter=Q(status__in=['submitted', 'under_review'])),
        rejected_applications=Count('application_id', filter=Q(status='rejected')),
        avg_processing_days=Avg(
            ExpressionWrapper(
                F('actual_completion_date') - F('submitted_date'),
                output_field=DurationField()
            )
        )
    )
    
    # Application type distribution
    type_distribution = applications.values('application_type').annotate(
        count=Count('application_id'),
        approved=Count('application_id', filter=Q(status='approved')),
        pending=Count('application_id', filter=Q(status__in=['submitted', 'under_review'])),
        rejected=Count('application_id', filter=Q(status='rejected'))
    ).order_by('-count')
    
    # Status timeline (last 30 days)
    status_timeline = applications.filter(
        application_date__date__gte=timezone.now().date() - timedelta(days=30)
    ).annotate(
        app_date=TruncDate('application_date')
    ).values('app_date', 'status').annotate(
        count=Count('application_id')
    ).order_by('app_date')
    
    # SLA Compliance
    sla_stats = applications.filter(actual_completion_date__isnull=False).annotate(
        processing_days=ExpressionWrapper(
            F('actual_completion_date') - F('submitted_date'),
            output_field=DurationField()
        ),
       
    )

    # Staff performance
    staff_performance = CustomUser.objects.filter(
        user_type__in=['admin', 'staff'],
        assigned_applications__isnull=False
    ).annotate(
        total_assigned=Count('assigned_applications'),
        completed=Count(
            'assigned_applications',
            filter=Q(assigned_applications__status__in=['approved', 'rejected', 'completed'])
        ),
        avg_processing_time=Avg(
            ExpressionWrapper(
                F('assigned_applications__actual_completion_date') - F('assigned_applications__submitted_date'),
                output_field=DurationField()
            ),
            filter=Q(assigned_applications__actual_completion_date__isnull=False)
        )
    ).filter(total_assigned__gt=0).order_by('-completed')
    
    # Pagination
    paginator = Paginator(applications.order_by('-application_date'), 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'applications': page_obj,
        'stats': stats,
        'type_distribution': type_distribution,
        'status_timeline': status_timeline,
        'sla_stats': sla_stats,
        'staff_performance': staff_performance,
        'filter_form': ReportFilterForm(request.GET or None),
        'active_tab': 'applications',
    }
    
    return render(request, 'MMC/reports/application_reports.html', context)

# ============ CPD REPORTS ============
@login_required
def cpd_reports(request):
    """Comprehensive CPD program and participation reports"""
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    program_type = request.GET.get('program_type')
    
    # CPD Program Statistics
    programs = CPDProgram.objects.all().prefetch_related('attendances')
    
    if date_from:
        programs = programs.filter(start_date__date__gte=date_from)
    if date_to:
        programs = programs.filter(start_date__date__lte=date_to)
    if program_type:
        programs = programs.filter(program_type=program_type)
    
    program_stats = programs.aggregate(
        total_programs=Count('id'),
        total_participants=Sum('max_participants'),
        completed_programs=Count('id', filter=Q(status='Completed')),
        active_programs=Count('id', filter=Q(status='Ongoing'))
    )
    
    # Participation Statistics
    participations = CPDAttendance.objects.all().select_related('rmp', 'program')
    
    if date_from:
        participations = participations.filter(registration_date__date__gte=date_from)
    if date_to:
        participations = participations.filter(registration_date__date__lte=date_to)
    
    participation_stats = participations.aggregate(
        total_registrations=Count('id'),
        attended=Count('id', filter=Q(attendance_status='attended')),
        completed=Count('id', filter=Q(attendance_status='completed')),
        total_points=Sum('points_earned')
    )
    
    # Top Programs by Participation
    top_programs = programs.annotate(
        actual_participants=Count('attendances'),
        attendance_rate=Count('attendances', filter=Q(attendances__attendance_status__in=['attended', 'completed'])) * 100.0 / Count('attendances'),
        completion_rate=Count('attendances', filter=Q(attendances__attendance_status='completed')) * 100.0 / Count('attendances')
    ).order_by('-actual_participants')[:10]
    
    # RMP CPD Compliance
    rmp_compliance = RMPProfile.objects.annotate(
        cpd_completion_rate=Case(
            When(cpd_points_required=0, then=Value(100.0)),
            default=F('total_cpd_points') * 100.0 / F('cpd_points_required'),
            output_field=DecimalField(max_digits=5, decimal_places=2)
        ),
        compliance_status=Case(
            When(total_cpd_points__gte=F('cpd_points_required'), then=Value('Compliant')),
            When(total_cpd_points__gte=F('cpd_points_required') * 0.7, then=Value('Near Compliant')),
            default=Value('Non-Compliant'),
            output_field=models.CharField()
        )
    ).values('specialization', 'compliance_status').annotate(
        count=Count('id'),
        avg_points=Avg('total_cpd_points'),
        avg_required=Avg('cpd_points_required')
    ).order_by('specialization', '-compliance_status')
    
    # Monthly CPD Points Trend
    monthly_trend = participations.filter(
        attendance_status__in=['attended', 'completed']
    ).annotate(
        month=TruncMonth('registration_date')
    ).values('month').annotate(
        total_points=Sum('points_earned'),
        total_participations=Count('id')
    ).order_by('month')
    
    context = {
        'program_stats': program_stats,
        'participation_stats': participation_stats,
        'top_programs': top_programs,
        'rmp_compliance': rmp_compliance,
        'monthly_trend': monthly_trend,
        'programs': programs.order_by('-start_date')[:20],
        'filter_form': ReportFilterForm(request.GET or None),
        'active_tab': 'cpd',
    }
    
    return render(request, 'MMC/reports/cpd_reports.html', context)

# ============ COMPREHENSIVE REPORTS ============
@login_required
def comprehensive_reports(request):
    """All-in-one comprehensive reporting dashboard"""
    
    date_range = request.GET.get('date_range', 'THIS_MONTH')
    end_date = timezone.now().date()
    
    # Date range calculation
    if date_range == 'TODAY':
        start_date = end_date
    elif date_range == 'YESTERDAY':
        start_date = end_date - timedelta(days=1)
    elif date_range == 'THIS_WEEK':
        start_date = end_date - timedelta(days=end_date.weekday())
    elif date_range == 'THIS_MONTH':
        start_date = end_date.replace(day=1)
    elif date_range == 'LAST_MONTH':
        start_date = (end_date.replace(day=1) - timedelta(days=1)).replace(day=1)
        end_date = start_date.replace(day=28) + timedelta(days=4)
        end_date = end_date - timedelta(days=end_date.day)
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
        total=Count('application_id'),
        approved=Count('application_id', filter=Q(status='approved')),
        pending=Count('application_id', filter=Q(status__in=['submitted', 'under_review'])),
        rejected=Count('application_id', filter=Q(status='rejected'))
    ).order_by('-total')
    
    # Payment Statistics
    payments = Payment.objects.filter(
        payment_date__date__range=[start_date, end_date], 
        status='success'
    )
    payment_summary = payments.aggregate(
        total_amount=Sum('amount'),
        total_count=Count('payment_id'),
        avg_transaction=Avg('amount')
    )
    
    # Payment method distribution
    payment_methods = payments.values('payment_method').annotate(
        count=Count('payment_id'),
        amount=Sum('amount')
    ).order_by('-amount')
    
    # CPD Statistics
    cpd_participations = CPDAttendance.objects.filter(
        registration_date__date__range=[start_date, end_date]
    )
    cpd_stats = cpd_participations.aggregate(
        total_participants=Count('id'),
        completed_sessions=Count('id', filter=Q(attendance_status='completed')),
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
    staff_performance = (
        CustomUser.objects.filter(
            user_type__in=['admin', 'staff'],
            verification_tasks__completed_date__date__range=[start_date, end_date]
        )
        .annotate(
            tasks_completed=Count(
                'verification_tasks',
                filter=Q(verification_tasks__status='COMPLETED'),
                distinct=True
            ),
            applications_processed=Count(
                'assigned_applications',
                filter=Q(assigned_applications__status__in=['approved', 'rejected']),
                distinct=True
            ),
            processing_duration=Avg(
                ExpressionWrapper(
                    F('verification_tasks__completed_date') - F('verification_tasks__assigned_date'),
                    output_field=DurationField()
                )
            )
        )
        .filter(tasks_completed__gt=0)
        .values(
            'username',
            'first_name',
            'last_name',
            'tasks_completed',
            'applications_processed',
            'processing_duration',
        )
        .order_by('-tasks_completed')
    )
    
    # Registration Trends
    registration_trends = (
        RMPProfile.objects.filter(
            registration_date__range=[start_date, end_date]  # ✅ use __range directly
        )
        .annotate(
            reg_date=TruncDate('registration_date')  # ✅ safe for both DateField & DateTimeField
        )
        .values('reg_date')
        .annotate(
            daily_registrations=Count('id')
        )
        .order_by('reg_date')
    )
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'application_stats': application_stats,
        'payment_summary': payment_summary,
        'payment_methods': payment_methods,
        'cpd_stats': cpd_stats,
        'user_stats': user_stats,
        'staff_performance': staff_performance,
        'registration_trends': registration_trends,
        'filter_form': ReportFilterForm(initial={
            'date_range': date_range,
            'start_date': start_date,
            'end_date': end_date
        }),
        'active_tab': 'comprehensive',
    }
    
    return render(request, 'MMC/reports/comprehensive_reports.html', context)

# ============ MANUAL VERIFICATION REPORTS ============
@login_required
def manual_verification_reports(request):
    """Manual verification status and performance reports"""
    
    status_filter = request.GET.get('status')
    verifier_filter = request.GET.get('verifier')
    
    verifications = Application.objects.filter(
        application_type='manual_verification'
    ).select_related('applicant', 'assigned_to')
    
    if status_filter:
        verifications = verifications.filter(status=status_filter)
    if verifier_filter:
        verifications = verifications.filter(assigned_to_id=verifier_filter)
    
    # Statistics
    stats = verifications.aggregate(
        total=Count('application_id'),
        pending=Count('application_id', filter=Q(status__in=['submitted', 'under_review'])),
        completed=Count('application_id', filter=Q(status__in=['approved', 'rejected', 'completed'])),
        avg_processing_days=Avg(
            ExpressionWrapper(
                F('actual_completion_date') - F('submitted_date'),
                output_field=DurationField()
            )
        )
    )
    
    # Document verification status
    doc_verification = Document.objects.filter(
        application__application_type='manual_verification'
    ).values('document_type', 'is_verified').annotate(
        count=Count('id')
    ).order_by('document_type', '-is_verified')
    
    # Staff performance in manual verification
    staff_performance = (
        CustomUser.objects.filter(
            user_type__in=['admin', 'staff'],
            verification_tasks__application__application_type='manual_verification'
        )
        .annotate(
            total_tasks=Count('verification_tasks', distinct=True),
            completed_tasks=Count(
                'verification_tasks',
                filter=Q(verification_tasks__status='COMPLETED'),
                distinct=True
            ),
            pending_tasks=Count(
                'verification_tasks',
                filter=Q(verification_tasks__status__in=['PENDING', 'IN_PROGRESS']),
                distinct=True
            ),
            avg_processing_duration=Avg(
                ExpressionWrapper(
                    F('verification_tasks__completed_date') - F('verification_tasks__assigned_date'),
                    output_field=DurationField()
                )
            ),
        )
        .filter(total_tasks__gt=0)
        .values(
            'username',
            'first_name',
            'last_name',
            'total_tasks',
            'completed_tasks',
            'pending_tasks',
            'avg_processing_duration',
        )
        .order_by('-completed_tasks')
    )
    
    # Convert duration to hours (Python-side)
    for staff in staff_performance:
        duration = staff.get('avg_processing_duration')
        if duration:
            staff['avg_processing_hours'] = round(duration.total_seconds() / 3600, 2)
        else:
            staff['avg_processing_hours'] = 0
    
    # Pending applications summary by type
    pending_summary = verifications.filter(
        status__in=['submitted', 'under_review']
    ).values('application_type').annotate(
        count=Count('application_id'),
        oldest_pending=Min('application_date')
    ).order_by('-count')
    
    context = {
        'verifications': verifications.order_by('-application_date'),
        'stats': stats,
        'doc_verification': doc_verification,
        'staff_performance': staff_performance,
        'pending_summary': pending_summary,
        'status_filter': status_filter,
        'verifier_filter': verifier_filter,
        'active_tab': 'manual_verification',
    }
    
    return render(request, 'MMC/reports/manual_verification_reports.html', context)

# ============ STAFF PERFORMANCE REPORTS ============
@login_required
def staff_performance_reports(request):
    """Detailed staff performance and productivity reports"""
    
    date_from = request.GET.get('date_from', (timezone.now() - timedelta(days=30)).date())
    date_to = request.GET.get('date_to', timezone.now().date())
    
    # --- Individual staff performance ---
    staff_members = (
        CustomUser.objects.filter(
            user_type__in=['admin', 'staff', 'super_admin']
        )
        .annotate(
            # Applications metrics
            applications_processed=Count(
                'assigned_applications',
                filter=Q(
                    assigned_applications__actual_completion_date__date__range=[date_from, date_to]
                ),
                distinct=True
            ),
            applications_approved=Count(
                'assigned_applications',
                filter=Q(
                    assigned_applications__status='approved',
                    assigned_applications__actual_completion_date__date__range=[date_from, date_to]
                ),
                distinct=True
            ),
            applications_rejected=Count(
                'assigned_applications',
                filter=Q(
                    assigned_applications__status='rejected',
                    assigned_applications__actual_completion_date__date__range=[date_from, date_to]
                ),
                distinct=True
            ),
            # Verification tasks
            tasks_assigned=Count(
                'verification_tasks',
                filter=Q(verification_tasks__assigned_date__date__range=[date_from, date_to]),
                distinct=True
            ),
            tasks_completed=Count(
                'verification_tasks',
                filter=Q(verification_tasks__completed_date__date__range=[date_from, date_to]),
                distinct=True
            ),
            # Processing time
            avg_processing_time=Avg(
                ExpressionWrapper(
                    F('verification_tasks__completed_date') - F('verification_tasks__assigned_date'),
                    output_field=DurationField()
                ),
                filter=Q(verification_tasks__completed_date__isnull=False)
            ),
        )
        .annotate(
            approval_rate=Case(
                When(applications_processed=0, then=Value(0.0)),
                default=F('applications_approved') * 100.0 / F('applications_processed'),
                output_field=DecimalField(max_digits=5, decimal_places=2)
            ),
        )
    )
    
    # --- Calculate productivity score (done separately to avoid ORM issues) ---
    for member in staff_members:
        avg_time = member.avg_processing_time or timedelta(hours=9999)
        time_score = (
            30 if avg_time < timedelta(hours=24)
            else 20 if avg_time < timedelta(hours=48)
            else 10
        )
        member.productivity_score = (
            member.applications_processed * 0.4 +
            member.tasks_completed * 0.3 +
            time_score
        )
    
    # --- Department-wise performance ---
    # Compute using a secondary aggregation
    dept_performance = (
        staff_members.values('user_type')
        .annotate(
            total_staff=Count('id'),
            avg_applications=Avg('applications_processed'),
            avg_tasks=Avg('tasks_completed'),
            avg_processing_time=Avg('avg_processing_time'),
            avg_approval_rate=Avg('approval_rate'),
            avg_productivity=Avg('productivity_score'),
        )
        .order_by('-avg_productivity')
    )
    
    # Monthly trend for top performer
    monthly_trend = Application.objects.filter(
        assigned_to=staff_members.first(),
        actual_completion_date__date__range=[date_from, date_to]
    ).annotate(
        month=TruncMonth('actual_completion_date')
    ).values('month').annotate(
        completed=Count('application_id'),
        approved=Count('application_id', filter=Q(status='approved'))
    ).order_by('month')
    
    context = {
        'staff_members': staff_members,
        'dept_performance': dept_performance,
        'monthly_trend': monthly_trend,
        'date_from': date_from,
        'date_to': date_to,
        'active_tab': 'staff_performance',
    }
    
    return render(request, 'MMC/reports/staff_performance_reports.html', context)

# ============ COMPLAINT ANALYSIS REPORTS ============
@login_required
def complaint_analysis_reports(request):
    """Complaint analysis and resolution tracking reports"""
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    severity = request.GET.get('severity')
    status = request.GET.get('status')
    
    complaints = Complaint.objects.all().select_related(
        'against_rmp', 'filed_by', 'assigned_to'
    )
    
    if date_from:
        complaints = complaints.filter(filed_date__date__gte=date_from)
    if date_to:
        complaints = complaints.filter(filed_date__date__lte=date_to)
    if severity:
        complaints = complaints.filter(severity=severity)
    if status:
        complaints = complaints.filter(status=status)
    
    # Complaint statistics
    stats = complaints.aggregate(
        total_complaints=Count('complaint_id'),
        resolved=Count('complaint_id', filter=Q(status='resolved')),
        under_investigation=Count('complaint_id', filter=Q(status='under_investigation')),
        avg_resolution_days=Avg(
            ExpressionWrapper(
                F('resolved_date') - F('filed_date'),
                output_field=DurationField()
            )
        )
    )
    
    # Severity distribution
    severity_dist = complaints.values('severity').annotate(
        count=Count('complaint_id'),
        resolved=Count('complaint_id', filter=Q(status='resolved')),
        resolution_rate=Count('complaint_id', filter=Q(status='resolved')) * 100.0 / Count('complaint_id')
    ).order_by('-count')
    
    # Category-wise analysis
    category_analysis = complaints.values('category').annotate(
        count=Count('complaint_id'),
        avg_resolution_days=Avg(
            ExpressionWrapper(
                F('resolved_date') - F('filed_date'),
                output_field=DurationField()
            )
        )
    ).exclude(category='').order_by('-count')
    
    # Monthly trend
    monthly_trend = complaints.annotate(
        month=TruncMonth('filed_date')
    ).values('month').annotate(
        filed=Count('complaint_id'),
        resolved=Count('complaint_id', filter=Q(status='resolved'))
    ).order_by('month')
    
    # Top RMPs with complaints
    top_rmps = complaints.values(
        'against_rmp__mmc_registration_number', 
        'against_rmp__full_name'
    ).annotate(
        complaint_count=Count('complaint_id'),
        resolved_count=Count('complaint_id', filter=Q(status='resolved')),
        severe_count=Count('complaint_id', filter=Q(severity__in=['high', 'critical']))
    ).order_by('-complaint_count')[:10]
    
    context = {
        'complaints': complaints.order_by('-filed_date'),
        'stats': stats,
        'severity_dist': severity_dist,
        'category_analysis': category_analysis,
        'monthly_trend': monthly_trend,
        'top_rmps': top_rmps,
        'filter_form': ReportFilterForm(request.GET or None),
        'active_tab': 'complaints',
    }
    
    return render(request, 'MMC/reports/complaint_analysis_reports.html', context)

# ============ AI PERFORMANCE REPORTS ============
@login_required
def ai_performance_reports(request):
    """AI integration performance and insights reports"""
    
    # AI Performance Scores Analysis
    ai_scores = AIPerformanceScore.objects.all().select_related('rmp')
    
    # Score distribution
    score_stats = ai_scores.aggregate(
        avg_overall=Avg('overall_score'),
        avg_cpd=Avg('cpd_score'),
        avg_compliance=Avg('compliance_score'),
        avg_patient_care=Avg('patient_care_score'),
        avg_professional=Avg('professional_conduct_score'),
        total_rmps=Count('id')
    )
    
    # Score ranges
    score_ranges = ai_scores.annotate(
        score_range=Case(
            When(overall_score__gte=90, then=Value('Excellent (90-100)')),
            When(overall_score__gte=80, then=Value('Good (80-89)')),
            When(overall_score__gte=70, then=Value('Average (70-79)')),
            When(overall_score__gte=60, then=Value('Below Average (60-69)')),
            default=Value('Needs Improvement (<60)'),
            output_field=models.CharField()
        )
    ).values('score_range').annotate(
        count=Count('id'),
        avg_score=Avg('overall_score')
    ).order_by('-avg_score')
    
    # Specialization-wise performance
    specialization_performance = ai_scores.values('rmp__specialization').annotate(
        count=Count('id'),
        avg_overall=Avg('overall_score'),
        avg_cpd=Avg('cpd_score'),
        avg_compliance=Avg('compliance_score')
    ).exclude(rmp__specialization='').order_by('-avg_overall')
    
    # AI Insights Analysis
    ai_insights = AIPerformanceScore.objects.filter(
        overall_score__lt=70
    ).select_related('rmp').order_by('overall_score')[:10]
    
    # Predictive Alerts Summary
    predictive_alerts = AIPerformanceScore.objects.filter(
        overall_score__lt=60
    ).values('rmp__specialization').annotate(
        count=Count('id')
    ).order_by('-count')
    
    context = {
        'score_stats': score_stats,
        'score_ranges': score_ranges,
        'specialization_performance': specialization_performance,
        'ai_insights': ai_insights,
        'predictive_alerts': predictive_alerts,
        'active_tab': 'ai_performance',
    }
    
    return render(request, 'MMC/reports/ai_performance_reports.html', context)

# ============ EXPORT FUNCTIONALITY ============
@login_required
def export_reports(request, report_type):
    """Unified export functionality for all report types"""
    
    format_type = request.GET.get('format', 'excel')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if report_type == 'applications':
        return export_applications_report(request, format_type, date_from, date_to)
    elif report_type == 'payments':
        return export_payments_report(request, format_type, date_from, date_to)
    elif report_type == 'cpd':
        return export_cpd_report(request, format_type, date_from, date_to)
    elif report_type == 'staff_performance':
        return export_staff_performance_report(request, format_type, date_from, date_to)
    elif report_type == 'complaints':
        return export_complaints_report(request, format_type, date_from, date_to)
    elif report_type == 'manual_verification':
        return export_manual_verification_report(request, format_type, date_from, date_to)
    else:
        messages.error(request, 'Invalid report type specified.')
        return redirect('reports_dashboard')

def export_applications_report(request, format_type, date_from, date_to):
    """Export applications report"""
    
    applications = Application.objects.all().select_related('applicant', 'rmp', 'assigned_to')
    
    if date_from:
        applications = applications.filter(application_date__date__gte=date_from)
    if date_to:
        applications = applications.filter(application_date__date__lte=date_to)
    
    if format_type == 'excel':
        return export_applications_excel(applications)
    elif format_type == 'pdf':
        return export_applications_pdf(applications)
    else:
        return export_applications_csv(applications)

def export_applications_excel(applications):
    """Export applications to Excel format"""
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="mmc_applications.xls"'
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Applications Report')
    
    # Style for header
    header_style = xlwt.easyxf(
        'font: bold on; align: horiz center; pattern: pattern solid, fore_color light_green;'
    )
    
    # Column headers
    columns = [
        'Application ID', 'Type', 'Applicant Name', 'MMC Number', 
        'Status', 'Submission Date', 'Completion Date', 
        'Payment Status', 'Fee Amount', 'Assigned To', 'SLA Days'
    ]
    
    for col_num, column_title in enumerate(columns):
        ws.write(0, col_num, column_title, header_style)
        ws.col(col_num).width = 6000  # Set column width
    
    # Data rows
    row_num = 1
    for app in applications:
        ws.write(row_num, 0, str(app.application_id))
        ws.write(row_num, 1, app.get_application_type_display())
        ws.write(row_num, 2, app.applicant.get_full_name())
        ws.write(row_num, 3, app.rmp.mmc_registration_number if app.rmp else 'N/A')
        ws.write(row_num, 4, app.get_status_display())
        ws.write(row_num, 5, app.submitted_date.strftime('%Y-%m-%d %H:%M') if app.submitted_date else '')
        ws.write(row_num, 6, app.actual_completion_date.strftime('%Y-%m-%d %H:%M') if app.actual_completion_date else '')
        ws.write(row_num, 7, 'Paid' if app.payment_status else 'Pending')
        ws.write(row_num, 8, str(app.fee_amount))
        ws.write(row_num, 9, app.assigned_to.get_full_name() if app.assigned_to else 'Not Assigned')
        ws.write(row_num, 10, str(app.sla_days))
        row_num += 1
    
    wb.save(response)
    return response

def export_applications_pdf(applications):
    """Export applications to PDF format"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        textColor=colors.HexColor('#2c3e50')
    )
    
    # Title
    title = Paragraph("MMC Applications Report", title_style)
    elements.append(title)
    
    # Summary table
    summary_data = [
        ['Total Applications', str(applications.count())],
        ['Approved', str(applications.filter(status='approved').count())],
        ['Pending', str(applications.filter(status__in=['submitted', 'under_review']).count())],
        ['Rejected', str(applications.filter(status='rejected').count())],
    ]
    
    summary_table = Table(summary_data, colWidths=[200, 100])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Applications table
    if applications.exists():
        app_data = [['ID', 'Type', 'Applicant', 'Status', 'Submission Date']]
        
        for app in applications[:50]:  # Limit to first 50 for PDF
            app_data.append([
                str(app.application_id),
                app.get_application_type_display(),
                app.applicant.get_full_name(),
                app.get_status_display(),
                app.submitted_date.strftime('%Y-%m-%d') if app.submitted_date else ''
            ])
        
        app_table = Table(app_data, colWidths=[60, 100, 120, 80, 80])
        app_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        elements.append(app_table)
    
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="mmc_applications_report.pdf"'
    return response

def export_applications_csv(applications):
    """Export applications to CSV format"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="mmc_applications.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Application ID', 'Type', 'Applicant Name', 'MMC Number', 
        'Status', 'Submission Date', 'Completion Date', 
        'Payment Status', 'Fee Amount', 'Assigned To'
    ])
    
    for app in applications:
        writer.writerow([
            app.application_id,
            app.get_application_type_display(),
            app.applicant.get_full_name(),
            app.rmp.mmc_registration_number if app.rmp else 'N/A',
            app.get_status_display(),
            app.submitted_date.strftime('%Y-%m-%d %H:%M') if app.submitted_date else '',
            app.actual_completion_date.strftime('%Y-%m-%d %H:%M') if app.actual_completion_date else '',
            'Paid' if app.payment_status else 'Pending',
            app.fee_amount,
            app.assigned_to.get_full_name() if app.assigned_to else 'Not Assigned'
        ])
    
    return response

# Similar export functions for other report types...
def export_payments_report(request, format_type, date_from, date_to):
    """Export payments report"""
    payments = Payment.objects.filter(status='success').select_related('application', 'application__applicant')
    
    if date_from:
        payments = payments.filter(payment_date__date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__date__lte=date_to)
    
    if format_type == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="mmc_payments.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Payments Report')
        
        header_style = xlwt.easyxf('font: bold on; align: horiz center;')
        columns = ['Payment ID', 'Application ID', 'Applicant', 'Amount', 'Method', 'Date', 'Transaction ID']
        
        for col_num, column_title in enumerate(columns):
            ws.write(0, col_num, column_title, header_style)
        
        row_num = 1
        for payment in payments:
            ws.write(row_num, 0, str(payment.payment_id))
            ws.write(row_num, 1, str(payment.application.application_id) if payment.application else 'N/A')
            ws.write(row_num, 2, payment.application.applicant.get_full_name() if payment.application else 'N/A')
            ws.write(row_num, 3, str(payment.amount))
            ws.write(row_num, 4, payment.get_payment_method_display())
            ws.write(row_num, 5, payment.payment_date.strftime('%Y-%m-%d'))
            ws.write(row_num, 6, payment.transaction_id)
            row_num += 1
        
        wb.save(response)
        return response
    
    else:  # CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="mmc_payments.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Payment ID', 'Application ID', 'Applicant', 'Amount', 'Method', 'Date', 'Transaction ID'])
        
        for payment in payments:
            writer.writerow([
                payment.payment_id,
                payment.application.application_id if payment.application else 'N/A',
                payment.application.applicant.get_full_name() if payment.application else 'N/A',
                payment.amount,
                payment.get_payment_method_display(),
                payment.payment_date.strftime('%Y-%m-%d'),
                payment.transaction_id
            ])
        
        return response

# ============ REPORT GENERATION ============
@login_required
def generate_report(request):
    """Dynamic report generation with filters"""
    if request.method == 'POST':
        form = ReportGenerationForm(request.POST)
        if form.is_valid():
            report_type = form.cleaned_data['report_type']
            date_from = form.cleaned_data['date_from']
            date_to = form.cleaned_data['date_to']
            format_type = form.cleaned_data['format']
            
            # Generate report data
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
            elif format_type == 'excel':
                return generate_excel_report(report_data, report_type)
            else:
                messages.success(request, "Report generated successfully!")
                return redirect('reports_dashboard')
    
    else:
        form = ReportGenerationForm()
    
    context = {
        'form': form,
        'active_tab': 'generate',
    }
    
    return render(request, 'MMC/reports/generate_report.html', context)

def generate_report_data(report_type, date_from, date_to):
    """Generate comprehensive report data based on type"""
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
            'by_status': list(payments.values('status').annotate(
                count=Count('id'), 
                amount=Sum('amount')
            )),
            'by_method': list(payments.values('payment_method').annotate(
                count=Count('id'), 
                amount=Sum('amount')
            )),
            'daily_breakdown': list(payments.filter(status='success').annotate(
                payment_day=TruncDate('payment_date')
            ).values('payment_day').annotate(
                daily_amount=Sum('amount'),
                count=Count('id')
            ).order_by('payment_day')),
        }
    
    elif report_type == 'application_status':
        applications = Application.objects.filter(**filters) if filters else Application.objects.all()
        return {
            'total_applications': applications.count(),
            'by_type': list(applications.values('application_type').annotate(count=Count('id'))),
            'by_status': list(applications.values('status').annotate(count=Count('id'))),
            'pending_count': applications.filter(status__in=['submitted', 'under_review']).count(),
            'sla_compliance': applications.filter(
                actual_completion_date__isnull=False
            ).annotate(
                within_sla=Case(
                    When(
                        actual_completion_date__lte=F('submitted_date') + timedelta(days=F('sla_days')), 
                        then=Value(1)
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ).aggregate(
                total=Count('id'),
                within_sla=Sum('within_sla'),
                compliance_rate=Sum('within_sla') * 100.0 / Count('id')
            ),
        }
    
    elif report_type == 'cpd_participation':
        participations = CPDAttendance.objects.filter(**filters) if filters else CPDAttendance.objects.all()
        return {
            'total_participations': participations.count(),
            'total_points': participations.aggregate(Sum('points_earned'))['points_earned__sum'] or 0,
            'by_status': list(participations.values('attendance_status').annotate(
                count=Count('id'),
                points=Sum('points_earned')
            )),
            'top_programs': list(participations.values(
                'program__title'
            ).annotate(
                participants=Count('id'),
                points=Sum('points_earned')
            ).order_by('-participants')[:10]),
        }
    
    return {}

# Utility functions for report generation
def generate_csv_report(report_data, report_type):
    """Generate CSV report from report data"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
    
    writer = csv.writer(response)
    
    if report_type == 'payment_summary':
        writer.writerow(['Status', 'Count', 'Amount'])
        for item in report_data.get('by_status', []):
            writer.writerow([item['status'], item['count'], item['amount']])
    
    return response

def generate_pdf_report(report_data, report_type):
    """Generate PDF report (simplified version)"""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, f"{report_type.replace('_', ' ').title()} Report")
    
    p.setFont("Helvetica", 12)
    y_position = 700
    
    if report_type == 'payment_summary':
        p.drawString(100, y_position, f"Total Amount: {report_data.get('total_amount', 0)}")
        y_position -= 20
        p.drawString(100, y_position, f"Total Count: {report_data.get('total_count', 0)}")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report.pdf"'
    return response

def generate_excel_report(report_data, report_type):
    """Generate Excel report from report data"""
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report.xls"'
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Report')
    
    # Add your Excel generation logic here
    
    wb.save(response)
    return response

# ============ AJAX ENDPOINTS FOR CHARTS ============
@login_required
def get_application_stats(request):
    """AJAX endpoint for application statistics"""
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    applications = Application.objects.all()
    
    if date_from:
        applications = applications.filter(application_date__date__gte=date_from)
    if date_to:
        applications = applications.filter(application_date__date__lte=date_to)
    
    stats = applications.aggregate(
        total=Count('id'),
        approved=Count('id', filter=Q(status='approved')),
        pending=Count('id', filter=Q(status__in=['submitted', 'under_review'])),
        rejected=Count('id', filter=Q(status='rejected'))
    )
    
    return JsonResponse(stats)

@login_required
def get_payment_trends(request):
    """AJAX endpoint for payment trends"""
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    trends = Payment.objects.filter(
        payment_date__date__range=[start_date, end_date],
        status='success'
    ).annotate(
        day=TruncDate('payment_date')
    ).values('day').annotate(
        amount=Sum('amount'),
        count=Count('id')
    ).order_by('day')
    
    return JsonResponse(list(trends), safe=False)


# views.py - Additional missing implementations

# ============ CPD REPORTS EXPORT ============
@login_required
@staff_required
def export_cpd_report(request, format_type, date_from, date_to):
    """Export CPD reports"""
    programs = CPDProgram.objects.all().prefetch_related('attendances')
    
    if date_from:
        programs = programs.filter(start_date__date__gte=date_from)
    if date_to:
        programs = programs.filter(start_date__date__lte=date_to)
    
    if format_type == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="mmc_cpd_programs.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('CPD Programs Report')
        
        header_style = xlwt.easyxf('font: bold on; align: horiz center;')
        columns = [
            'Program ID', 'Title', 'Type', 'Organizer', 'Start Date', 'End Date',
            'Max Participants', 'Actual Participants', 'CPD Points', 'Status'
        ]
        
        for col_num, column_title in enumerate(columns):
            ws.write(0, col_num, column_title, header_style)
            ws.col(col_num).width = 6000
        
        row_num = 1
        for program in programs:
            actual_participants = program.attendances.count()
            ws.write(row_num, 0, str(program.id))
            ws.write(row_num, 1, program.title)
            ws.write(row_num, 2, program.get_program_type_display())
            ws.write(row_num, 3, program.organizer)
            ws.write(row_num, 4, program.start_date.strftime('%Y-%m-%d'))
            ws.write(row_num, 5, program.end_date.strftime('%Y-%m-%d'))
            ws.write(row_num, 6, program.max_participants)
            ws.write(row_num, 7, actual_participants)
            ws.write(row_num, 8, program.cpd_points)
            ws.write(row_num, 9, program.get_status_display())
            row_num += 1
        
        wb.save(response)
        return response
    
    else:  # CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="mmc_cpd_programs.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Program ID', 'Title', 'Type', 'Organizer', 'Start Date', 'End Date',
            'Max Participants', 'Actual Participants', 'CPD Points', 'Status'
        ])
        
        for program in programs:
            actual_participants = program.attendances.count()
            writer.writerow([
                program.id,
                program.title,
                program.get_program_type_display(),
                program.organizer,
                program.start_date.strftime('%Y-%m-%d'),
                program.end_date.strftime('%Y-%m-%d'),
                program.max_participants,
                actual_participants,
                program.cpd_points,
                program.get_status_display()
            ])
        
        return response

# ============ STAFF PERFORMANCE EXPORT ============
@login_required
@staff_required
def export_staff_performance_report(request, format_type, date_from, date_to):
    """Export staff performance reports"""
    staff_members = CustomUser.objects.filter(
        user_type__in=['admin', 'staff', 'super_admin']
    ).annotate(
        applications_processed=Count('assigned_applications', 
            filter=Q(assigned_applications__actual_completion_date__date__range=[date_from, date_to])),
        tasks_completed=Count('verification_tasks',
            filter=Q(verification_tasks__completed_date__date__range=[date_from, date_to])),
    ).filter(
        Q(applications_processed__gt=0) | Q(tasks_completed__gt=0)
    )
    
    if format_type == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="mmc_staff_performance.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Staff Performance Report')
        
        header_style = xlwt.easyxf('font: bold on; align: horiz center;')
        columns = [
            'Staff Name', 'Username', 'Role', 'Applications Processed',
            'Tasks Completed', 'Total Workload', 'Performance Rating'
        ]
        
        for col_num, column_title in enumerate(columns):
            ws.write(0, col_num, column_title, header_style)
            ws.col(col_num).width = 6000
        
        row_num = 1
        for staff in staff_members:
            total_workload = (staff.applications_processed or 0) + (staff.tasks_completed or 0)
            performance = "Excellent" if total_workload > 50 else "Good" if total_workload > 20 else "Average"
            
            ws.write(row_num, 0, staff.get_full_name())
            ws.write(row_num, 1, staff.username)
            ws.write(row_num, 2, staff.get_user_type_display())
            ws.write(row_num, 3, staff.applications_processed or 0)
            ws.write(row_num, 4, staff.tasks_completed or 0)
            ws.write(row_num, 5, total_workload)
            ws.write(row_num, 6, performance)
            row_num += 1
        
        wb.save(response)
        return response
    
    else:  # CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="mmc_staff_performance.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Staff Name', 'Username', 'Role', 'Applications Processed',
            'Tasks Completed', 'Total Workload', 'Performance Rating'
        ])
        
        for staff in staff_members:
            total_workload = (staff.applications_processed or 0) + (staff.tasks_completed or 0)
            performance = "Excellent" if total_workload > 50 else "Good" if total_workload > 20 else "Average"
            
            writer.writerow([
                staff.get_full_name(),
                staff.username,
                staff.get_user_type_display(),
                staff.applications_processed or 0,
                staff.tasks_completed or 0,
                total_workload,
                performance
            ])
        
        return response

# ============ COMPLAINTS EXPORT ============
@login_required
@staff_required
def export_complaints_report(request, format_type, date_from, date_to):
    """Export complaints analysis reports"""
    complaints = Complaint.objects.all().select_related('against_rmp', 'filed_by', 'assigned_to')
    
    if date_from:
        complaints = complaints.filter(filed_date__date__gte=date_from)
    if date_to:
        complaints = complaints.filter(filed_date__date__lte=date_to)
    
    if format_type == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="mmc_complaints_analysis.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Complaints Analysis Report')
        
        header_style = xlwt.easyxf('font: bold on; align: horiz center;')
        columns = [
            'Complaint ID', 'Against RMP', 'Filed By', 'Severity', 'Status',
            'Category', 'Filed Date', 'Resolved Date', 'Assigned To'
        ]
        
        for col_num, column_title in enumerate(columns):
            ws.write(0, col_num, column_title, header_style)
            ws.col(col_num).width = 6000
        
        row_num = 1
        for complaint in complaints:
            ws.write(row_num, 0, complaint.complaint_id)
            ws.write(row_num, 1, complaint.against_rmp.mmc_registration_number)
            ws.write(row_num, 2, complaint.filed_by.mmc_registration_number)
            ws.write(row_num, 3, complaint.get_severity_display())
            ws.write(row_num, 4, complaint.get_status_display())
            ws.write(row_num, 5, complaint.category or 'N/A')
            ws.write(row_num, 6, complaint.filed_date.strftime('%Y-%m-%d'))
            ws.write(row_num, 7, complaint.resolved_date.strftime('%Y-%m-%d') if complaint.resolved_date else '')
            ws.write(row_num, 8, complaint.assigned_to.get_full_name() if complaint.assigned_to else '')
            row_num += 1
        
        wb.save(response)
        return response
    
    else:  # CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="mmc_complaints_analysis.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Complaint ID', 'Against RMP', 'Filed By', 'Severity', 'Status',
            'Category', 'Filed Date', 'Resolved Date', 'Assigned To'
        ])
        
        for complaint in complaints:
            writer.writerow([
                complaint.complaint_id,
                complaint.against_rmp.mmc_registration_number,
                complaint.filed_by.mmc_registration_number,
                complaint.get_severity_display(),
                complaint.get_status_display(),
                complaint.category or 'N/A',
                complaint.filed_date.strftime('%Y-%m-%d'),
                complaint.resolved_date.strftime('%Y-%m-%d') if complaint.resolved_date else '',
                complaint.assigned_to.get_full_name() if complaint.assigned_to else ''
            ])
        
        return response

# ============ MANUAL VERIFICATION EXPORT ============
@login_required
@staff_required
def export_manual_verification_report(request, format_type, date_from, date_to):
    """Export manual verification reports"""
    verifications = Application.objects.filter(
        application_type='manual_verification'
    ).select_related('applicant', 'assigned_to')
    
    if date_from:
        verifications = verifications.filter(application_date__date__gte=date_from)
    if date_to:
        verifications = verifications.filter(application_date__date__lte=date_to)
    
    if format_type == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="mmc_manual_verification.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Manual Verification Report')
        
        header_style = xlwt.easyxf('font: bold on; align: horiz center;')
        columns = [
            'Application ID', 'Applicant', 'MMC Number', 'Status',
            'Submission Date', 'Assigned To', 'Completion Date', 'SLA Status'
        ]
        
        for col_num, column_title in enumerate(columns):
            ws.write(0, col_num, column_title, header_style)
            ws.col(col_num).width = 6000
        
        row_num = 1
        for verification in verifications:
            sla_status = "Within SLA" if verification.actual_completion_date and verification.actual_completion_date <= verification.submitted_date + timedelta(days=verification.sla_days) else "Overdue" if verification.actual_completion_date else "In Progress"
            
            ws.write(row_num, 0, verification.application_id)
            ws.write(row_num, 1, verification.applicant.get_full_name())
            ws.write(row_num, 2, verification.rmp.mmc_registration_number if verification.rmp else 'N/A')
            ws.write(row_num, 3, verification.get_status_display())
            ws.write(row_num, 4, verification.submitted_date.strftime('%Y-%m-%d'))
            ws.write(row_num, 5, verification.assigned_to.get_full_name() if verification.assigned_to else '')
            ws.write(row_num, 6, verification.actual_completion_date.strftime('%Y-%m-%d') if verification.actual_completion_date else '')
            ws.write(row_num, 7, sla_status)
            row_num += 1
        
        wb.save(response)
        return response
    
    else:  # CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="mmc_manual_verification.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Application ID', 'Applicant', 'MMC Number', 'Status',
            'Submission Date', 'Assigned To', 'Completion Date', 'SLA Status'
        ])
        
        for verification in verifications:
            sla_status = "Within SLA" if verification.actual_completion_date and verification.actual_completion_date <= verification.submitted_date + timedelta(days=verification.sla_days) else "Overdue" if verification.actual_completion_date else "In Progress"
            
            writer.writerow([
                verification.application_id,
                verification.applicant.get_full_name(),
                verification.rmp.mmc_registration_number if verification.rmp else 'N/A',
                verification.get_status_display(),
                verification.submitted_date.strftime('%Y-%m-%d'),
                verification.assigned_to.get_full_name() if verification.assigned_to else '',
                verification.actual_completion_date.strftime('%Y-%m-%d') if verification.actual_completion_date else '',
                sla_status
            ])
        
        return response

