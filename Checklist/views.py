from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import FileResponse, HttpResponseRedirect
from django.db.models import Q
import csv
import zipfile
import os
from io import TextIOWrapper
from tempfile import TemporaryDirectory
from .models import Checklist, ChecklistDocument
from .forms import (
    ChecklistForm, ChecklistDocumentForm, 
    ChecklistBulkUploadForm, DocumentBulkUploadForm
)

class ChecklistListView(ListView):
    model = Checklist
    template_name = 'Checklist/checklist_list.html'
    context_object_name = 'checklists'
    paginate_by = 35
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search')
        type_filter = self.request.GET.get('type')
        risk_filter = self.request.GET.get('risk')
        
        if search_query:
            queryset = queryset.filter(
                Q(type__icontains=search_query) |
                Q(task__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        if type_filter:
            queryset = queryset.filter(type=type_filter)
            
        if risk_filter:
            queryset = queryset.filter(risk=risk_filter)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['type_choices'] = Checklist.objects.values_list('type', 'type').distinct()
        context['risk_choices'] = Checklist.RISK_CHOICES
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_type'] = self.request.GET.get('type', '')
        context['selected_risk'] = self.request.GET.get('risk', '')
        return context

def checklist_documents_view(request, checklist_type):
    documents = ChecklistDocument.objects.filter(checklist_type=checklist_type)
    checklist_items = Checklist.objects.filter(type=checklist_type)
    
    # Get PDF and DOC documents for this checklist type
    pdf_doc = documents.filter(doc_type='PDF').first()
    word_doc = documents.filter(doc_type='DOC').first()
    
    context = {
        'checklist_type': checklist_type,
        'checklist_items': checklist_items,
        'pdf_document': pdf_doc,
        'word_document': word_doc,
    }
    
    return render(request, 'Checklist/checklist_detail.html', context)

class ChecklistCreateView(CreateView):
    model = Checklist
    form_class = ChecklistForm
    template_name = 'Checklist/checklist_form.html'
    success_url = reverse_lazy('checklist_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Checklist item created successfully!')
        return super().form_valid(form)

class ChecklistUpdateView(UpdateView):
    model = Checklist
    form_class = ChecklistForm
    template_name = 'Checklist/checklist_form.html'
    success_url = reverse_lazy('checklist_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Checklist item updated successfully!')
        return super().form_valid(form)

class ChecklistDeleteView(DeleteView):
    model = Checklist
    template_name = 'Checklist/checklist_confirm_delete.html'
    success_url = reverse_lazy('checklist_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Checklist item deleted successfully!')
        return super().delete(request, *args, **kwargs)

class DocumentCreateView(CreateView):
    model = ChecklistDocument
    form_class = ChecklistDocumentForm
    template_name = 'Checklist/document_form.html'
    success_url = reverse_lazy('checklist_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Document uploaded successfully!')
        return super().form_valid(form)

class DocumentUpdateView(UpdateView):
    model = ChecklistDocument
    form_class = ChecklistDocumentForm
    template_name = 'Checklist/document_form.html'
    success_url = reverse_lazy('checklist_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Document updated successfully!')
        return super().form_valid(form)

class DocumentDeleteView(DeleteView):
    model = ChecklistDocument
    template_name = 'Checklist/document_confirm_delete.html'
    success_url = reverse_lazy('checklist_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Document deleted successfully!')
        return super().delete(request, *args, **kwargs)

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
import pandas as pd
from io import BytesIO
from openpyxl import Workbook
from .models import Checklist, ChecklistDocument
from .forms import ChecklistBulkUploadForm, DocumentBulkUploadForm

def download_checklist_template(request):
    """Generate and serve Excel template for checklist bulk upload"""
    # Create a workbook and add worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Compliance Checklist"
    
    # Add headers and sample data
    headers = ['type', 'task', 'description', 'risk']
    sample_data = [
        ['ISO 9001', 'Document Control', 'Verify document version control', 'High'],
        ['FDA', 'Product Labeling', 'Check label requirements', 'Critical'],
        ['GDPR', 'Data Consent', 'Verify user consent mechanisms', 'Medium']
    ]
    
    ws.append(headers)
    for row in sample_data:
        ws.append(row)
    
    # Create response
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=compliance_checklist_template.xlsx'
    return response

def bulk_upload_checklist(request):
    """Handle Excel file upload for checklist items"""
    if request.method == 'POST':
        form = ChecklistBulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                excel_file = request.FILES['excel_file']
                df = pd.read_excel(excel_file)
                
                # Validate required columns
                required_columns = {'type', 'task', 'description', 'risk'}
                if not required_columns.issubset(df.columns):
                    missing = required_columns - set(df.columns)
                    messages.error(request, f"Missing columns: {', '.join(missing)}")
                    return redirect('bulk_upload_checklist')
                
                created_count = 0
                for _, row in df.iterrows():
                    # Skip empty rows
                    if pd.isna(row['type']) or pd.isna(row['task']):
                        continue
                    
                    Checklist.objects.create(
                        type=row['type'],
                        task=row['task'],
                        description=row['description'] if not pd.isna(row['description']) else '',
                        risk=row['risk'] if not pd.isna(row['risk']) else 'Medium'
                    )
                    created_count += 1
                
                messages.success(request, f"Successfully imported {created_count} checklist items!")
                return redirect('checklist_list')
            
            except Exception as e:
                messages.error(request, f"Error processing Excel file: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ChecklistBulkUploadForm()
    
    return render(request, 'Checklist/bulk_upload_checklist.html', {'form': form})

def bulk_upload_documents(request):
    """Handle multiple document uploads with type selection"""
    if request.method == 'POST':
        form = DocumentBulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                doc_type = form.cleaned_data['doc_type']
                checklist_type = form.cleaned_data['checklist_type']
                files = request.FILES.getlist('document_files')
                
                uploaded_count = 0
                for file in files:
                    # Validate file extension
                    ext = file.name.split('.')[-1].lower()
                    if ext not in ['pdf', 'doc', 'docx']:
                        continue
                    
                    # Create document record
                    doc = ChecklistDocument(
                        checklist_type=checklist_type,
                        doc_type=doc_type,
                        file=file
                    )
                    doc.save()
                    uploaded_count += 1
                
                if uploaded_count > 0:
                    messages.success(request, f"Successfully uploaded {uploaded_count} documents!")
                else:
                    messages.warning(request, "No valid documents were uploaded.")
                return redirect('checklist_list')
            
            except Exception as e:
                messages.error(request, f"Error uploading documents: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DocumentBulkUploadForm()
    
    # Get unique checklist types for dropdown
    checklist_types = Checklist.objects.values_list('type', flat=True).distinct()
    return render(request, 'Checklist/bulk_upload_documents.html', {
        'form': form,
        'checklist_types': checklist_types
    })

def download_document(request, pk):
    document = get_object_or_404(ChecklistDocument, pk=pk)
    response = FileResponse(document.file.open('rb'))
    response['Content-Disposition'] = f'attachment; filename="{document.file.name}"'
    return response