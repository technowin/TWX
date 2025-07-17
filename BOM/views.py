from datetime import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.urls import reverse, reverse_lazy
from django.db.models import Q, Sum, F

from django.http import JsonResponse
from django.contrib import messages

from .models import (
    BOMHeader, BOMItem, Component, Supplier, ComponentSupplier,
    Inventory, InventoryLocation, Document, BOMRevision, Comment, ApprovalRequest
)
from .forms import (
    BOMHeaderForm, BOMItemForm, ComponentForm, ComponentSupplierForm,
    DocumentForm, CommentForm, ApprovalRequestForm, RejectionForm
)
from BOM import models

class DashboardView(TemplateView):
    template_name = 'BOM/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Recent BOMs
        context['recent_boms'] = BOMHeader.objects.all().order_by('-last_modified')[:5]
        
        # Pending approvals
        if self.request.user.has_perm('bom.approve_bom'):
            context['pending_approvals'] = ApprovalRequest.objects.filter(approved_by__isnull=True)
        
        # Low stock items
        context['low_stock_items'] = Inventory.objects.filter(
            quantity_on_hand__lt=F('min_stock_level')
        ).select_related('component', 'location')[:5]

        
        # BOM stats
        context['active_bom_count'] = BOMHeader.objects.filter(status='AC').count()
        context['draft_bom_count'] = BOMHeader.objects.filter(status='DR').count()
        
        return context

class BOMDetailView(DetailView):
    model = BOMHeader
    template_name = 'BOM/bom_detail.html'
    context_object_name = 'bom'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bom = self.object
        
        # Add forms for related models
        context['item_form'] = BOMItemForm(initial={'bom': bom})
        context['comment_form'] = CommentForm(initial={'bom': bom, 'author': self.request.user})
        context['document_form'] = DocumentForm(initial={'bom': bom, 'uploaded_by': self.request.user})
        
        # Get all components for the typeahead search
        context['all_components'] = Component.objects.all().values('id', 'part_number', 'description')
        
        # Check if user can approve
        context['can_approve'] = self.request.user.has_perm('bom.approve_bom')
        
        return context

class BOMCreateView(CreateView):
    model = BOMHeader
    form_class = BOMHeaderForm
    template_name = 'BOM/bom_form.html'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.status = 'DR'
        response = super().form_valid(form)
        messages.success(self.request, f"BOM {self.object.name} created successfully.")
        return response
    
    def get_success_url(self):
        return reverse('bom_detail', kwargs={'pk': self.object.pk})

class BOMUpdateView(UpdateView):
    model = BOMHeader
    form_class = BOMHeaderForm
    template_name = 'BOM/bom_form.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"BOM {self.object.name} updated successfully.")
        return response
    
    def get_success_url(self):
        return reverse('bom_detail', kwargs={'pk': self.object.pk})
    
from django.views.generic import DeleteView

