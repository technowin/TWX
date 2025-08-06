from django.shortcuts import render
from .models import ChecklistType

def compliance_checklist(request):
    # Get all checklist types with their related data
    checklist_types = ChecklistType.objects.prefetch_related(
        'checklists', 
        'documents'
    ).all()
    
    context = {
        'checklist_types': checklist_types,
    }
    return render(request, 'Checklist/checklist.html', context)