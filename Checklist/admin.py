from django.contrib import admin
from .models import Checklist, ChecklistDocument

class ChecklistAdmin(admin.ModelAdmin):
    list_display = ('type', 'task', 'risk', 'created_at')
    list_filter = ('type', 'risk')
    search_fields = ('type', 'task', 'description')
    ordering = ('type', 'task')

class ChecklistDocumentAdmin(admin.ModelAdmin):
    list_display = ('checklist_type', 'doc_type', 'uploaded_at')
    list_filter = ('checklist_type', 'doc_type')
    search_fields = ('checklist_type',)
    ordering = ('checklist_type', 'doc_type')

admin.site.register(Checklist, ChecklistAdmin)
admin.site.register(ChecklistDocument, ChecklistDocumentAdmin)