class BOMDeleteView(DeleteView):
    model = BOMHeader
    template_name = 'BOM/bom_confirm_delete.html'
    context_object_name = 'bom'
    
    def get_success_url(self):
        messages.success(self.request, f"BOM {self.object.name} was deleted successfully.")
        return reverse('bom_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['child_boms'] = self.object.child_boms.all()
        return context
    
class BOMCompareView(View):
    template_name = 'BOM/bom_compare.html'
    
    def get(self, request, *args, **kwargs):
        bom_id = kwargs.get('pk')
        bom = get_object_or_404(BOMHeader, pk=bom_id)
        revisions = BOMRevision.objects.filter(bom=bom).order_by('-created_date')
        
        # Get the two revisions to compare
        rev1_id = request.GET.get('rev1')
        rev2_id = request.GET.get('rev2')
        
        rev1 = rev2 = None
        if rev1_id:
            rev1 = get_object_or_404(BOMRevision, pk=rev1_id)
        if rev2_id:
            rev2 = get_object_or_404(BOMRevision, pk=rev2_id)
        
        # If we have both revisions, generate the diff
        diff_data = None
        if rev1 and rev2:
            diff_data = self.generate_diff(rev1, rev2)
        
        context = {
            'bom': bom,
            'revisions': revisions,
            'rev1': rev1,
            'rev2': rev2,
            'diff_data': diff_data,
        }
        return render(request, self.template_name, context)
    
    def generate_diff(self, rev1, rev2):
        # This is a simplified diff - you might want to use a proper diff library
        items1 = rev1.snapshot_data.get('items', [])
        items2 = rev2.snapshot_data.get('items', [])
        
        # Create dictionaries for easy lookup
        items1_dict = {(item['component_id'], item.get('reference_designators', '')): item for item in items1}
        items2_dict = {(item['component_id'], item.get('reference_designators', '')): item for item in items2}
        
        all_keys = set(items1_dict.keys()).union(set(items2_dict.keys()))
        
        diff = []
        for key in sorted(all_keys):
            item1 = items1_dict.get(key)
            item2 = items2_dict.get(key)
            
            if item1 and not item2:
                # Item was removed
                diff.append({
                    'component_id': item1['component_id'],
                    'part_number': item1['part_number'],
                    'description': item1['description'],
                    'status': 'removed',
                    'qty1': item1['quantity'],
                    'qty2': None,
                })
            elif not item1 and item2:
                # Item was added
                diff.append({
                    'component_id': item2['component_id'],
                    'part_number': item2['part_number'],
                    'description': item2['description'],
                    'status': 'added',
                    'qty1': None,
                    'qty2': item2['quantity'],
                })
            else:
                # Item exists in both - check for changes
                if item1['quantity'] != item2['quantity'] or item1.get('notes', '') != item2.get('notes', ''):
                    diff.append({
                        'component_id': item1['component_id'],
                        'part_number': item1['part_number'],
                        'description': item1['description'],
                        'status': 'changed',
                        'qty1': item1['quantity'],
                        'qty2': item2['quantity'],
                        'notes1': item1.get('notes', ''),
                        'notes2': item2.get('notes', ''),
                    })
        
        return diff

class ComponentDetailView(DetailView):
    model = Component
    template_name = 'BOM/component_detail.html'
    context_object_name = 'component'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        component = self.object
        
        # Add forms for related models
        context['supplier_form'] = ComponentSupplierForm(initial={'component': component})
        context['document_form'] = DocumentForm(initial={'component': component, 'uploaded_by': self.request.user})
        
        # Get inventory summary
        context['inventory_summary'] = Inventory.objects.filter(component=component).select_related('location')
        
        # Get the unique BOMs where the component is used
        bom_ids = BOMItem.objects.filter(component=component).values_list('bom_id', flat=True).distinct()
        context['used_in_boms'] = BOMHeader.objects.filter(id__in=bom_ids)

        
        return context

# AJAX views for BOM editor functionality
class AddBOMItemView(View):
    def post(self, request, *args, **kwargs):
        bom_id = request.POST.get('bom')
        component_id = request.POST.get('component')
        quantity = request.POST.get('quantity')
        reference_designators = request.POST.get('reference_designators', '')
        notes = request.POST.get('notes', '')
        
        bom = get_object_or_404(BOMHeader, pk=bom_id)
        component = get_object_or_404(Component, pk=component_id)
        
        # Check if item already exists in BOM
        existing_item = BOMItem.objects.filter(bom=bom, component=component, reference_designators=reference_designators).first()
        if existing_item:
            return JsonResponse({
                'success': False,
                'message': 'This component with the same reference designators already exists in the BOM.'
            })
        
        # Create new item
        BOMItem.objects.create(
            bom=bom,
            component=component,
            quantity=quantity,
            reference_designators=reference_designators,
            notes=notes
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Component added to BOM successfully.'
        })

class RemoveBOMItemView(View):
    def post(self, request, *args, **kwargs):
        item_id = request.POST.get('item_id')
        item = get_object_or_404(BOMItem, pk=item_id)
        item.delete()
        return JsonResponse({'success': True})

class UpdateBOMItemView(View):
    def post(self, request, *args, **kwargs):
        item_id = request.POST.get('item_id')
        quantity = request.POST.get('quantity')
        reference_designators = request.POST.get('reference_designators', '')
        notes = request.POST.get('notes', '')
        
        item = get_object_or_404(BOMItem, pk=item_id)
        item.quantity = quantity
        item.reference_designators = reference_designators
        item.notes = notes
        item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'BOM item updated successfully.'
        })

# class RequestBOMApprovalView(View):
#     def post(self, request, *args, **kwargs):
#         bom_id = request.POST.get('bom_id')
#         comments = request.POST.get('comments', '')
        
#         bom = get_object_or_404(BOMHeader, pk=bom_id)
        
#         # Check if there's already a pending request
#         existing_request = ApprovalRequest.objects.filter(bom=bom, approved_by__isnull=True).first()
#         if existing_request:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'There is already a pending approval request for this BOM.'
#             })
        
#         # Create the approval request
#         ApprovalRequest.objects.create(
#             bom=bom,
#             requested_by=request.user,
#             comments=comments
#         )
        
#         # Update BOM status
#         bom.status = 'PE'
#         bom.save()
        
#         return JsonResponse({
#             'success': True,
#             'message': 'Approval request submitted successfully.'
#         })

