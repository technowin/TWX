from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import ListView, DetailView
from django.utils.decorators import method_decorator
from django.db.models import Q
from django.core.paginator import Paginator
import json

from .models import AadharVerificationRequest, AadharVerificationResult, APIConfig
from .forms import AadharVerificationForm, AadharOTPVerificationForm
from .services import AadharVerificationService

@login_required
def aadhar_verification_home(request):
    """Aadhar verification home page"""
    recent_verifications = AadharVerificationRequest.objects.filter(
        user=request.user
    ).select_related('verification_result').order_by('-created_at')[:5]
    
    context = {
        'recent_verifications': recent_verifications,
        'total_verifications': AadharVerificationRequest.objects.filter(user=request.user).count(),
        'successful_verifications': AadharVerificationRequest.objects.filter(
            user=request.user, 
            status='verified'
        ).count(),
        'pending_verifications': AadharVerificationRequest.objects.filter(
            user=request.user,
            status__in=['initiated', 'otp_sent']
        ).count(),
    }
    return render(request, 'aadhar_verification/home.html', context)

@login_required
def initiate_verification(request):
    """Initiate Aadhar verification process"""
    if request.method == 'POST':
        form = AadharVerificationForm(request.POST)
        if form.is_valid():
            try:
                # Save verification request
                verification_request = form.save(commit=False)
                verification_request.user = request.user
                verification_request.save()
                
                # Generate OTP
                service = AadharVerificationService()
                otp_result = service.generate_otp(
                    aadhaar_number=verification_request.aadhaar_number,
                    consent="Y",
                    reason=verification_request.reason
                )
                
                if otp_result['success']:
                    # Update verification request with reference ID
                    verification_request.reference_id = otp_result['reference_id']
                    verification_request.transaction_id = otp_result.get('transaction_id')
                    verification_request.status = 'otp_sent'
                    verification_request.save()
                    
                    messages.success(request, 'OTP has been sent successfully to the registered mobile number.')
                    return redirect('aadhar_verification:verify_otp', request_id=verification_request.id)
                else:
                    verification_request.status = 'failed'
                    verification_request.save()
                    messages.error(request, f"Failed to send OTP: {otp_result['message']}")
                    
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
    else:
        form = AadharVerificationForm()
    
    context = {
        'form': form,
        'title': 'Aadhar Verification - Initiate'
    }
    return render(request, 'aadhar_verification/initiate.html', context)

@login_required
def verify_otp(request, request_id):
    """Verify OTP and complete verification"""
    verification_request = get_object_or_404(
        AadharVerificationRequest, 
        id=request_id, 
        user=request.user
    )
    
    if verification_request.status != 'otp_sent':
        messages.error(request, 'Invalid verification request.')
        return redirect('aadhar_verification:aadhar_verification_home')
    
    if request.method == 'POST':
        form = AadharOTPVerificationForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            reference_id = form.cleaned_data['reference_id']
            
            try:
                service = AadharVerificationService()
                verification_result = service.verify_otp(reference_id, otp)
                
                if verification_result['success']:
                    # Save verification result
                    save_verification_result(verification_request, verification_result)
                    verification_request.status = 'verified'
                    verification_request.transaction_id = verification_result.get('transaction_id')
                    verification_request.save()
                    
                    messages.success(request, 'Aadhar verification completed successfully!')
                    return redirect('aadhar_verification:verification_result', request_id=verification_request.id)
                else:
                    messages.error(request, f"Verification failed: {verification_result['message']}")
                    
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
    else:
        form = AadharOTPVerificationForm(initial={
            'reference_id': verification_request.reference_id
        })
    
    context = {
        'form': form,
        'verification_request': verification_request,
        'title': 'Verify OTP'
    }
    return render(request, 'aadhar_verification/verify_otp.html', context)

def save_verification_result(verification_request, verification_result):
    """Save verification result to database"""
    data = verification_result['data']
    address = data.get('address', {})
    
    AadharVerificationResult.objects.create(
        verification_request=verification_request,
        reference_id=data.get('reference_id'),
        status=data.get('status'),
        message=data.get('message'),
        care_of=data.get('care_of'),
        full_address=data.get('full_address'),
        date_of_birth=data.get('date_of_birth'),
        email_hash=data.get('email_hash'),
        gender=data.get('gender'),
        name=data.get('name'),
        year_of_birth=data.get('year_of_birth'),
        mobile_hash=data.get('mobile_hash'),
        photo=data.get('photo'),
        share_code=data.get('share_code'),
        transaction_id=verification_result.get('transaction_id'),
        # Address fields
        country=address.get('country'),
        district=address.get('district'),
        house=address.get('house'),
        landmark=address.get('landmark'),
        pincode=address.get('pincode'),
        post_office=address.get('post_office'),
        state=address.get('state'),
        street=address.get('street'),
        subdistrict=address.get('subdistrict'),
        vtc=address.get('vtc')
    )

