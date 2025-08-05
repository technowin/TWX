from django.contrib import admin
from .models import ChecklistType, Checklist, ChecklistDoc

class ChecklistInline(admin.TabularInline):
    model = Checklist
    extra = 1
    fields = ('task', 'description', 'risk')
    ordering = ('task',)

class ChecklistDocInline(admin.TabularInline):
    model = ChecklistDoc
    extra = 1
    fields = ('doc_type', 'file', 'title')
    ordering = ('doc_type',)

@admin.register(ChecklistType)
class ChecklistTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    inlines = [ChecklistInline, ChecklistDocInline]
    prepopulated_fields = {'description': ('name',)}

@admin.register(Checklist)
class ChecklistAdmin(admin.ModelAdmin):
    list_display = ('type', 'task', 'risk', 'created_at')
    list_filter = ('type', 'risk')
    search_fields = ('task', 'description')
    list_select_related = ('type',)

@admin.register(ChecklistDoc)
class ChecklistDocAdmin(admin.ModelAdmin):
    list_display = ('checklist_type', 'title', 'doc_type', 'uploaded_at')
    list_filter = ('checklist_type', 'doc_type')
    search_fields = ('title', 'checklist_type__name')
    list_select_related = ('checklist_type',)