class RequestBOMApprovalView(View):
    def post(self, request, *args, **kwargs):
        bom = get_object_or_404(BOMHeader, pk=self.kwargs['pk'])
        
        # Check if already has pending approval
        if ApprovalRequest.objects.filter(bom=bom, approved_by__isnull=True).exists():
            messages.warning(request, f"There is already a pending approval request for BOM {bom.name}")
            return redirect('bom_detail', pk=bom.pk)
        
        # Create the approval request
        approval = ApprovalRequest.objects.create(
            bom=bom,
            requested_by=request.user,
            comments=request.POST.get('comments', '')
        )
        
        # Update BOM status
        bom.status = 'PE'  # Pending Approval
        bom.save()
        
        messages.success(request, f"Approval requested for BOM {bom.name}")
        return redirect('bom_detail', pk=bom.pk)
    
    def get(self, request, *args, **kwargs):
        bom = get_object_or_404(BOMHeader, pk=self.kwargs['pk'])
        context = {
            'bom': bom,
            'form': ApprovalRequestForm(initial={
                'bom': bom,
                'requested_by': request.user
            })
        }
        return render(request, 'BOM/request_approval.html', context)
 
class ApproveBOMView( View):
    def post(self, request, *args, **kwargs):
        approval = get_object_or_404(ApprovalRequest, pk=self.kwargs['pk'])
        
        if approval.approved_by:
            messages.warning(request, "This request has already been approved")
            return redirect('bom_detail', pk=approval.bom.pk)
            
        approval.approved_by = request.user
        approval.approved_date = timezone.now()
        approval.save()
        
        # Update BOM status
        bom = approval.bom
        bom.status = 'AC'  # Active
        bom.save()
        
        messages.success(request, f"BOM {bom.name} approved successfully")
        return redirect('bom_detail', pk=bom.pk)

class RejectBOMView(View):
    def post(self, request, *args, **kwargs):
        approval = get_object_or_404(ApprovalRequest, pk=self.kwargs['pk'])
        bom = approval.bom
        
        if approval.status != "Pending":
            messages.warning(request, f"This request has already been {approval.status.lower()}")
            return redirect('bom_detail', pk=bom.pk)
            
        # Update approval request with rejection info
        approval.rejected_by = request.user
        approval.rejected_date = timezone.now()
        approval.rejection_reason = request.POST.get('rejection_reason', '')
        approval.save()
        
        # Update BOM status back to Draft
        bom.status = 'DR'
        bom.save()
        
        messages.warning(request, f"BOM {bom.name} has been rejected and returned to Draft status")
        return redirect('bom_detail', pk=bom.pk)
    
    def get(self, request, *args, **kwargs):
        approval = get_object_or_404(ApprovalRequest, pk=self.kwargs['pk'])
        context = {
            'approval': approval,
            'bom': approval.bom,
            'form': RejectionForm(initial={
                'approval_request': approval.id,
                'rejected_by': request.user.id
            })
        }
        return render(request, 'bom/reject_approval.html', context)
    

    
    def create_revision_snapshot(self, bom):
        # Create a JSON snapshot of the current BOM state
        items = []
        for item in bom.items.all():
            items.append({
                'component_id': item.component.id,
                'part_number': item.component.part_number,
                'description': item.component.description,
                'quantity': float(item.quantity),
                'reference_designators': item.reference_designators,
                'notes': item.notes,
            })
        
        snapshot_data = {
            'name': bom.name,
            'description': bom.description,
            'revision': bom.revision,
            'status': bom.status,
            'items': items,
        }
        
        BOMRevision.objects.create(
            bom=bom,
            revision=bom.revision,
            change_reason=f"Approved by {self.request.user.get_full_name()}",
            created_by=self.request.user,
            snapshot_data=snapshot_data
        )

from django.views.generic import ListView
from django.core.paginator import Paginator
from django.db.models import Q

