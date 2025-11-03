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
from decimal import Decimal

from PLM.models import StatusAction


from .models import (
    MaterialPlan, MaterialPlanItem, PurchaseRequisition,
    InventoryReservation, ProductionOrder, MaterialShortageAlert
)
from BOM.models import BOMHeader, Component, Inventory, ComponentSupplier
from .forms import (
    MaterialPlanForm, MaterialPlanItemForm, PurchaseRequisitionForm,
    ProductionOrderForm, MaterialShortageResolutionForm
)

class MaterialPlanDashboardView(View):
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


class MaterialPlanListView(ListView):
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


class MaterialPlanCreateView(CreateView):
    model = MaterialPlan
    form_class = MaterialPlanForm
    template_name = 'MaterialPlan/plan_form.html'

    def get_initial(self):
        initial = super().get_initial()

        # Handle Production Order (dropdown expects pk)
        po_order = self.request.GET.get('po_order')
        if po_order:
            try:
                initial['production_order'] = ProductionOrder.objects.get(order_number=po_order).pk
            except ProductionOrder.DoesNotExist:
                pass

        # Handle BOM (dropdown expects pk)
        bom_header = self.request.GET.get('bom_header')
        if bom_header:
            try:
                initial['bom'] = BOMHeader.objects.get(name=bom_header).pk
            except BOMHeader.DoesNotExist:
                pass
        initial['quantity'] = self.request.GET.get('quantity')
        if po_order and bom_header:
            self.index = 1
        else:
            self.index = 0

        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['index'] = getattr(self, 'index', 0)  # Default to 0 if not set
        return context

    def get_success_url(self):
        # Use the named URL pattern (make sure you have it in urls.py as "plan_detail")
        return reverse_lazy('plan_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):

        index = self.request.POST.get('index', 0)

        form.instance.created_by = self.request.user
        form.instance.version = 1
        response = super().form_valid(form)

        self.object.calculate_requirements()

        if index == '1' and form.instance.production_order:
            try:
                production_order = form.instance.production_order
                production_order.order_status = get_object_or_404(StatusAction , id =3)  # Update status to 3
                production_order.save()
                messages.success(self.request, f"MRP Completed Successfully for  order {production_order.order_number}")
                return redirect('plm_index')
            except Exception as e:
                messages.warning(self.request, f"Material plan created but failed to update production order status: {str(e)}")

        messages.success(self.request, "Material plan created successfully. BOM has been exploded.")
        return response



class MaterialPlanDetailView(DetailView):
    model = MaterialPlan
    template_name = 'MaterialPlan/plan_detail.html'
    context_object_name = 'plan'
    
    def get_context_data(self, **kwargs):
        try:
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
        except Exception as e:
                print(f"Error fetching form data: {e}")



from django.http import Http404

class MaterialPlanDetailViewIndex(DetailView):
    model = MaterialPlan
    template_name = 'MaterialPlan/plan_detail.html'
    context_object_name = 'plan'

    def get_object(self, queryset=None):
        po_order = self.request.GET.get("po_order")
        bom_header = self.request.GET.get("bom_header")

        if not (po_order and bom_header):
            raise Http404("Production order and component are required")

        plan = MaterialPlan.objects.filter(
            production_order__order_number=po_order,
            bom__name=bom_header
        ).first()

        if not plan:
            raise Http404("No MaterialPlan found for given criteria")

        return plan

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan = self.object  # already set by get_object()

        context.update({
            "items": plan.items.all().select_related("component", "supplier"),
            "shortage_alerts": plan.alerts.filter(status="open"),
            "purchase_requisitions": plan.purchase_requisitions.all().select_related(
                "component", "supplier"
            ),
            "status_choices": MaterialPlanItem.ITEM_STATUS_CHOICES,
        })
        return context



class MaterialPlanUpdateView(UpdateView):
    model = MaterialPlan
    form_class = MaterialPlanForm
    template_name = 'MaterialPlan/plan_form.html'
    
    def get_success_url(self):
        return reverse_lazy('/plan_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        form.instance.last_updated = timezone.now()
        response = super().form_valid(form)
        messages.success(self.request, "Material plan updated successfully.")
        return response


class MaterialPlanItemUpdateView(UpdateView):
    model = MaterialPlanItem
    form_class = MaterialPlanItemForm
    template_name = 'MaterialPlan/item_update.html'
    
    def get_success_url(self):
        return reverse_lazy('/plan_detail', kwargs={'pk': self.object.plan.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Plan item updated successfully.")
        return response


class PurchaseRequisitionCreateView(View):
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
            return redirect('/plan_detail', pk=plan.pk)
        
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


class PurchaseRequisitionSubmitView(View):
    def post(self, request, pk):
        requisition = get_object_or_404(PurchaseRequisition, pk=pk)
        
        if requisition.status != 'draft':
            messages.error(request, "Only draft requisitions can be submitted.")
            return redirect('/plan_detail', pk=requisition.plan.pk)
        
        requisition.status = 'submitted'
        requisition.save()
        
        messages.success(request, "Purchase requisition submitted for approval.")
        return redirect('/plan_detail', pk=requisition.plan.pk)


class InventoryReservationView(View):
    def post(self, request, plan_id, item_id):
        plan = get_object_or_404(MaterialPlan, pk=plan_id)
        item = get_object_or_404(MaterialPlanItem, pk=item_id, plan=plan)
        
        if item.quantity_available <= 0:
            messages.error(request, "No available inventory to reserve.")
            return redirect('plan_detail', pk=plan.pk)
        
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
                quantity_to_reserve = Decimal(str(quantity_to_reserve))  # ensure Decimal

                for inventory in available_inventory:
                    if quantity_to_reserve <= 0:
                        break

                    reservable = min(
                        inventory.quantity_on_hand - inventory.quantity_allocated,
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

        return redirect('plan_detail', pk=plan.pk)


class MaterialShortageResolutionView(View):
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
            return redirect('/plan_detail', pk=alert.plan.pk)
        
        context = {
            'alert': alert,
            'form': form,
        }
        return render(request, self.template_name, context)


class ProductionOrderCreateView(CreateView):
    model = ProductionOrder
    form_class = ProductionOrderForm
    template_name = 'MaterialPlan/production_order_create.html'
    
    def get_success_url(self):
        # ✅ Use the URL name, not the path
        return reverse_lazy('plm_index')
    
    def form_valid(self, form):
        # Set user and default status
        form.instance.created_by = self.request.user
        form.instance.order_status = get_object_or_404(StatusAction, id=1)
        
        response = super().form_valid(form)
        messages.success(self.request, "Production order created with material plan.")
        return response

class ProductionOrderDetailView(DetailView):
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
    
# material_planning/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, F, ExpressionWrapper, fields
from django.db.models.functions import Coalesce
from datetime import date, timedelta
from .models import (
    MaterialPlan, MaterialPlanItem, PurchaseRequisition, 
    InventoryReservation, MaterialShortageAlert, ProductionOrder
)
from BOM.models import Inventory


@login_required
def mtp_dashboard(request):
    # Total active plans (draft or confirmed)
    total_active_plans = MaterialPlan.objects.filter(
        Q(status='confirmed') | Q(status='draft')
    ).count()

    # Total open shortage alerts
    total_shortage_alerts = MaterialShortageAlert.objects.filter(
        status='open'
    ).count()

    # Critical components based on coverage ratio
    critical_components = MaterialPlanItem.objects.annotate(
        coverage_ratio=ExpressionWrapper(
            F('quantity_available') * 100.0 / F('quantity_required'),
            output_field=fields.FloatField()
        )
    ).filter(
        coverage_ratio__lt=100,
        plan__status='confirmed'
    ).order_by('coverage_ratio')[:5]

    # Procurement status breakdown
    requisition_status = PurchaseRequisition.objects.values('status').annotate(
        count=Count('id'),
        total_quantity=Sum('quantity'),
        total_cost=Sum(
            ExpressionWrapper(
                F('quantity') * F('unit_cost'),
                output_field=fields.DecimalField()
            )
        )
    ).order_by('status')

    # Material shortage alerts (latest 5)
    shortage_alerts = MaterialShortageAlert.objects.filter(
        status='open'
    ).select_related('component', 'plan').order_by('required_date')[:5]

    # Production order readiness (% of fulfilled material plan items)
    production_orders = ProductionOrder.objects.filter(
        status__in=['planned', 'scheduled']
    ).annotate(
        total_items=Count('materialplan__items'),
        fulfilled_items=Count('materialplan__items', filter=Q(materialplan__items__status='fulfilled')),
        material_readiness=ExpressionWrapper(
            100.0 * F('fulfilled_items') / Coalesce(F('total_items'), 1),
            output_field=fields.FloatField()
        )
    ).order_by('start_date')[:5]

    # Inventory coverage by component category
    inventory_coverage = MaterialPlanItem.objects.filter(
        plan__status='confirmed'
    ).values('component__category').annotate(
        total_required=Sum('quantity_required'),
        total_available=Sum('quantity_available'),
        coverage=ExpressionWrapper(
            Sum('quantity_available') * 100.0 / Coalesce(Sum('quantity_required'), 1),
            output_field=fields.FloatField()
        )
    ).order_by('coverage')

    # Time-based material requirement forecast
    today = date.today()
    date_ranges = [
        (today, today + timedelta(days=7)),
        (today + timedelta(days=7), today + timedelta(days=14)),
        (today + timedelta(days=14), today + timedelta(days=30)),
        (today + timedelta(days=30), today + timedelta(days=60)),
    ]

    time_based_requirements = []
    for start_date, end_date in date_ranges:
        requirements = MaterialPlanItem.objects.filter(
            required_date__gte=start_date,
            required_date__lt=end_date,
            plan__status='confirmed'
        ).aggregate(
            total_required=Sum('quantity_required'),
            total_available=Sum('quantity_available'),
            components=Count('component', distinct=True)
        )

        time_based_requirements.append({
            'range': f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}",
            'required': requirements['total_required'] or 0,
            'available': requirements['total_available'] or 0,
            'components': requirements['components'] or 0
        })

    context = {
        'total_active_plans': total_active_plans,
        'total_shortage_alerts': total_shortage_alerts,
        'critical_components': critical_components,
        'requisition_status': requisition_status,
        'shortage_alerts': shortage_alerts,
        'production_orders': production_orders,
        'inventory_coverage': inventory_coverage,
        'time_based_requirements': time_based_requirements,
    }

    return render(request, 'MaterialPlan/dashboard2.html', context)


# material_planning/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q, F, Value, Case, When, IntegerField
from django.utils import timezone

from .models import (
    MaterialPlan, MaterialPlanItem, PurchaseRequisition,
    MaterialShortageAlert, InventoryReservation
)
from BOM.models import Component, Inventory


@login_required
def mtp_dashboar3(request):
    # Summary statistics
    total_plans = MaterialPlan.objects.count()
    active_plans = MaterialPlan.objects.exclude(status__in=['cancelled', 'executed']).count()
    open_shortages = MaterialShortageAlert.objects.filter(status='open').count()
    pending_requisitions = PurchaseRequisition.objects.filter(status='draft').count()

    # Material status breakdown
    material_status = MaterialPlanItem.objects.values('status').annotate(
        count=Count('id'),
        total_quantity=Sum('quantity_required')
    ).order_by('status')

    # Critical shortages (top 10 within 7 days)
    critical_shortages = MaterialShortageAlert.objects.filter(
        status='open',
        required_date__lte=timezone.now() + timezone.timedelta(days=7)
    ).order_by('required_date')[:10]

    # Upcoming material requirements (next 30 days)
    upcoming_requirements = MaterialPlanItem.objects.filter(
        required_date__gte=timezone.now(),
        required_date__lte=timezone.now() + timezone.timedelta(days=30)
    ).select_related('component', 'plan').order_by('required_date')[:15]

    # Inventory health (low stock components)
    inventory_health = Inventory.objects.annotate(
        shortage=Case(
            When(quantity_on_hand__lt=F('min_stock_level'), then=Value(1)),
            default=Value(0),
            output_field=IntegerField()
        )
    ).filter(shortage=1).select_related('component')[:10]

    # Cost analysis by component category
    cost_analysis = PurchaseRequisition.objects.filter(
        status__in=['approved', 'ordered']
    ).values('component__category').annotate(
        total_cost=Sum(F('quantity') * F('unit_cost')),
        count=Count('id')
    ).order_by('-total_cost')

    # Plan status overview
    plan_status = MaterialPlan.objects.values('status').annotate(
        count=Count('id'),
        total_quantity=Sum('quantity')
    ).order_by('status')

    context = {
        'total_plans': total_plans,
        'active_plans': active_plans,
        'open_shortages': open_shortages,
        'pending_requisitions': pending_requisitions,
        'material_status': list(material_status),
        'critical_shortages': critical_shortages,
        'upcoming_requirements': upcoming_requirements,
        'inventory_health': inventory_health,
        'cost_analysis': list(cost_analysis),
        'plan_status': list(plan_status),
    }

    return render(request, 'MaterialPlan/dashboard3.html', context)

# material_planning/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import MaterialShortageAlert
from BOM.models import Component, Inventory

@login_required
def shortage_list(request):
    # Get all open shortages ordered by urgency
    shortages = MaterialShortageAlert.objects.filter(
        status='open'
    ).order_by('required_date')
    
    # Group by component for summary view
    component_shortages = MaterialShortageAlert.objects.filter(
        status='open'
    ).values(
        'component__part_number',
        'component__description',
        'component__category'
    ).annotate(
        total_required=Sum('required_quantity'),
        total_available=Sum('available_quantity'),
        shortage_count=Count('id')
    ).order_by('component__part_number')
    
    context = {
        'shortages': shortages,
        'component_shortages': component_shortages,
        'view_mode': request.GET.get('view', 'list')  # 'list' or 'summary'
    }
    return render(request, 'MaterialPlan/shortage_list.html', context)

@login_required
def shortage_detail(request, pk):
    shortage = get_object_or_404(MaterialShortageAlert, pk=pk)
    
    # Get inventory locations with this component
    inventory_items = Inventory.objects.filter(
        component=shortage.component
    ).select_related('location')
    
    # Get similar shortages for the same component
    related_shortages = MaterialShortageAlert.objects.filter(
        component=shortage.component,
        status='open'
    ).exclude(pk=pk).order_by('required_date')
    
    context = {
        'shortage': shortage,
        'inventory_items': inventory_items,
        'related_shortages': related_shortages,
    }
    return render(request, 'MaterialPlan/shortage_detail.html', context)


def confirm_plan(request, pk):
    plan = get_object_or_404(MaterialPlan, pk=pk)

    # Check permission
    if not request.user.has_perm('production.change_machineplan'):
        messages.error(request, "You don't have permission to update plans.")
        return redirect('plan_detail', pk=pk)

    try:
        if plan.status == 'draft':
            # ---- Confirm the plan ----
            plan.status = 'confirmed'
            plan.confirmed_by = request.user
            plan.confirmed_at = timezone.now()
            plan.save()

            ProductionOrder.objects.filter(
                id=plan.production_order_id,
                bom_id=plan.bom_id
            ).update(order_status=3)

            # (Optional: your inventory/reservation logic here)

            messages.success(request, "Material plan has been successfully confirmed!")

        elif plan.status == 'confirmed':
            # ---- Execute the plan ----
            plan.status = 'executed'
            plan.executed_by = request.user
            plan.executed_at = timezone.now()
            plan.save()

            # Update related Production Order status

            ProductionOrder.objects.filter(
                id=plan.production_order_id,
                bom_id=plan.bom_id
            ).update(order_status=3)

            messages.success(request, "Material plan has been executed and production order updated!")

        else:
            messages.error(request, f"Plan cannot be updated. Current status: {plan.get_status_display()}.")

    except Exception as e:
        messages.error(request, f"Error updating plan: {str(e)}")
    
    return redirect('plan_list')

def get_bom_for_production_order(request):
    production_order_id = request.GET.get('production_order_id')
    
    if not production_order_id:
        return JsonResponse({'error': 'Production order ID is required'}, status=400)
    
    try:
        # Get the production order
        production_order = ProductionOrder.objects.get(id=production_order_id)
        
        # Get the associated BOM
        bom = production_order.bom  # Assuming your model has a ForeignKey from ProductionOrder to BOM
        
        if bom:
            return JsonResponse({
                'bom_id': bom.id,
                'bom_name': str(bom)  # Or use the appropriate field for display
            })
        else:
            return JsonResponse({
                'bom_id': None,
                'bom_name': 'No BOM associated'
            })
            
    except ProductionOrder.DoesNotExist:
        return JsonResponse({'error': 'Production order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