@login_required
def verification_result(request, request_id):
    """Display verification result"""
    verification_request = get_object_or_404(
        AadharVerificationRequest, 
        id=request_id, 
        user=request.user
    )
    
    try:
        result = verification_request.verification_result
    except AadharVerificationResult.DoesNotExist:
        messages.error(request, 'Verification result not found.')
        return redirect('aadhar_verification:aadhar_verification_home')
    
    context = {
        'verification_request': verification_request,
        'result': result,
        'title': 'Verification Result'
    }
    return render(request, 'aadhar_verification/result.html', context)

@method_decorator(login_required, name='dispatch')
class VerificationListView(ListView):
    """List all verification requests"""
    model = AadharVerificationRequest
    template_name = 'aadhar_verification/list.html'
    context_object_name = 'verifications'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = AadharVerificationRequest.objects.filter(
            user=self.request.user
        ).select_related('verification_result').order_by('-created_at')
        
        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(aadhaar_number__icontains=search_query) |
                Q(reference_id__icontains=search_query) |
                Q(status__icontains=search_query)
            )
        
        # Status filter
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['total_count'] = self.get_queryset().count()
        return context

@login_required
def quick_verify_modal(request):
    """Quick verification modal content"""
    if request.method == 'POST':
        form = AadharVerificationForm(request.POST)
        if form.is_valid():
            # Similar to initiate_verification but return JSON for AJAX
            try:
                verification_request = form.save(commit=False)
                verification_request.user = request.user
                verification_request.save()
                
                service = AadharVerificationService()
                otp_result = service.generate_otp(
                    aadhaar_number=verification_request.aadhaar_number,
                    consent="Y",
                    reason=verification_request.reason
                )
                
                if otp_result['success']:
                    verification_request.reference_id = otp_result['reference_id']
                    verification_request.transaction_id = otp_result.get('transaction_id')
                    verification_request.status = 'otp_sent'
                    verification_request.save()
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'OTP sent successfully',
                        'request_id': str(verification_request.id)
                    })
                else:
                    verification_request.status = 'failed'
                    verification_request.save()
                    return JsonResponse({
                        'success': False,
                        'message': f"Failed to send OTP: {otp_result['message']}"
                    })
                    
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f"An error occurred: {str(e)}"
                })
        else:
            errors = form.errors.get_json_data()
            return JsonResponse({
                'success': False,
                'message': 'Form validation failed',
                'errors': errors
            })
    
    form = AadharVerificationForm()
    return render(request, 'aadhar_verification/quick_verify_modal.html', {'form': form})

@login_required
def delete_verification(request, request_id):
    """Delete verification request"""
    verification_request = get_object_or_404(
        AadharVerificationRequest, 
        id=request_id, 
        user=request.user
    )
    
    if request.method == 'POST':
        verification_request.delete()
        messages.success(request, 'Verification request deleted successfully.')
        return redirect('aadhar_verification:verification_list')
    
    context = {
        'verification_request': verification_request
    }
    return render(request, 'aadhar_verification/delete_confirm.html', context)

# API Views for AJAX calls
@login_required
def api_verification_status(request, request_id):
    """Get verification status via API"""
    verification = get_object_or_404(AadharVerificationRequest, id=request_id, user=request.user)
    
    return JsonResponse({
        'status': verification.status,
        'aadhaar_number': verification.get_masked_aadhaar(),
        'created_at': verification.created_at.isoformat(),
        'has_result': hasattr(verification, 'verification_result')
    })

@login_required
def verification_stats(request):
    """Get verification statistics for dashboard"""
    total = AadharVerificationRequest.objects.filter(user=request.user).count()
    verified = AadharVerificationRequest.objects.filter(user=request.user, status='verified').count()
    pending = AadharVerificationRequest.objects.filter(user=request.user, status__in=['initiated', 'otp_sent']).count()
    failed = AadharVerificationRequest.objects.filter(user=request.user, status='failed').count()
    
    return JsonResponse({
        'total': total,
        'verified': verified,
        'pending': pending,
        'failed': failed
    })