class BOMListView(ListView):
    model = BOMHeader
    template_name = 'BOM/bom_list.html'
    context_object_name = 'boms'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search functionality
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(revision__icontains=search_query)
            )
        
        # Filter by status
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Sort by different fields
        sort_by = self.request.GET.get('sort_by', '-last_modified')
        if sort_by in ['name', 'revision', 'status', 'created_date', 'last_modified']:
            queryset = queryset.order_by(sort_by)
        
        return queryset.select_related('created_by')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = BOMHeader.STATUS_CHOICES
        context['search_query'] = self.request.GET.get('q', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['sort_by'] = self.request.GET.get('sort_by', '-last_modified')
        return context

class ComponentListView(ListView):
    model = Component
    template_name = 'BOM/component_list.html'
    context_object_name = 'components'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search functionality
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(part_number__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Filter by category
        category_filter = self.request.GET.get('category')
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        
        # Sort by different fields
        sort_by = self.request.GET.get('sort_by', 'part_number')
        if sort_by in ['part_number', 'category', 'created_date', 'last_modified']:
            queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category_choices'] = Component.CATEGORY_CHOICES
        context['search_query'] = self.request.GET.get('q', '')
        context['category_filter'] = self.request.GET.get('category', '')
        context['sort_by'] = self.request.GET.get('sort_by', 'part_number')
        return context

class AddCommentView(View):
    def post(self, request, *args, **kwargs):
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save()
            return JsonResponse({
                'success': True,
                'comment': {
                    'author': comment.author.get_full_name(),
                    'text': comment.text,
                    'created_date': comment.created_date.strftime("%b %d, %Y %H:%M"),
                }
            })
        return JsonResponse({
            'success': False,
            'errors': form.errors.as_json()
        }, status=400)

class ComponentCreateView(CreateView):
    model = Component
    form_class = ComponentForm
    template_name = 'BOM/component_form.html'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"Component {self.object.part_number} created successfully.")
        return response
    
    def get_success_url(self):
        return reverse('component_detail', kwargs={'pk': self.object.pk})

class ComponentUpdateView(UpdateView):
    model = Component
    form_class = ComponentForm
    template_name = 'BOM/component_form.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Component {self.object.part_number} updated successfully.")
        return response
    
    def get_success_url(self):
        return reverse('component_detail', kwargs={'pk': self.object.pk})
    
class AddComponentSupplierView(CreateView):
    model = ComponentSupplier
    form_class = ComponentSupplierForm
    template_name = 'BOM/component_supplier_form.html'  # We'll create this template
    
    def form_valid(self, form):
        component_id = self.kwargs['pk']
        component = get_object_or_404(Component, pk=component_id)
        form.instance.component = component
        response = super().form_valid(form)
        messages.success(self.request, f"Supplier added to {component.part_number} successfully.")
        return response
    
    def get_success_url(self):
        return reverse('component_detail', kwargs={'pk': self.kwargs['pk']})
    
from django.http import JsonResponse
from django.views import View
from django.core.serializers import serialize
import json
from .models import Component, Inventory, ComponentSupplier

class ComponentAPIView(View):
    def get(self, request, pk):
        try:
            component = Component.objects.get(pk=pk)
            
            # Get supplier information
            suppliers = []
            for cs in component.suppliers.all().select_related('supplier'):
                suppliers.append({
                    'id': cs.id,
                    'supplier_id': cs.supplier.id,
                    'supplier_name': cs.supplier.name,
                    'supplier_part_number': cs.supplier_part_number,
                    'cost': float(cs.cost),
                    'lead_time_days': cs.lead_time_days,
                    'is_approved': cs.is_approved,
                    'notes': cs.notes,
                })
            
            # Get inventory information
            inventory = []
            for inv in component.inventory.all().select_related('location'):
                inventory.append({
                    'id': inv.id,
                    'location_id': inv.location.id,
                    'location_name': inv.location.name,
                    'quantity_on_hand': inv.quantity_on_hand,
                    'quantity_allocated': inv.quantity_allocated,
                    'min_stock_level': inv.min_stock_level,
                    'last_updated': inv.last_updated.strftime("%Y-%m-%d %H:%M"),
                })
            
            # Get where used information
            where_used = []
            for item in component.bomitem_set.all().select_related('bom'):
                where_used.append({
                    'bom_id': item.bom.id,
                    'bom_name': item.bom.name,
                    'bom_revision': item.bom.revision,
                    'quantity': float(item.quantity),
                    'reference_designators': item.reference_designators,
                })
            
            # Prepare response data
            data = {
                'id': component.id,
                'part_number': component.part_number,
                'description': component.description,
                'category': component.category,
                'category_display': component.get_category_display(),
                'unit_of_measure': component.unit_of_measure,
                'material': component.material,
                'tolerance': component.tolerance,
                'finish': component.finish,
                'weight': float(component.weight) if component.weight else None,
                'thumbnail_url': component.thumbnail.url if component.thumbnail else None,
                'created_date': component.created_date.strftime("%Y-%m-%d %H:%M"),
                'last_modified': component.last_modified.strftime("%Y-%m-%d %H:%M"),
                'created_by': component.created_by.get_full_name() if component.created_by else None,
                'suppliers': suppliers,
                'inventory': inventory,
                'where_used': where_used,
            }
            
            return JsonResponse(data)
        except Component.DoesNotExist:
            return JsonResponse({'error': 'Component not found'}, status=404)