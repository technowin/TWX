# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta

from .models import (
    MaterialPlan, MaterialPlanItem, PurchaseRequisition,
    InventoryReservation, ProductionOrder, MaterialShortageAlert
)
from BOM.models import BOMHeader, Component, Inventory, ComponentSupplier
from .forms import (
    MaterialPlanForm, MaterialPlanItemForm, PurchaseRequisitionForm,
    ProductionOrderForm, MaterialShortageResolutionForm
)

class MaterialPlanDashboardView(LoginRequiredMixin, View):
    template_name = 'MaterialPlan/dashboard.html'
    
    def get(self, request):
        # Get counts for dashboard cards
        pending_plans = MaterialPlan.objects.filter(status='draft').count()
        shortage_alerts = MaterialShortageAlert.objects.filter(status='open').count()
        late_orders = ProductionOrder.objects.filter(
            status__in=['planned', 'scheduled'],
            end_date__lt=timezone.now().date()
        ).count()
        
        # Get recent orders needing planning
        recent_orders = ProductionOrder.objects.filter(
            materialplan__isnull=True
        ).order_by('-created_at')[:10]
        
        context = {
            'pending_plans': pending_plans,
            'shortage_alerts': shortage_alerts,
            'late_orders': late_orders,
            'recent_orders': recent_orders,
        }
        return render(request, self.template_name, context)


class MaterialPlanListView(LoginRequiredMixin, ListView):
    model = MaterialPlan
    template_name = 'MaterialPlan/plan_list.html'
    context_object_name = 'plans'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.GET.get('status')
        search = self.request.GET.get('search')
        from django.db import models

        if status:
            queryset = queryset.filter(status=status)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(sales_order_reference__icontains=search) |
                models.Q(description__icontains=search)
            )
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = MaterialPlan.PLAN_STATUS_CHOICES
        return context


