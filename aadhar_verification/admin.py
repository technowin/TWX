from django.contrib import admin
from .models import APIConfig, APIToken, AadharVerificationRequest, AadharVerificationResult, VerificationLog

@admin.register(APIConfig)
class APIConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_url', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(APIToken)
class APITokenAdmin(admin.ModelAdmin):
    list_display = ['config', 'is_active', 'expires_at', 'created_at']
    list_filter = ['is_active', 'config', 'created_at']
    readonly_fields = ['created_at']

@admin.register(AadharVerificationRequest)
class AadharVerificationRequestAdmin(admin.ModelAdmin):
    list_display = ['aadhaar_number', 'user', 'status', 'reference_id', 'created_at']
    list_filter = ['status', 'created_at', 'user']
    search_fields = ['aadhaar_number', 'reference_id', 'transaction_id']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'

@admin.register(AadharVerificationResult)
class AadharVerificationResultAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'gender', 'date_of_birth', 'verified_at']
    list_filter = ['status', 'gender', 'verified_at']
    search_fields = ['name', 'verification_request__aadhaar_number']
    readonly_fields = ['verified_at']
    
    def has_add_permission(self, request):
        return False

@admin.register(VerificationLog)
class VerificationLogAdmin(admin.ModelAdmin):
    list_display = ['log_type', 'status_code', 'created_at']
    list_filter = ['log_type', 'status_code', 'created_at']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False