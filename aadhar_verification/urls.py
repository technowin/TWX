from django.urls import path
from . import views

app_name = 'aadhar_verification'

urlpatterns = [
    # Main pages
    path('', views.aadhar_verification_home, name='aadhar_verification_home'),
    path('initiate/', views.initiate_verification, name='initiate_verification'),
    path('verify-otp/<int:request_id>/', views.verify_otp, name='verify_otp'),
    path('result/<int:request_id>/', views.verification_result, name='verification_result'),
    path('delete/<int:request_id>/', views.delete_verification, name='delete_verification'),
    path('list/', views.VerificationListView.as_view(), name='verification_list'),
    
    # Quick actions
    path('quick-verify/', views.quick_verify_modal, name='quick_verify_modal'),
    
    # API endpoints
    path('api/status/<int:request_id>/', views.api_verification_status, name='api_verification_status'),
]