class MaterialPlanCreateView(LoginRequiredMixin, CreateView):
    model = MaterialPlan
    form_class = MaterialPlanForm
    template_name = 'MaterialPlan/plan_create.html'
    
    def get_success_url(self):
        return reverse_lazy('material_planning:plan_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.version = 1
        response = super().form_valid(form)
        
        # After creating the plan, automatically explode the BOM and create plan items
        self.object.calculate_requirements()
        
        messages.success(self.request, "Material plan created successfully. BOM has been exploded.")
        return response


class MaterialPlanDetailView(LoginRequiredMixin, DetailView):
    model = MaterialPlan
    template_name = 'MaterialPlan/plan_detail.html'
    context_object_name = 'plan'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan = self.get_object()
        
        # Get all plan items with their status
        items = plan.items.all().select_related('component', 'supplier')
        
        # Get any shortage alerts for this plan
        shortage_alerts = plan.alerts.filter(status='open')
        
        # Get purchase requisitions
        purchase_requisitions = plan.purchase_requisitions.all().select_related(
            'component', 'supplier'
        )
        
        context.update({
            'items': items,
            'shortage_alerts': shortage_alerts,
            'purchase_requisitions': purchase_requisitions,
            'status_choices': MaterialPlanItem.ITEM_STATUS_CHOICES,
        })
        return context


class MaterialPlanUpdateView(LoginRequiredMixin, UpdateView):
    model = MaterialPlan
    form_class = MaterialPlanForm
    template_name = 'MaterialPlan/plan_update.html'
    
    def get_success_url(self):
        return reverse_lazy('material_planning:plan_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        form.instance.last_updated = timezone.now()
        response = super().form_valid(form)
        messages.success(self.request, "Material plan updated successfully.")
        return response


class MaterialPlanItemUpdateView(LoginRequiredMixin, UpdateView):
    model = MaterialPlanItem
    form_class = MaterialPlanItemForm
    template_name = 'MaterialPlan/item_update.html'
    
    def get_success_url(self):
        return reverse_lazy('material_planning:plan_detail', kwargs={'pk': self.object.plan.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Plan item updated successfully.")
        return response


class PurchaseRequisitionCreateView(LoginRequiredMixin, View):
    template_name = 'MaterialPlan/requisition_create.html'
    
    def get(self, request, plan_id, item_id):
        plan = get_object_or_404(MaterialPlan, pk=plan_id)
        item = get_object_or_404(MaterialPlanItem, pk=item_id, plan=plan)
        
        # Get preferred suppliers for this component
        suppliers = ComponentSupplier.objects.filter(
            component=item.component,
            is_approved=True
        ).select_related('supplier').order_by('cost')
        
        form = PurchaseRequisitionForm(initial={
            'plan': plan,
            'plan_item': item,
            'component': item.component,
            'quantity': item.quantity_to_purchase,
            'required_by_date': item.required_date,
        })
        
        context = {
            'plan': plan,
            'item': item,
            'form': form,
            'suppliers': suppliers,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, plan_id, item_id):
        plan = get_object_or_404(MaterialPlan, pk=plan_id)
        item = get_object_or_404(MaterialPlanItem, pk=item_id, plan=plan)
        
        form = PurchaseRequisitionForm(request.POST)
        if form.is_valid():
            requisition = form.save(commit=False)
            requisition.plan = plan
            requisition.plan_item = item
            requisition.created_by = request.user
            requisition.status = 'draft'
            requisition.save()
            
            messages.success(request, "Purchase requisition created successfully.")
            return redirect('material_planning:plan_detail', pk=plan.pk)
        
        # Get preferred suppliers for this component
        suppliers = ComponentSupplier.objects.filter(
            component=item.component,
            is_approved=True
        ).select_related('supplier').order_by('cost')
        
        context = {
            'plan': plan,
            'item': item,
            'form': form,
            'suppliers': suppliers,
        }
        return render(request, self.template_name, context)


class PurchaseRequisitionSubmitView(LoginRequiredMixin, View):
    def post(self, request, pk):
        requisition = get_object_or_404(PurchaseRequisition, pk=pk)
        
        if requisition.status != 'draft':
            messages.error(request, "Only draft requisitions can be submitted.")
            return redirect('material_planning:plan_detail', pk=requisition.plan.pk)
        
        requisition.status = 'submitted'
        requisition.save()
        
        messages.success(request, "Purchase requisition submitted for approval.")
        return redirect('material_planning:plan_detail', pk=requisition.plan.pk)


class InventoryReservationView(LoginRequiredMixin, View):
    def post(self, request, plan_id, item_id):
        plan = get_object_or_404(MaterialPlan, pk=plan_id)
        item = get_object_or_404(MaterialPlanItem, pk=item_id, plan=plan)
        
        if item.quantity_available <= 0:
            messages.error(request, "No available inventory to reserve.")
            return redirect('material_planning:plan_detail', pk=plan.pk)
        
        # Find available inventory
        available_inventory = Inventory.objects.filter(
            component=item.component,
            quantity_on_hand__gt=0
        ).order_by('last_updated')
        
        quantity_to_reserve = min(
            float(item.quantity_available),
            float(item.quantity_required - item.quantity_reserved)
        )
        
        try:
            with transaction.atomic():
                for inventory in available_inventory:
                    if quantity_to_reserve <= 0:
                        break
                    
                    reservable = min(
                        float(inventory.quantity_on_hand - inventory.quantity_allocated),
                        quantity_to_reserve
                    )
                    
                    if reservable > 0:
                        InventoryReservation.objects.create(
                            plan=plan,
                            plan_item=item,
                            inventory=inventory,
                            quantity=reservable,
                        )
                        
                        inventory.quantity_allocated += reservable
                        inventory.save()
                        
                        quantity_to_reserve -= reservable
                
                item.quantity_reserved += (item.quantity_required - item.quantity_reserved - quantity_to_reserve)
                if item.quantity_reserved >= item.quantity_required:
                    item.status = 'reserved'
                else:
                    item.status = 'partially_fulfilled'
                item.save()
                
                messages.success(request, f"Successfully reserved inventory for {item.component.part_number}.")
        
        except Exception as e:
            messages.error(request, f"Error reserving inventory: {str(e)}")
        
        return redirect('material_planning:plan_detail', pk=plan.pk)


class MaterialShortageResolutionView(LoginRequiredMixin, View):
    template_name = 'MaterialPlan/shortage_resolution.html'
    
    def get(self, request, alert_id):
        alert = get_object_or_404(MaterialShortageAlert, pk=alert_id)
        form = MaterialShortageResolutionForm(instance=alert)
        
        context = {
            'alert': alert,
            'form': form,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, alert_id):
        alert = get_object_or_404(MaterialShortageAlert, pk=alert_id)
        form = MaterialShortageResolutionForm(request.POST, instance=alert)
        
        if form.is_valid():
            alert = form.save(commit=False)
            alert.status = 'resolved'
            alert.resolved_by = request.user
            alert.resolved_at = timezone.now()
            alert.save()
            
            messages.success(request, "Shortage alert resolved successfully.")
            return redirect('material_planning:plan_detail', pk=alert.plan.pk)
        
        context = {
            'alert': alert,
            'form': form,
        }
        return render(request, self.template_name, context)


class ProductionOrderCreateView(LoginRequiredMixin, CreateView):
    model = ProductionOrder
    form_class = ProductionOrderForm
    template_name = 'MaterialPlan/production_order_create.html'
    
    def get_success_url(self):
        return reverse_lazy('material_planning:production_order_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        
        # Create a material plan for this production order
        material_plan = MaterialPlan.objects.create(
            name=f"Material Plan for {self.object.order_number}",
            production_order=self.object,
            bom=self.object.bom,
            quantity=self.object.quantity,
            status='draft',
            created_by=self.request.user,
            due_date=self.object.start_date,
        )
        
        # Calculate requirements
        material_plan.calculate_requirements()
        
        messages.success(self.request, "Production order created with material plan.")
        return response


class ProductionOrderDetailView(LoginRequiredMixin, DetailView):
    model = ProductionOrder
    template_name = 'MaterialPlan/production_order_detail.html'
    context_object_name = 'order'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.get_object()
        
        # Get associated material plan if exists
        material_plan = MaterialPlan.objects.filter(production_order=order).first()
        
        context['material_plan'] = material_plan
        return context