import traceback
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from decimal import Decimal
import json
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import *
from BOM.models import * 
from MaterialPlan.models import * 
from .forms import *
from django.core.paginator import Paginator
from django.db.models import Q
from weasyprint import HTML
import tempfile
from django.template.loader import render_to_string

from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.utils.timezone import now


@login_required
def dashboard(request):
    """Enhanced dashboard with more metrics"""
    # Sales metrics
    customer_count = Customer.objects.count()
    rfq_count = RFQ.objects.count()
    quotation_count = Quotation.objects.count()
    sales_order_count = SalesOrder.objects.count()
    invoice_count = Invoice.objects.count()
    
    # Purchase metrics
    supplier_count = Supplier.objects.count()
    purchase_rfq_count = PurchaseRFQ.objects.count()
    purchase_order_count = PurchaseOrder.objects.count()
    grn_count = GoodsReceivedNote.objects.count()
    supplier_invoice_count = SupplierInvoice.objects.count()
    
    # Financial metrics
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    # Sales revenue
    monthly_sales = Invoice.objects.filter(
        invoice_date__gte=month_start,
        status__in=['issued', 'partially_paid', 'paid']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # Outstanding invoices
    outstanding_invoices = Invoice.objects.filter(
        status__in=['issued', 'partially_paid'],
        due_date__lt=today
    ).aggregate(
        total=Sum(F('total_amount') - F('amount_paid'))
    )['total'] or Decimal('0.00')
    
    # Purchase costs
    monthly_purchases = SupplierInvoice.objects.filter(
        invoice_date__gte=month_start,
        status__in=['verified', 'paid']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # Recent activities
    recent_rfqs = RFQ.objects.all().order_by('-created_date')[:5]
    recent_quotations = Quotation.objects.all().order_by('-created_date')[:5]
    recent_orders = SalesOrder.objects.all().order_by('-created_date')[:5]
    recent_invoices = Invoice.objects.all().order_by('-created_date')[:5]
    recent_purchase_orders = PurchaseOrder.objects.all().order_by('-created_date')[:5]
    recent_grns = GoodsReceivedNote.objects.all().order_by('-created_date')[:5]
    
    # Alerts and notifications
    overdue_invoices = Invoice.objects.filter(
        due_date__lt=today,
        status__in=['issued', 'partially_paid']
    ).count()
    
    overdue_supplier_invoices = SupplierInvoice.objects.filter(
        due_date__lt=today,
        status__in=['received', 'verified']
    ).count()
    
    low_stock_items = Inventory.objects.filter(
        quantity_on_hand__lte=F('min_stock_level')
    ).count()
    
    pending_grns = GoodsReceivedNote.objects.filter(
        status='received'
    ).count()
    
    context = {
        # Counts
        'customer_count': customer_count,
        'rfq_count': rfq_count,
        'quotation_count': quotation_count,
        'sales_order_count': sales_order_count,
        'invoice_count': invoice_count,
        'supplier_count': supplier_count,
        'purchase_rfq_count': purchase_rfq_count,
        'purchase_order_count': purchase_order_count,
        'grn_count': grn_count,
        'supplier_invoice_count': supplier_invoice_count,
        
        # Financials
        'monthly_sales': monthly_sales,
        'outstanding_invoices': outstanding_invoices,
        'monthly_purchases': monthly_purchases,
        
        # Recent activities
        'recent_rfqs': recent_rfqs,
        'recent_quotations': recent_quotations,
        'recent_orders': recent_orders,
        'recent_invoices': recent_invoices,
        'recent_purchase_orders': recent_purchase_orders,
        'recent_grns': recent_grns,
        
        # Alerts
        'overdue_invoices': overdue_invoices,
        'overdue_supplier_invoices': overdue_supplier_invoices,
        'low_stock_items': low_stock_items,
        'pending_grns': pending_grns,
    }
    
    return render(request, 'sales/sp_dashboard.html', context)

# Sales Dashboard View
@login_required
def sales_dashboard(request):
    # Get counts for dashboard
    customer_count = Customer.objects.count()
    rfq_count = RFQ.objects.count()
    quotation_count = Quotation.objects.count()
    sales_order_count = SalesOrder.objects.count()
    invoice_count = Invoice.objects.count()
    
    # Get recent activities
    recent_rfqs = RFQ.objects.all().order_by('-created_date')[:5]
    recent_quotations = Quotation.objects.all().order_by('-created_date')[:5]
    recent_orders = SalesOrder.objects.all().order_by('-created_date')[:5]
    recent_invoices = Invoice.objects.all().order_by('-created_date')[:5]
    
    # Get sales metrics
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    monthly_sales = Invoice.objects.filter(
        invoice_date__gte=month_start,
        status__in=['issued', 'partially_paid', 'paid']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    outstanding_invoices = Invoice.objects.filter(
        status__in=['issued', 'partially_paid'],
        due_date__lt=today
    ).aggregate(
        total=Sum(F('total_amount') - F('amount_paid'))
    )['total'] or Decimal('0.00')
    
    context = {
        'customer_count': customer_count,
        'rfq_count': rfq_count,
        'quotation_count': quotation_count,
        'sales_order_count': sales_order_count,
        'invoice_count': invoice_count,
        'recent_rfqs': recent_rfqs,
        'recent_quotations': recent_quotations,
        'recent_orders': recent_orders,
        'recent_invoices': recent_invoices,
        'monthly_sales': monthly_sales,
        'outstanding_invoices': outstanding_invoices,
    }
    
    return render(request, 'sales/dashboard.html', context)

# Purchase Dashboard View
@login_required
def purchase_dashboard(request):
    # Get counts for dashboard
    supplier_count = Supplier.objects.count()
    purchase_rfq_count = PurchaseRFQ.objects.count()
    purchase_order_count = PurchaseOrder.objects.count()
    grn_count = GoodsReceivedNote.objects.count()
    supplier_invoice_count = SupplierInvoice.objects.count()
    
    # Get recent activities
    recent_purchase_rfqs = PurchaseRFQ.objects.all().order_by('-created_date')[:5]
    recent_purchase_orders = PurchaseOrder.objects.all().order_by('-created_date')[:5]
    recent_grns = GoodsReceivedNote.objects.all().order_by('-created_date')[:5]
    recent_supplier_invoices = SupplierInvoice.objects.all().order_by('-created_date')[:5]
    
    # Get purchase metrics
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    monthly_purchases = SupplierInvoice.objects.filter(
        invoice_date__gte=month_start,
        status__in=['verified', 'paid']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    pending_grns = GoodsReceivedNote.objects.filter(
        status='received'
    ).count()
    
    pending_po_receipts = PurchaseOrderItem.objects.annotate(
        pending_qty=F('quantity') - F('received_quantity')
    ).filter(pending_qty__gt=0).count()
    
    context = {
        'today': today,
        'supplier_count': supplier_count,
        'purchase_rfq_count': purchase_rfq_count,
        'purchase_order_count': purchase_order_count,
        'grn_count': grn_count,
        'supplier_invoice_count': supplier_invoice_count,
        'recent_purchase_rfqs': recent_purchase_rfqs,
        'recent_purchase_orders': recent_purchase_orders,
        'recent_grns': recent_grns,
        'recent_supplier_invoices': recent_supplier_invoices,
        'monthly_purchases': monthly_purchases,
        'pending_grns': pending_grns,
        'pending_po_receipts': pending_po_receipts,
    }
    
    return render(request, 'purchase/dashboard.html', context)

# Supplier Comparison View
@login_required
def supplier_comparison(request, rfq_id):
    rfq = get_object_or_404(PurchaseRFQ, pk=rfq_id)
    
    if not rfq.suppliers.exists():
        messages.error(request, 'No suppliers added to this RFQ.')
        return redirect('purchase_rfq_detail', pk=rfq_id)
    
    # Get all responses for this RFQ
    responses = SupplierResponse.objects.filter(
        rfq_supplier__rfq=rfq
    ).select_related('rfq_supplier__supplier', 'rfq_item__component')
    
    # Organize data for comparison
    comparison_data = {}
    for response in responses:
        component_id = response.rfq_item.component.component_id
        supplier_id = response.rfq_supplier.supplier.supplier_id
        
        if component_id not in comparison_data:
            comparison_data[component_id] = {
                'component': response.rfq_item.component,
                'quantity': response.rfq_item.quantity,
                'suppliers': {}
            }
        
        comparison_data[component_id]['suppliers'][supplier_id] = {
            'unit_price': response.unit_price,
            'lead_time_days': response.lead_time_days,
            'min_order_quantity': response.min_order_quantity,
            'validity_days': response.validity_days,
            'notes': response.notes,
            'supplier_name': response.rfq_supplier.supplier.name,
            'response_id': response.response_id
        }
    
    # Process award decisions if POST
    if request.method == 'POST':
        awarded_suppliers = {}
        
        for key, value in request.POST.items():
            if key.startswith('award_'):
                component_id = key.split('_')[1]  
                supplier_id = value
                
                if supplier_id not in awarded_suppliers:
                    awarded_suppliers[supplier_id] = []
                awarded_suppliers[supplier_id].append(component_id)
        
        # Update awarded status
        with transaction.atomic():
            for supplier in rfq.suppliers.all():
                if supplier.supplier_id in awarded_suppliers:
                    supplier.status = 'awarded'
                else:
                    supplier.status = 'responded'
                supplier.save()
        
        messages.success(request, 'Supplier awards updated successfully.')
        return redirect('purchase_rfq_detail', pk=rfq_id)
    
    return render(request, 'purchase/supplier_comparison.html', {
        'rfq': rfq,
        'comparison_data': comparison_data,
        'suppliers': rfq.suppliers.all()
    })


# Customer Views
@login_required
def customer_list(request):
    customers = Customer.objects.all()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        customers = customers.filter(
            Q(name__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(address__icontains=search_query)
        )
    
    # Filter by type
    customer_type = request.GET.get('type', '')
    if customer_type:
        customers = customers.filter(type=customer_type)
    
    paginator = Paginator(customers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'sales/customer_list.html', {
        'customers': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'search_query': search_query,
        'customer_type': customer_type
    })

@login_required
def customer_create(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.created_by = request.user
            customer.save()
            messages.success(request, 'Customer created successfully.')
            return redirect('customer_list')
    else:
        form = CustomerForm()
    return render(request, 'sales/customer_form.html', {'form': form, 'title': 'Create Customer'})

@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer updated successfully.')
            return redirect('customer_list')
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'sales/customer_form.html', {'form': form, 'title': 'Edit Customer'})

@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    return render(request, 'sales/customer_detail.html', {'customer': customer})

# Customer Pricing Views
@login_required
def customer_pricing_list(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)
    pricings = CustomerPricing.objects.filter(customer=customer).order_by('-effective_date')
    
    return render(request, 'sales/customer_pricing_list.html', {
        'customer': customer,
        'pricings': pricings
    })

@login_required
def customer_pricing_create(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)
    
    if request.method == 'POST':
        form = CustomerPricingForm(request.POST)
        if form.is_valid():
            pricing = form.save(commit=False)
            pricing.customer = customer
            pricing.created_by = request.user
            pricing.save()
            messages.success(request, 'Customer pricing created successfully.')
            return redirect('customer_pricing_list', customer_id=customer.customer_id)
    else:
        form = CustomerPricingForm(initial={'customer': customer})
    
    return render(request, 'sales/customer_pricing_form.html', {
        'form': form,
        'customer': customer,
        'title': 'Create Customer Pricing'
    })

@login_required
def customer_pricing_edit(request, pk):
    pricing = get_object_or_404(CustomerPricing, pk=pk)
    
    if request.method == 'POST':
        form = CustomerPricingForm(request.POST, instance=pricing)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer pricing updated successfully.')
            return redirect('customer_pricing_list', customer_id=pricing.customer.customer_id)
    else:
        form = CustomerPricingForm(instance=pricing)
    
    return render(request, 'sales/customer_pricing_form.html', {
        'form': form,
        'customer': pricing.customer,
        'title': 'Edit Customer Pricing'
    })

# RFQ Views
@login_required
def rfq_list(request):
    rfqs = RFQ.objects.all().select_related('customer', 'created_by')
    
    # Filter functionality
    status_filter = request.GET.get('status', '')
    customer_filter = request.GET.get('customer', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('search', '')
    
    if status_filter:
        rfqs = rfqs.filter(status=status_filter)
    
    if customer_filter:
        rfqs = rfqs.filter(customer_id=customer_filter)
    
    if date_from:
        rfqs = rfqs.filter(rfq_date__gte=date_from)
    
    if date_to:
        rfqs = rfqs.filter(rfq_date__lte=date_to)
    
    if search_query:
        rfqs = rfqs.filter(
            Q(rfq_number__icontains=search_query) |
            Q(customer__name__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    customers = Customer.objects.all()
    status_choices = RFQ.RFQ_STATUS
    
    paginator = Paginator(rfqs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'sales/rfq_list.html', {
        'rfqs': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'customers': customers,
        'status_choices': status_choices,
        'status_filter': status_filter,
        'customer_filter': customer_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query
    })

@login_required
def rfq_create(request):
    try:
        if request.method == 'POST':
            form = RFQForm(request.POST, request.FILES)
            formset = RFQItemFormSet(request.POST)
            
            if form.is_valid() and formset.is_valid():
                rfq = form.save(commit=False)
                rfq.created_by = request.user
                rfq.save()
                
                formset.instance = rfq
                formset.save()
                
                messages.success(request, 'RFQ created successfully.')
                return redirect('rfq_detail', pk=rfq.rfq_id)
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = RFQForm()
            formset = RFQItemFormSet()
        
        return render(request, 'sales/rfq_form.html', {
            'form': form, 
            'formset': formset,
            'title': 'Create RFQ'
        })
    
    except Exception as e:
        messages.error(request, f'Error creating RFQ: {str(e)}')
        return redirect('rfq_list')

@login_required
def rfq_edit(request, pk):
    rfq = get_object_or_404(RFQ, pk=pk)
    if request.method == 'POST':
        form = RFQForm(request.POST, request.FILES, instance=rfq)
        if form.is_valid():
            form.save()
            
            formset = RFQItemFormSet(request.POST, instance=rfq)
            if formset.is_valid():
                formset.save()
                messages.success(request, 'RFQ updated successfully.')
                return redirect('rfq_list')
        else:
            formset = RFQItemFormSet(request.POST, instance=rfq)
    else:
        form = RFQForm(instance=rfq)
        formset = RFQItemFormSet(instance=rfq)
    
    return render(request, 'sales/rfq_form.html', {
        'form': form, 
        'formset': formset,
        'title': 'Edit RFQ'
    })

@login_required
def rfq_detail(request, pk):
    rfq = get_object_or_404(RFQ, pk=pk)
    return render(request, 'sales/rfq_detail.html', {'rfq': rfq})

@login_required
def rfq_clone(request, pk):
    original_rfq = get_object_or_404(RFQ, pk=pk)
    
    if request.method == 'POST':
        form = RFQForm(request.POST, request.FILES)
        if form.is_valid():
            rfq = form.save(commit=False)
            rfq.created_by = request.user
            rfq.status = 'draft'
            rfq.save()
            
            # Clone RFQ items
            for item in original_rfq.items.all():
                RFQItem.objects.create(
                    rfq=rfq,
                    item_type=item.item_type,
                    component=item.component,
                    bom=item.bom,
                    quantity=item.quantity,
                    target_price=item.target_price,
                    specifications=item.specifications,
                    notes=item.notes
                )
            
            messages.success(request, 'RFQ cloned successfully.')
            return redirect('rfq_list')
    else:
        # Prepopulate form with original RFQ data
        form = RFQForm(instance=original_rfq)
        form.fields['rfq_date'].initial = timezone.now().date()
    
    return render(request, 'sales/rfq_form.html', {
        'form': form, 
        'formset': RFQItemFormSet(instance=original_rfq),
        'title': 'Clone RFQ'
    })

# Quotation Views
@login_required
def quotation_list(request):
    quotations = Quotation.objects.all().select_related('customer', 'created_by')
    
    # Filter functionality
    status_filter = request.GET.get('status', '')
    customer_filter = request.GET.get('customer', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if status_filter:
        quotations = quotations.filter(status=status_filter)
    
    if customer_filter:
        quotations = quotations.filter(customer_id=customer_filter)
    
    if date_from:
        quotations = quotations.filter(quotation_date__gte=date_from)
    
    if date_to:
        quotations = quotations.filter(quotation_date__lte=date_to)
    
    customers = Customer.objects.all()
    status_choices = Quotation.QUOTATION_STATUS
    
    paginator = Paginator(quotations, 10)  # Show 25 quotations per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'sales/quotation_list.html', {
        'quotations': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'customers': customers,
        'status_choices': status_choices
    })

@login_required
def quotation_create(request):
    try:
        # Get components and BOMs for the form
        components = Component.objects.all()
        boms = BOMHeader.objects.all()

        if request.method == 'POST':
            form = QuotationForm(request.POST)
            formset = QuotationItemFormSet(request.POST)
            
            if form.is_valid() and formset.is_valid():
                quotation = form.save(commit=False)
                quotation.created_by = request.user
                quotation.save()
                
                formset.instance = quotation
                formset.save()
                
                messages.success(request, 'Quotation created successfully.')
                return redirect('quotation_detail', pk=quotation.quotation_id)
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = QuotationForm()
            formset = QuotationItemFormSet()
        
        return render(request, 'sales/quotation_form.html', {
            'form': form, 
            'formset': formset,
            'components': components,
            'boms': boms,
            'title': 'Create Quotation'
        })
    
    except Exception as e:
        messages.error(request, f'Error creating quotation: {str(e)}')
        return redirect('quotation_list')

@login_required
def quotation_from_rfq(request, rfq_id):
    """Create quotation from RFQ with proper pricing calculation"""
    rfq = get_object_or_404(RFQ, pk=rfq_id)
    
    # Get components and BOMs for the form
    components = Component.objects.all()
    boms = BOMHeader.objects.all()
    
    
    if not rfq.can_create_quotation:
        messages.error(request, 'Cannot create quotation from this RFQ.')
        return redirect('rfq_detail', pk=rfq_id)
    
    if request.method == 'POST':
        form = QuotationForm(request.POST)
        
        if form.is_valid():
            quotation = form.save(commit=False)
            quotation.rfq = rfq
            quotation.customer = rfq.customer
            quotation.created_by = request.user
            
            # Calculate totals
            subtotal = Decimal('0.00')
            items_data = []
            
            for rfq_item in rfq.items.all():
                # Calculate price based on item type and customer pricing
                unit_price = Decimal('0.00')
                
                if rfq_item.item_type == 'part' and rfq_item.component:
                    # Get customer-specific pricing
                    try:
                        customer_pricing = CustomerPricing.objects.get(
                            customer=rfq.customer,
                            component=rfq_item.component,
                            effective_date__lte=timezone.now().date(),
                            expiry_date__gte=timezone.now().date()
                        )
                        unit_price = customer_pricing.price
                    except CustomerPricing.DoesNotExist:
                        # Get lowest supplier price with markup
                        supplier_price = ComponentSupplier.objects.filter(
                            component=rfq_item.component,
                            is_approved=True
                        ).order_by('cost').first()
                        
                        if supplier_price:
                            unit_price = supplier_price.cost * Decimal('1.2')  # 20% markup
                        else:
                            unit_price = Decimal('0.00')  # Default price
                
                elif rfq_item.item_type == 'product' and rfq_item.bom:
                    # Calculate price from BOM
                    bom_cost = calculate_bom_cost(rfq_item.bom.id)
                    unit_price = bom_cost * Decimal('1.3')  # 30% markup
                
                line_total = unit_price * rfq_item.quantity
                subtotal += line_total
                
                items_data.append({
                    'rfq_item': rfq_item,
                    'unit_price': unit_price,
                    'line_total': line_total
                })
            
            # Calculate taxes and totals
            tax_rate = Decimal('10.00')  # Default tax rate
            tax_amount = subtotal * (tax_rate / 100)
            total_amount = subtotal + tax_amount
            
            quotation.subtotal = subtotal
            quotation.tax_amount = tax_amount
            quotation.total_amount = total_amount
            quotation.save()
            
            # Create quotation items
            for item_data in items_data:
                rfq_item = item_data['rfq_item']
                
                QuotationItem.objects.create(
                    quotation=quotation,
                    rfq_item=rfq_item,
                    item_type=rfq_item.item_type,
                    component=rfq_item.component,
                    bom=rfq_item.bom,
                    description=rfq_item.component.description if rfq_item.component else rfq_item.bom.description,
                    quantity=rfq_item.quantity,
                    unit_price=item_data['unit_price'],
                    tax_rate=tax_rate,
                    line_total=item_data['line_total']
                )
            
            # Update RFQ status
            rfq.status = 'quoted'
            rfq.save()
            
            messages.success(request, 'Quotation created successfully.')
            return redirect('quotation_detail', pk=quotation.quotation_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = QuotationForm(initial={
            'customer': rfq.customer,
            'quotation_date': timezone.now().date(),
            'expiry_date': timezone.now().date() + timezone.timedelta(days=30),
            'currency': rfq.currency,
            'payment_terms': rfq.customer.payment_terms,
        })
        formset = QuotationItemFormSet()
    
    return render(request, 'sales/quotation_form.html', {
        'form': form,
        'formset': formset,
        'rfq': rfq,
        'components': components,
        'boms': boms,
        'title': 'Create Quotation from RFQ'
    })

@login_required
def quotation_edit(request, pk):
    quotation = get_object_or_404(Quotation, pk=pk)
     # Get components and BOMs for the form
    components = Component.objects.all()
    boms = BOMHeader.objects.all()

    if request.method == 'POST':
        form = QuotationForm(request.POST, instance=quotation)
        if form.is_valid():
            form.save()
            
            formset = QuotationItemFormSet(request.POST, instance=quotation)
            if formset.is_valid():
                formset.save()
                messages.success(request, 'Quotation updated successfully.')
                return redirect('quotation_list')
        else:
            formset = QuotationItemFormSet(request.POST, instance=quotation)
    else:
        form = QuotationForm(instance=quotation)
        formset = QuotationItemFormSet(instance=quotation)
    
    return render(request, 'sales/quotation_form.html', {
        'form': form, 
        'formset': formset,
        'quotation': quotation,
        'components': components,
        'boms': boms,
        'title': 'Edit Quotation'
    })

@login_required
def quotation_detail(request, pk):
    quotation = get_object_or_404(Quotation, pk=pk)
    return render(request, 'sales/quotation_detail.html', {'quotation': quotation})

@login_required
def quotation_pdf(request, pk):
    quotation = get_object_or_404(Quotation, pk=pk)
    
    try:
        # Render HTML template
        html_string = render_to_string('sales/quotation_pdf.html', {'quotation': quotation})
        html = HTML(string=html_string)
        
        # Generate PDF
        result = html.write_pdf()
        
        # Create HTTP response with PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="quotation_{quotation.quotation_number}.pdf"'
        response.write(result)
        
        return response
    
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('quotation_detail', pk=quotation.quotation_id)

# Variant BOM functionality
@login_required
def bom_clone(request, bom_id):
    original_bom = get_object_or_404(BOMHeader, pk=bom_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        if not name:
            messages.error(request, 'BOM name is required.')
            return redirect('bom_clone', bom_id=bom_id)
        
        # Check if BOM with this name already exists
        if BOMHeader.objects.filter(name=name).exists():
            messages.error(request, 'A BOM with this name already exists.')
            return redirect('bom_clone', bom_id=bom_id)
        
        # Clone the BOM
        with transaction.atomic():
            new_bom = BOMHeader.objects.create(
                name=name,
                description=description or original_bom.description,
                revision=1,
                status='draft',
                created_by=request.user,
                parent_bom_id=original_bom.id
            )
            
            # Clone BOM items
            for item in original_bom.items.all():
                BOMItem.objects.create(
                    bom=new_bom,
                    component=item.component,
                    quantity=item.quantity,
                    reference_designators=item.reference_designators,
                    notes=item.notes,
                    sort_order=item.sort_order,
                    level=item.level,
                    position=item.position
                )
        
        messages.success(request, f'BOM {original_bom.name} cloned as {new_bom.name}.')
        return redirect('bom_detail', pk=new_bom.id)
    
    return render(request, 'sales/bom_clone.html', {'bom': original_bom})

# # Quotation with Variant BOM
# @login_required
# def quotation_with_variant_bom(request, rfq_id):
#     rfq = get_object_or_404(RFQ, pk=rfq_id)
    
#     if request.method == 'POST':
#         # Handle variant BOM creation and quotation
#         bom_id = request.POST.get('bom_id')
#         new_bom_name = request.POST.get('new_bom_name')
#         new_bom_description = request.POST.get('new_bom_description')
        
#         if not bom_id:
#             messages.error(request, 'Please select a BOM to clone.')
#             return redirect('quotation_with_variant_bom', rfq_id=rfq_id)
        
#         original_bom = get_object_or_404(BOMHeader, pk=bom_id)
        
#         # Create variant BOM
#         variant_bom = BOMHeader.objects.create(
#             name=new_bom_name,
#             description=new_bom_description or original_bom.description,
#             revision=1,
#             status='draft',
#             created_by=request.user,
#             parent_bom_id=original_bom.id
#         )
        
#         # Clone BOM items
#         for item in original_bom.items.all():
#             BOMItem.objects.create(
#                 bom=variant_bom,
#                 component=item.component,
#                 quantity=item.quantity,
#                 reference_designators=item.reference_designators,
#                 notes=item.notes,
#                 sort_order=item.sort_order,
#                 level=item.level,
#                 position=item.position
#             )
        
#         # Create quotation
#         quotation = Quotation.objects.create(
#             customer=rfq.customer,
#             rfq=rfq,
#             quotation_date=timezone.now().date(),
#             expiry_date=timezone.now().date() + timezone.timedelta(days=30),
#             currency=rfq.currency,
#             status='draft',
#             payment_terms=rfq.customer.payment_terms,
#             created_by=request.user
#         )
        
#         # Create quotation item for the variant BOM
#         # Calculate price based on BOM cost
#         bom_cost = calculate_bom_cost(variant_bom.id)
#         unit_price = bom_cost * Decimal('1.3')  # 30% markup
        
#         QuotationItem.objects.create(
#             quotation=quotation,
#             item_type='product',
#             bom=variant_bom,
#             description=variant_bom.description,
#             quantity=1,  # Default quantity, can be adjusted
#             unit_price=unit_price,
#             tax_rate=Decimal('10.00')  # Default tax rate
#         )
        
#         messages.success(request, f'Variant BOM created and quotation generated successfully.')
#         return redirect('quotation_detail', pk=quotation.quotation_id)
    
#     # Get all BOMs for selection
#     boms = BOMHeader.objects.filter(status='approved')
    
#     return render(request, 'sales/quotation_with_variant_bom.html', {
#         'rfq': rfq,
#         'boms': boms
#     })


# Quotation with Variant BOM

# views.py
from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.exceptions import ValidationError

@login_required
def quotation_with_variant_bom(request, rfq_id):
    rfq = get_object_or_404(RFQ, pk=rfq_id)

    if request.method == 'POST':
        try:
            # Handle variant BOM creation and quotation
            bom_id = request.POST.get('bom_id')
            new_bom_name = request.POST.get('new_bom_name')
            new_bom_description = request.POST.get('new_bom_description')

            if not bom_id:
                messages.error(request, 'Please select a BOM to clone.')
                return redirect('quotation_with_variant_bom', rfq_id=rfq_id)

            if not new_bom_name:
                messages.error(request, 'Variant BOM name is required.')
                return redirect('quotation_with_variant_bom', rfq_id=rfq_id)

            original_bom = get_object_or_404(BOMHeader, pk=bom_id)

            # Create variant BOM
            variant_bom = BOMHeader.objects.create(
                name=new_bom_name,
                description=new_bom_description or original_bom.description,
                revision=1,
                status='draft',
                created_by=request.user,
                parent_bom=original_bom
            )

            # Clone BOM items with pricing from ComponentSupplier
            for item in original_bom.items.all():
                max_price = get_component_max_price(item.component)  # external function

                BOMItem.objects.create(
                    bom=variant_bom,
                    component=item.component,
                    supplier=item.supplier,
                    price=max_price,
                    cost=max_price,  # Using price as cost for simplicity
                    quantity=item.quantity,
                    reference_designators=item.reference_designators,
                    notes=item.notes,
                    sort_order=item.sort_order,
                    level=item.level,
                    position=item.position
                )

            # Create quotation
            quotation = Quotation.objects.create(
                customer=rfq.customer,
                rfq=rfq,
                quotation_date=timezone.now().date(),
                expiry_date=timezone.now().date() + timezone.timedelta(days=30),
                currency=rfq.currency,
                status='draft',
                payment_terms=rfq.customer.payment_terms,
                created_by=request.user
            )

            # Create quotation item for the variant BOM
            bom_cost = calculate_bom_cost_vbom(variant_bom.id)  # external function
            markup_percentage = Decimal('30.0')  # 30% markup
            unit_price = bom_cost * (1 + markup_percentage / 100)

            QuotationItem.objects.create(
                quotation=quotation,
                item_type='product',
                bom=variant_bom,
                description=variant_bom.description,
                quantity=1,  # Default quantity
                unit_price=unit_price,
                tax_rate=Decimal('10.00')  # Default tax rate
            )

            messages.success(request, f'Variant BOM created and quotation generated successfully.')
            return redirect('quotation_detail', pk=quotation.quotation_id)

        except Exception as e:
            logger.exception("Error while creating variant BOM and quotation")
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('quotation_with_variant_bom', rfq_id=rfq_id)

    # Get all BOMs for selection
    boms = BOMHeader.objects.filter(status='approved')

    return render(request, 'sales/quotation_with_variant_bom.html', {
        'rfq': rfq,
        'boms': boms
    })

def get_component_max_price(component):
    """Get the maximum price from approved suppliers for a component"""
    approved_suppliers = component.suppliers.filter(is_approved=True)
    if approved_suppliers.exists():
        return approved_suppliers.order_by('-cost').first().cost
    return Decimal('0.00')

def calculate_bom_cost_vbom(bom_id):
    """Calculate the total cost of a BOM"""
    bom = get_object_or_404(BOMHeader, pk=bom_id)
    total_cost = Decimal('0.00')
    
    for item in bom.items.all():
        if item.cost:
            total_cost += item.quantity * item.cost
        else:
            # Fallback to component supplier pricing
            max_price = get_component_max_price(item.component)
            total_cost += item.quantity * max_price
    
    return total_cost


def bom_details_api(request, bom_id):
    try:
        bom = BOMHeader.objects.get(pk=bom_id)
        items_data = []
        
        for item in bom.items.all():
            # Get max price from approved suppliers
            max_price = get_component_max_price(item.component)
            
            items_data.append({
                'part_number': item.component.part_number,
                'description': item.component.description,
                'category': item.component.category,
                'quantity': float(item.quantity),
                'unit_of_measure': item.component.unit_of_measure,
                'max_price': float(max_price)
            })
        
        return JsonResponse({
            'success': True,
            'bom': {
                'name': bom.name,
                'description': bom.description,
                'revision': bom.revision,
                'status': bom.status
            },
            'items': items_data
        })
    except BOMHeader.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'BOM not found'})
    
# Sales Order Views
@login_required
def sales_order_list(request):
    orders = SalesOrder.objects.all().select_related('customer', 'created_by')
    
    # Filter functionality
    status_filter = request.GET.get('status', '')
    customer_filter = request.GET.get('customer', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    if customer_filter:
        orders = orders.filter(customer_id=customer_filter)
    
    if date_from:
        orders = orders.filter(order_date__gte=date_from)
    
    if date_to:
        orders = orders.filter(order_date__lte=date_to)
    
    customers = Customer.objects.all()
    status_choices = SalesOrder.ORDER_STATUS
    
    paginator = Paginator(orders, 10)  # Show 25 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'sales/sales_order_list.html', {
        'orders': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'customers': customers,
        'status_choices': status_choices
    })

@login_required
def sales_order_create(request):
    if request.method == 'POST':
        form = SalesOrderForm(request.POST, request.FILES)
        if form.is_valid():
            order = form.save(commit=False)
            order.created_by = request.user
            order.save()
            
            # Handle order items
            formset = SalesOrderItemFormSet(request.POST, instance=order)
            if formset.is_valid():
                formset.save()
                messages.success(request, 'Sales Order created successfully.')
                return redirect('sales_order_list')
        else:
            formset = SalesOrderItemFormSet(request.POST)
    else:
        form = SalesOrderForm()
        formset = SalesOrderItemFormSet()
    
     # Get components and BOMs for the template
    components = Component.objects.all()
    boms = BOMHeader.objects.all()

    return render(request, 'sales/sales_order_form.html', {
        'form': form, 
        'formset': formset,
        'components': components,
        'boms': boms,
        'title': 'Create Sales Order'
    })

@login_required
def sales_order_from_quotation(request, quotation_id):
    """Create sales order from quotation"""
    quotation = get_object_or_404(Quotation, pk=quotation_id)
    
    if not quotation.can_create_order:
        messages.error(request, 'Cannot create sales order from this quotation.')
        return redirect('quotation_detail', pk=quotation_id)
    
    if request.method == 'POST':
        form = SalesOrderForm(request.POST, request.FILES)
        
        if form.is_valid():
            order = form.save(commit=False)
            order.quotation = quotation
            order.customer = quotation.customer
            order.currency = quotation.currency
            order.payment_terms = quotation.payment_terms
            order.created_by = request.user
            
            # Copy totals from quotation
            order.subtotal = quotation.subtotal
            order.tax_amount = quotation.tax_amount
            order.total_amount = quotation.total_amount
            order.save()
            
            # Create order items from quotation items
            for quotation_item in quotation.items.all():
                SalesOrderItem.objects.create(
                    sales_order=order,
                    quotation_item=quotation_item,
                    item_type=quotation_item.item_type,
                    component=quotation_item.component,
                    bom=quotation_item.bom,
                    description=quotation_item.description,
                    quantity=quotation_item.quantity,
                    unit_price=quotation_item.unit_price,
                    tax_rate=quotation_item.tax_rate,
                    line_total=quotation_item.line_total
                )
            
            # Update quotation status
            quotation.status = 'accepted'
            quotation.save()
            
            messages.success(request, 'Sales Order created successfully.')
            return redirect('sales_order_detail', pk=order.order_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SalesOrderForm(initial={
            'quotation': quotation,
            'customer': quotation.customer,
            'order_date': timezone.now().date(),
            'delivery_date': quotation.expiry_date,
            'currency': quotation.currency,
            'payment_terms': quotation.payment_terms,
        })
        
    # Get components and BOMs for the template
    components = Component.objects.all()
    boms = BOMHeader.objects.all()
    formset = SalesOrderItemFormSet()
    return render(request, 'sales/sales_order_form.html', {
        'form': form,
        'formset': formset,
        'quotation': quotation,
        'components': components,
        'boms': boms,
        'title': 'Create Sales Order from Quotation'
    })

@login_required
def sales_order_edit(request, pk):
    order = get_object_or_404(SalesOrder, pk=pk)
    if request.method == 'POST':
        form = SalesOrderForm(request.POST, request.FILES, instance=order)
        if form.is_valid():
            form.save()
            
            formset = SalesOrderItemFormSet(request.POST, instance=order)
            if formset.is_valid():
                formset.save()
                messages.success(request, 'Sales Order updated successfully.')
                return redirect('sales_order_list')
        else:
            formset = SalesOrderItemFormSet(request.POST, instance=order)
    else:
        form = SalesOrderForm(instance=order)
        formset = SalesOrderItemFormSet(instance=order)
    
    # Get components and BOMs for the template
    components = Component.objects.all()
    boms = BOMHeader.objects.all()

    return render(request, 'sales/sales_order_form.html', {
        'form': form, 
        'formset': formset,
        'components': components,
        'boms': boms,
        'title': 'Edit Sales Order'
    })

@login_required
def sales_order_detail(request, pk):
    order = get_object_or_404(SalesOrder, pk=pk)
    return render(request, 'sales/sales_order_detail.html', {'order': order})

# Invoice Views
@login_required
def invoice_list(request):
    invoices = Invoice.objects.all().select_related('sales_order', 'created_by')
    
    # Filter functionality
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if status_filter:
        invoices = invoices.filter(status=status_filter)
    
    if date_from:
        invoices = invoices.filter(invoice_date__gte=date_from)
    
    if date_to:
        invoices = invoices.filter(invoice_date__lte=date_to)
    
    status_choices = Invoice.INVOICE_STATUS
    
    paginator = Paginator(invoices, 10)  # Show 25 invoices per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'sales/invoice_list.html', {
        'invoices': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'status_choices': status_choices
    })

@login_required
def invoice_create(request):
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        item_formset = InvoiceItemFormSet(request.POST, instance=None)
        
        if form.is_valid() and item_formset.is_valid():
            invoice = form.save(commit=False)
            invoice.created_by = request.user
            invoice.save()
            
            # Save the formset
            item_formset.instance = invoice
            item_formset.save()
            
            messages.success(request, 'Invoice created successfully.')
            return redirect('invoice_list')
    else:
        form = InvoiceForm()
        item_formset = InvoiceItemFormSet(instance=None)
    
    return render(request, 'sales/invoice_form.html', {
        'form': form, 
        'item_formset': item_formset,
        'title': 'Create Invoice'
    })

@login_required
def invoice_from_sales_order(request, order_id):
    """Create invoice from sales order"""
    order = get_object_or_404(SalesOrder, pk=order_id)
    
    if order.status not in ['confirmed', 'in_progress', 'shipped', 'delivered']:
        messages.error(request, 'Cannot create invoice from this sales order.')
        return redirect('sales_order_detail', pk=order_id)
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        item_formset = InvoiceItemFormSet(request.POST, instance=None)
        
        if form.is_valid() and item_formset.is_valid():
            invoice = form.save(commit=False)
            invoice.sales_order = order
            invoice.created_by = request.user
            invoice.save()
            
            # Save the formset
            item_formset.instance = invoice
            item_formset.save()
            
            # Recalculate totals based on items
            invoice.subtotal = sum(item.quantity * item.unit_price for item in invoice.items.all())
            invoice.tax_amount = sum(item.quantity * item.unit_price * item.tax_rate / 100 for item in invoice.items.all())
            invoice.total_amount = invoice.subtotal + invoice.tax_amount
            invoice.save()
            
            messages.success(request, 'Invoice created successfully.')
            return redirect('invoice_detail', pk=invoice.invoice_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = InvoiceForm(initial={
            'sales_order': order,
            'invoice_date': timezone.now().date(),
            'due_date': timezone.now().date() + timezone.timedelta(days=30),
        })
        
        # Prepopulate the formset with order items
        initial_data = []
        for order_item in order.items.all():
            # Check if component exists before accessing it
            component_value = order_item.component_id if order_item.component_id else None
            bom_value = order_item.bom_id if order_item.bom_id else None
            initial_data.append({
                'sales_order_item': order_item,
                'item_type': order_item.item_type,
                'component': component_value,
                'bom': bom_value,
                'description': order_item.description,
                'quantity': order_item.quantity,
                'unit_price': order_item.unit_price,
                'tax_rate': order_item.tax_rate,
                'line_total': order_item.line_total,
            })
        
        item_formset = InvoiceItemFormSet(initial=initial_data, instance=None)
    
    return render(request, 'sales/invoice_form.html', {
        'form': form,
        'item_formset': item_formset,
        'order': order,
        'title': 'Create Invoice from Sales Order'
    })

@login_required
def invoice_edit(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        item_formset = InvoiceItemFormSet(request.POST, instance=invoice)
        
        if form.is_valid() and item_formset.is_valid():
            form.save()
            item_formset.save()
            
            # Recalculate totals based on items
            invoice.subtotal = sum(item.quantity * item.unit_price for item in invoice.items.all())
            invoice.tax_amount = sum(item.quantity * item.unit_price * item.tax_rate / 100 for item in invoice.items.all())
            invoice.total_amount = invoice.subtotal + invoice.tax_amount
            invoice.save()
            
            messages.success(request, 'Invoice updated successfully.')
            return redirect('invoice_list')
    else:
        form = InvoiceForm(instance=invoice)
        item_formset = InvoiceItemFormSet(instance=invoice)
    
    return render(request, 'sales/invoice_form.html', {
        'form': form, 
        'item_formset': item_formset,
        'invoice': invoice,
        'title': 'Edit Invoice'
    })

@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    return render(request, 'sales/invoice_detail.html', {'invoice': invoice})

@login_required
def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    
    try:
        # Render HTML template
        html_string = render_to_string('sales/invoice_pdf.html', {'invoice': invoice})
        html = HTML(string=html_string)
        
        # Generate PDF
        result = html.write_pdf()
        
        # Create HTTP response with PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
        response.write(result)
        
        return response
    
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('invoice_detail', pk=invoice.invoice_id)

# Purchase RFQ Views
@login_required
def purchase_rfq_list(request):
    rfqs = PurchaseRFQ.objects.all().select_related('created_by')
    
    # Filter functionality
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if status_filter:
        rfqs = rfqs.filter(status=status_filter)
    
    if date_from:
        rfqs = rfqs.filter(created_date__date__gte=date_from)
    
    if date_to:
        rfqs = rfqs.filter(created_date__date__lte=date_to)
    
    status_choices = PurchaseRFQ.RFQ_STATUS
    
    paginator = Paginator(rfqs, 10)  # Show 25 RFQs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'purchase/purchase_rfq_list.html', {
        'rfqs': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'status_choices': status_choices
    })

@login_required
def purchase_rfq_create(request):
    if request.method == 'POST':
        form = PurchaseRFQForm(request.POST)
        formset = PurchaseRFQItemFormSet(request.POST)
        supplier_formset = PurchaseRFQSupplierFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid() and supplier_formset.is_valid():
            rfq = form.save(commit=False)
            rfq.created_by = request.user
            rfq.save()
            
            formset.instance = rfq
            formset.save()
            
            supplier_formset.instance = rfq
            supplier_formset.save()
            
            messages.success(request, 'Purchase RFQ created successfully.')
            return redirect('purchase_rfq_list')
    else:
        form = PurchaseRFQForm()
        formset = PurchaseRFQItemFormSet()
        supplier_formset = PurchaseRFQSupplierFormSet()
    
    return render(request, 'purchase/purchase_rfq_form.html', {
        'form': form, 
        'formset': formset,
        'supplier_formset': supplier_formset,
        'title': 'Create Purchase RFQ'
    })

@login_required
def purchase_rfq_from_requisition(request, requisition_id):
    requisition = get_object_or_404(PurchaseRequisition, pk=requisition_id)
    
    if request.method == 'POST':
        form = PurchaseRFQForm(request.POST)
        formset = PurchaseRFQItemFormSet(request.POST)
        supplier_formset = PurchaseRFQSupplierFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid() and supplier_formset.is_valid():
            rfq = form.save(commit=False)
            rfq.requisition = requisition
            rfq.created_by = request.user
            rfq.save()
            
            formset.instance = rfq
            formset.save()
            
            supplier_formset.instance = rfq
            supplier_formset.save()
            
            messages.success(request, 'Purchase RFQ created from Requisition successfully.')
            return redirect('purchase_rfq_detail', pk=rfq.pk)
    else:
        form = PurchaseRFQForm(initial={
            'requisition': requisition,
            'title': f"RFQ for Requisition {requisition.id}",
        })
        
        # Prepopulate items from requisition
        formset = PurchaseRFQItemFormSet(initial=[
            {
                'component': req.component,
                'quantity': req.quantity,
                'required_date': req.required_by_date,
            }
            for req in requisition.plan.purchase_requisitions.all()
        ])

        
        supplier_formset = PurchaseRFQSupplierFormSet()
    
    return render(request, 'purchase/purchase_rfq_form.html', {
        'form': form, 
        'formset': formset,
        'supplier_formset': supplier_formset,
        'requisition': requisition,
        'title': 'Create Purchase RFQ from Requisition'
    })

@login_required
def purchase_rfq_edit(request, pk):
    rfq = get_object_or_404(PurchaseRFQ, pk=pk)
    if request.method == 'POST':
        form = PurchaseRFQForm(request.POST, instance=rfq)
        formset = PurchaseRFQItemFormSet(request.POST, instance=rfq)
        supplier_formset = PurchaseRFQSupplierFormSet(request.POST, instance=rfq)
        
        if form.is_valid() and formset.is_valid() and supplier_formset.is_valid():
            form.save()
            formset.save()
            supplier_formset.save()
            messages.success(request, 'Purchase RFQ updated successfully.')
            return redirect('purchase_rfq_list')
    else:
        form = PurchaseRFQForm(instance=rfq)
        formset = PurchaseRFQItemFormSet(instance=rfq)
        supplier_formset = PurchaseRFQSupplierFormSet(instance=rfq)
    
    return render(request, 'purchase/purchase_rfq_form.html', {
        'form': form, 
        'formset': formset,
        'supplier_formset': supplier_formset,
        'title': 'Edit Purchase RFQ'
    })

@login_required
def purchase_rfq_detail(request, pk):
    rfq = get_object_or_404(PurchaseRFQ, pk=pk)
    return render(request, 'purchase/purchase_rfq_detail.html', {'rfq': rfq})

@login_required
def purchase_rfq_send(request, pk):
    rfq = get_object_or_404(PurchaseRFQ, pk=pk)
    
    if request.method == 'POST':
        # Update status and sent date for all suppliers
        for supplier in rfq.suppliers.all():
            supplier.sent_date = timezone.now()
            supplier.status = 'sent'
            supplier.save()
        
        rfq.status = 'sent'
        rfq.save()
        
        # Here you would typically send emails to suppliers
        # For now, we'll just update the status
        
        messages.success(request, 'Purchase RFQ sent to suppliers.')
        return redirect('purchase_rfq_detail', pk=rfq.pk)
    
    return render(request, 'purchase/purchase_rfq_send.html', {'rfq': rfq})


@login_required
def purchase_quotation_list(request):
    quotations = PurchaseQuotation.objects.all().order_by('-created_date')
    
    # Filtering
    status_filter = request.GET.get('status')
    if status_filter:
        quotations = quotations.filter(status=status_filter)
    
    supplier_filter = request.GET.get('supplier')
    if supplier_filter:
        quotations = quotations.filter(supplier_id=supplier_filter)
    
    context = {
        'quotations': quotations,
        'status_choices': PurchaseQuotation.QUOTATION_STATUS,
        'suppliers': Supplier.objects.all(),
    }
    return render(request, 'purchase/purchase_quotation_list.html', context)

@login_required
def purchase_quotation_create(request):
    if request.method == 'POST':
        form = PurchaseQuotationForm(request.POST)
        formset = PurchaseQuotationItemFormSet(request.POST, instance=PurchaseQuotation())
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                quotation = form.save(commit=False)
                quotation.created_by = request.user
                quotation.save()
                
                formset.instance = quotation
                formset.save()
                
            messages.success(request, 'Purchase quotation created successfully!')
            return redirect('purchase_quotation_detail', pk=quotation.pk)
    else:
        form = PurchaseQuotationForm()
        formset = PurchaseQuotationItemFormSet(instance=PurchaseQuotation())
    
    context = {
        'form': form,
        'formset': formset,
        'title': 'Create Purchase Quotation',
    }
    return render(request, 'purchase/purchase_quotation_form.html', context)

@login_required
def purchase_quotation_from_rfq(request, rfq_id):
    rfq = get_object_or_404(PurchaseRFQ, pk=rfq_id)
    
    if request.method == 'POST':
        form = PurchaseQuotationForm(request.POST)
        formset = PurchaseQuotationItemFormSet(request.POST, instance=PurchaseQuotation())
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                quotation = form.save(commit=False)
                quotation.created_by = request.user
                quotation.purchase_rfq = rfq
                quotation.save()
                
                formset.instance = quotation
                formset.save()
                
            messages.success(request, 'Purchase quotation created successfully!')
            return redirect('purchase_quotation_detail', pk=quotation.pk)
    else:
        # Pre-fill form with RFQ data
        form = PurchaseQuotationForm(initial={
            'supplier': rfq.supplier,
            'currency': rfq.currency,
            'payment_terms': rfq.payment_terms,
        })
        
        # Create formset with RFQ items
        quotation = PurchaseQuotation()
        formset = PurchaseQuotationItemFormSet(instance=quotation)
        
        # Pre-fill formset data
        for i, item in enumerate(rfq.items.all()):
            if i < formset.total_form_count():
                formset.forms[i].initial = {
                    'rfq_item': item,
                    'component': item.component,
                    'description': item.component.description,
                    'quantity': item.quantity,
                }
    
    context = {
        'form': form,
        'formset': formset,
        'rfq': rfq,
        'title': f'Create Quotation from RFQ #{rfq.rfq_number}',
    }
    return render(request, 'purchase/purchase_quotation_form.html', context)

@login_required
def purchase_quotation_edit(request, pk):
    quotation = get_object_or_404(PurchaseQuotation, pk=pk)
    
    if request.method == 'POST':
        form = PurchaseQuotationForm(request.POST, instance=quotation)
        formset = PurchaseQuotationItemFormSet(request.POST, instance=quotation)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
                
            messages.success(request, 'Purchase quotation updated successfully!')
            return redirect('purchase_quotation_detail', pk=quotation.pk)
    else:
        form = PurchaseQuotationForm(instance=quotation)
        formset = PurchaseQuotationItemFormSet(instance=quotation)
    
    context = {
        'form': form,
        'formset': formset,
        'quotation': quotation,
        'title': f'Edit Purchase Quotation #{quotation.quotation_number}',
    }
    return render(request, 'purchase/purchase_quotation_form.html', context)

@login_required
def purchase_quotation_detail(request, pk):
    quotation = get_object_or_404(PurchaseQuotation, pk=pk)
    context = {
        'quotation': quotation,
    }
    return render(request, 'purchase/purchase_quotation_detail.html', context)

from weasyprint import HTML, CSS

@login_required
def purchase_quotation_pdf(request, pk):
    quotation = get_object_or_404(PurchaseQuotation, pk=pk)
    
    try:
        # Render HTML template
        html_string = render_to_string('purchase/purchase_quotation_pdf.html', {
            'quotation': quotation,
            'base_url': request.build_absolute_uri('/')[:-1]  # For loading static files
        })
        
        # Generate PDF using WeasyPrint
        html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
        
        # Add CSS for better PDF styling
        css = CSS(string='''
            @page {
                size: A4;
                margin: 1cm;
                @top-right {
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 10pt;
                }
            }
            body {
                font-family: Arial, sans-serif;
                font-size: 10pt;
            }
            .header {
                border-bottom: 2px solid #333;
                margin-bottom: 20px;
                padding-bottom: 10px;
            }
            .company-info {
                float: left;
                width: 40%;
            }
            .quotation-info {
                float: right;
                width: 40%;
                text-align: right;
            }
            .clear {
                clear: both;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #f5f5f5;
                font-weight: bold;
            }
            .text-right {
                text-align: right;
            }
            .total-row {
                font-weight: bold;
                background-color: #f9f9f9;
            }
            .footer {
                margin-top: 30px;
                padding-top: 10px;
                border-top: 1px solid #ddd;
                font-size: 9pt;
            }
        ''')
        
        # Generate PDF
        pdf_file = html.write_pdf(stylesheets=[css])
        
        # Create HTTP response with PDF
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="purchase_quotation_{quotation.quotation_number}.pdf"'
        
        return response
    
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('purchase_quotation_detail', pk=quotation.quotation_id)

@login_required
def update_quotation_status(request, pk, status):
    quotation = get_object_or_404(PurchaseQuotation, pk=pk)
    
    if status in dict(PurchaseQuotation.QUOTATION_STATUS).keys():
        quotation.status = status
        quotation.save()
        messages.success(request, f'Quotation status updated to {status}.')
    else:
        messages.error(request, 'Invalid status.')
    
    return redirect('purchase_quotation_detail', pk=quotation.pk)

# Purchase Order Views
@login_required
def purchase_order_list(request):
    orders = PurchaseOrder.objects.all().select_related('supplier', 'created_by')
    
    # Filter functionality
    status_filter = request.GET.get('status', '')
    supplier_filter = request.GET.get('supplier', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    if supplier_filter:
        orders = orders.filter(supplier_id=supplier_filter)
    
    if date_from:
        orders = orders.filter(order_date__gte=date_from)
    
    if date_to:
        orders = orders.filter(order_date__lte=date_to)
    
    suppliers = Supplier.objects.all()
    status_choices = PurchaseOrder.PO_STATUS
    
    paginator = Paginator(orders, 10)  # Show 25 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'purchase/purchase_order_list.html', {
        'orders': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'suppliers': suppliers,
        'status_choices': status_choices
    })

@login_required
def purchase_order_create(request):
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseOrderItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            order = form.save(commit=False)
            order.created_by = request.user
            order.save()
            
            formset.instance = order
            formset.save()
            
            messages.success(request, 'Purchase Order created successfully.')
            return redirect('purchase_order_list')
    else:
        form = PurchaseOrderForm()
        formset = PurchaseOrderItemFormSet()
    
    return render(request, 'purchase/purchase_order_form.html', {
        'form': form, 
        'formset': formset,
        'title': 'Create Purchase Order'
    })

@login_required
def purchase_order_from_rfq(request, rfq_id):
    rfq = get_object_or_404(PurchaseRFQ, pk=rfq_id)
    
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseOrderItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            order = form.save(commit=False)
            order.rfq = rfq
            order.created_by = request.user
            order.save()
            
            formset.instance = order
            formset.save()
            
            messages.success(request, 'Purchase Order created from RFQ successfully.')
            return redirect('purchase_order_detail', pk=order.pk)
    else:
        # Get the awarded supplier (simplified logic)
        awarded_supplier = None
        for supplier in rfq.suppliers.all():
            if supplier.status == 'awarded':
                awarded_supplier = supplier.supplier
                break
        
        if not awarded_supplier:
            # If no awarded supplier, use the first one
            if rfq.suppliers.exists():
                awarded_supplier = rfq.suppliers.first().supplier
        
        form = PurchaseOrderForm(initial={
            'rfq': rfq,
            'supplier': awarded_supplier,
            'order_date': timezone.now().date(),
            'expected_delivery_date': timezone.now().date() + timezone.timedelta(days=30),
        })
        
        # Prepopulate items from RFQ
        formset = PurchaseOrderItemFormSet(initial=[
            {
                'component': item.component_id,
                'quantity': item.quantity,
            }
            for item in rfq.items.all()
        ])
    
    return render(request, 'purchase/purchase_order_form.html', {
        'form': form, 
        'formset': formset,
        'rfq': rfq,
        'title': 'Create Purchase Order from RFQ'
    })

@login_required
def purchase_order_edit(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, instance=order)
        formset = PurchaseOrderItemFormSet(request.POST, instance=order)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Purchase Order updated successfully.')
            return redirect('purchase_order_list')
    else:
        form = PurchaseOrderForm(instance=order)
        formset = PurchaseOrderItemFormSet(instance=order)
    
    return render(request, 'purchase/purchase_order_form.html', {
        'form': form, 
        'formset': formset,
        'title': 'Edit Purchase Order'
    })

@login_required
def purchase_order_detail(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    return render(request, 'purchase/purchase_order_detail.html', {'order': order})

@login_required
def purchase_order_pdf(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    
    try:
        # Render HTML template
        html_string = render_to_string('purchase/purchase_order_pdf.html', {'order': order})
        html = HTML(string=html_string)
        
        # Generate PDF
        result = html.write_pdf()
        
        # Create HTTP response with PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="purchase_order_{order.po_number}.pdf"'
        response.write(result)
        
        return response
    
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('purchase_order_detail', pk=order.po_id)

# GRN Views
@login_required
def grn_list(request):
    grns = GoodsReceivedNote.objects.all().select_related('purchase_order', 'received_by', 'verified_by')
    
    # Filter functionality
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if status_filter:
        grns = grns.filter(status=status_filter)
    
    if date_from:
        grns = grns.filter(received_date__gte=date_from)
    
    if date_to:
        grns = grns.filter(received_date__lte=date_to)
    
    status_choices = GoodsReceivedNote.GRN_STATUS
    
    paginator = Paginator(grns, 10)  # Show 25 GRNs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'purchase/grn_list.html', {
        'grns': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'status_choices': status_choices
    })

@login_required
def grn_create(request):
    if request.method == 'POST':
        form = GoodsReceivedNoteForm(request.POST)
        formset = GRNItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            grn = form.save(commit=False)
            grn.received_by = request.user
            grn.save()
            
            formset.instance = grn
            formset.save()
            
            messages.success(request, 'GRN created successfully.')
            return redirect('grn_list')
    else:
        form = GoodsReceivedNoteForm()
        formset = GRNItemFormSet()
    
    return render(request, 'purchase/grn_form.html', {
        'form': form, 
        'formset': formset,
        'title': 'Create GRN'
    })

@login_required
def grn_from_po(request, po_id):
    po = get_object_or_404(PurchaseOrder, pk=po_id)
    
    if request.method == 'POST':
        form = GoodsReceivedNoteForm(request.POST)
        formset = GRNItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            grn = form.save(commit=False)
            grn.purchase_order = po
            grn.received_by = request.user
            grn.save()
            
            formset.instance = grn
            formset.save()
            
            messages.success(request, 'GRN created from Purchase Order successfully.')
            return redirect('grn_detail', pk=grn.pk)
    else:
        form = GoodsReceivedNoteForm(initial={
            'purchase_order': po,
            'received_date': timezone.now().date(),
        })
        
        # Prepopulate items from PO
        formset = GRNItemFormSet(initial=[
            {
                'po_item': item.pk,   # pass pk instead of object
                'quantity_received': item.quantity - item.received_quantity,
                'quantity_accepted': item.quantity - item.received_quantity,
                'quality_status': 'accepted',
            }
            for item in po.items.all()
            if item.quantity > item.received_quantity
        ], form_kwargs={'purchase_order': po})

    
    return render(request, 'purchase/grn_form.html', {
        'form': form, 
        'formset': formset,
        'po': po,
        'title': 'Create GRN from Purchase Order'
    })

@login_required
def grn_edit(request, pk):
    grn = get_object_or_404(GoodsReceivedNote, pk=pk)
    if request.method == 'POST':
        form = GoodsReceivedNoteForm(request.POST, instance=grn)
        formset = GRNItemFormSet(request.POST, instance=grn)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'GRN updated successfully.')
            return redirect('grn_list')
    else:
        form = GoodsReceivedNoteForm(instance=grn)
        formset = GRNItemFormSet(instance=grn)
    
    return render(request, 'purchase/grn_form.html', {
        'form': form, 
        'formset': formset,
        'title': 'Edit GRN'
    })

@login_required
def grn_detail(request, pk):
    grn = get_object_or_404(GoodsReceivedNote, pk=pk)
    return render(request, 'purchase/grn_detail.html', {'grn': grn})

@login_required
def grn_verify(request, pk):
    grn = get_object_or_404(GoodsReceivedNote, pk=pk)
    
    if request.method == 'POST':
        try:
            grn.status = 'verified'
            grn.verified_by = request.user
            grn.save()
            
            # Update inventory for all accepted items
            for item in grn.items.all():
                if item.quality_status == 'accepted' and item.quantity_accepted > 0:
                    # Find or create inventory record
                    inventory, created = Inventory.objects.get_or_create(
                        component=item.po_item.component,
                        defaults={'quantity_on_hand': 0, 'quantity_allocated': 0}
                    )
                    
                    # Update quantity on hand
                    inventory.quantity_on_hand += item.quantity_accepted
                    inventory.save()
            
            messages.success(request, 'GRN verified and inventory updated.')
            return redirect('grn_detail', pk=grn.pk)
        
        except Exception as e:
            messages.error(request, f'Error verifying GRN: {str(e)}')
            return redirect('grn_detail', pk=grn.pk)
    
    return render(request, 'purchase/grn_verify.html', {'grn': grn})

# Supplier Invoice Views
@login_required
def supplier_invoice_list(request):
    invoices = SupplierInvoice.objects.all().select_related('supplier', 'purchase_order', 'grn', 'created_by')
    
    # Filter functionality
    status_filter = request.GET.get('status', '')
    supplier_filter = request.GET.get('supplier', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if status_filter:
        invoices = invoices.filter(status=status_filter)
    
    if supplier_filter:
        invoices = invoices.filter(supplier_id=supplier_filter)
    
    if date_from:
        invoices = invoices.filter(invoice_date__gte=date_from)
    
    if date_to:
        invoices = invoices.filter(invoice_date__lte=date_to)
    
    suppliers = Supplier.objects.all()
    status_choices = SupplierInvoice.INVOICE_STATUS
    
    paginator = Paginator(invoices, 10)  # Show 25 invoices per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'purchase/supplier_invoice_list.html', {
        'invoices': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'suppliers': suppliers,
        'status_choices': status_choices
    })

@login_required
def supplier_invoice_create(request):
    if request.method == 'POST':
        form = SupplierInvoiceForm(request.POST, request.FILES)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.created_by = request.user
            invoice.save()
            messages.success(request, 'Supplier Invoice created successfully.')
            return redirect('supplier_invoice_list')
    else:
        form = SupplierInvoiceForm()
    
    return render(request, 'purchase/supplier_invoice_form.html', {
        'form': form, 
        'title': 'Create Supplier Invoice'
    })

@login_required
def supplier_invoice_from_grn(request, grn_id):
    grn = get_object_or_404(GoodsReceivedNote, pk=grn_id)
    
    if request.method == 'POST':
        form = SupplierInvoiceForm(request.POST, request.FILES)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.grn = grn
            invoice.purchase_order = grn.purchase_order
            invoice.supplier = grn.purchase_order.supplier
            invoice.created_by = request.user
            
            # Calculate amounts from PO
            invoice.amount = grn.purchase_order.subtotal
            invoice.tax_amount = grn.purchase_order.tax_amount
            invoice.total_amount = grn.purchase_order.total_amount
            
            invoice.save()
            
            messages.success(request, 'Supplier Invoice created from GRN successfully.')
            return redirect('supplier_invoice_detail', pk=invoice.pk)
    else:
        form = SupplierInvoiceForm(initial={
            'grn': grn,
            'purchase_order': grn.purchase_order,
            'supplier': grn.purchase_order.supplier,
            'invoice_date': timezone.now().date(),
            'due_date': timezone.now().date() + timezone.timedelta(days=30),
            'amount': grn.purchase_order.subtotal,
            'tax_amount': grn.purchase_order.tax_amount,
            'total_amount': grn.purchase_order.total_amount,
        })
    
    return render(request, 'purchase/supplier_invoice_form.html', {
        'form': form, 
        'grn': grn,
        'title': 'Create Supplier Invoice from GRN'
    })

@login_required
def supplier_invoice_edit(request, pk):
    invoice = get_object_or_404(SupplierInvoice, pk=pk)
    if request.method == 'POST':
        form = SupplierInvoiceForm(request.POST, request.FILES, instance=invoice)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier Invoice updated successfully.')
            return redirect('supplier_invoice_list')
    else:
        form = SupplierInvoiceForm(instance=invoice)
    
    return render(request, 'purchase/supplier_invoice_form.html', {
        'form': form, 
        'title': 'Edit Supplier Invoice'
    })

@login_required
def supplier_invoice_detail(request, pk):
    invoice = get_object_or_404(SupplierInvoice, pk=pk)
    return render(request, 'purchase/supplier_invoice_detail.html', {'invoice': invoice})

# AJAX Views

@login_required
def get_customer_details(request, customer_id):
    """AJAX view to get customer details"""
    try:
        customer = Customer.objects.get(pk=customer_id)
        data = {
            'email': customer.email,
            'phone': customer.phone,
            'contact_person': customer.contact_person or '',
            'address': customer.address,
            'payment_terms': customer.payment_terms,
            'currency': customer.currency,
        }
        return JsonResponse(data)
    except Customer.DoesNotExist:
        return JsonResponse({'error': 'Customer not found'}, status=404)
    
@login_required
def get_component_details(request, component_id):
    """AJAX view to get component details"""
    try:
        component = Component.objects.get(pk=component_id)
        data = {
            'description': component.description,
            'unit_of_measure': component.unit_of_measure,
            'material': component.material or '',
            'tolerance': component.tolerance or '',
            'finish': component.finish or '',
        }
        return JsonResponse(data)
    except Component.DoesNotExist:
        return JsonResponse({'error': 'Component not found'}, status=404)

@login_required
def get_bom_details(request, bom_id):
    """AJAX view to get BOM details"""
    try:
        bom = BOMHeader.objects.get(pk=bom_id)
        data = {
            'description': bom.description,
            'revision': bom.revision,
            'status': bom.status,
        }
        return JsonResponse(data)
    except BOMHeader.DoesNotExist:
        return JsonResponse({'error': 'BOM not found'}, status=404)

@login_required
def get_customer_pricing(request, customer_id, component_id):
    """AJAX view to get customer pricing"""
    try:
        pricing = CustomerPricing.objects.get(
            customer_id=customer_id,
            component_id=component_id,
            effective_date__lte=timezone.now().date(),
            expiry_date__gte=timezone.now().date()
        )
        data = {
            'price': str(pricing.price),
            'min_order_quantity': pricing.min_order_quantity,
            'exists': True,
        }
        return JsonResponse(data)
    except CustomerPricing.DoesNotExist:
        data = {'exists': False}
        return JsonResponse(data)

@csrf_exempt
def calculate_price(request):
    try:
        data = json.loads(request.body)
        item_type = data.get('item_type')
        item_id = data.get('item_id')
        customer_id = data.get('customer_id')
        currency = data.get('currency', 'USD')
                
        customer = get_object_or_404(Customer, pk=customer_id)
        unit_price = Decimal('0.00')
        
        if item_type == 'part':
            component = get_object_or_404(Component, pk=item_id)
            
            # Try to get customer-specific pricing
            try:
                customer_pricing = CustomerPricing.objects.get(
                    customer=customer,
                    component=component,
                    effective_date__lte=timezone.now().date(),
                    expiry_date__gte=timezone.now().date()
                )
                unit_price = customer_pricing.price
            except CustomerPricing.DoesNotExist:
                # Get lowest supplier price with markup
                supplier_price = ComponentSupplier.objects.filter(
                    component=component,
                    is_approved=True
                ).order_by('cost').first()
                
                if supplier_price:
                    unit_price = supplier_price.cost * Decimal('1.2')  # 20% markup
                else:
                    unit_price = Decimal('0.00')  # Default price
        
        elif item_type == 'product':
            bom = get_object_or_404(BOMHeader, pk=item_id)
            # Calculate price from BOM
            bom_cost = calculate_bom_cost(bom.id)
            unit_price = bom_cost * Decimal('1.3')  # 30% markup
        
        # Apply currency conversion if needed (you would implement this)
        # unit_price = convert_currency(unit_price, 'USD', currency)
        
        return JsonResponse({
            'unit_price': float(unit_price),
            'currency': currency
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def calculate_bom_cost(request, bom_id):
    """AJAX view to calculate BOM cost"""
    try:
        bom = BOMHeader.objects.get(pk=bom_id)
        total_cost = Decimal('0.00')
        
        for item in bom.items.all():
            # Get the lowest supplier price for this component
            supplier_price = ComponentSupplier.objects.filter(
                component=item.component,
                is_approved=True
            ).order_by('cost').first()
            
            if supplier_price:
                total_cost += supplier_price.cost * item.quantity
            else:
                # Use a default cost if no supplier price is available
                total_cost += Decimal('10.00') * item.quantity  # Default cost
        
        data = {
            'cost': str(total_cost),
            'selling_price': str(total_cost * Decimal('1.3')),  # 30% markup
        }
        return JsonResponse(data)
    except BOMHeader.DoesNotExist:
        return JsonResponse({'error': 'BOM not found'}, status=404)


@login_required
def calculate_bom_cost_ajax(request, bom_id):
    bom = get_object_or_404(BOMHeader, pk=bom_id)
    total_cost = Decimal('0.00')
    
    for item in bom.items.all():
        # Get the lowest supplier price for this component
        supplier_price = ComponentSupplier.objects.filter(
            component=item.component,
            is_approved=True
        ).order_by('cost').first()
        
        if supplier_price:
            total_cost += supplier_price.cost * item.quantity
        else:
            # Use a default cost if no supplier price is available
            total_cost += Decimal('0.00') * item.quantity
    
    # Apply markup (30%)
    selling_price = total_cost * Decimal('1.3')
    
    return JsonResponse({
        'cost': str(total_cost),
        'selling_price': str(selling_price)
    })


@login_required
def upload_customer_po(request, order_id):
    """Handle customer PO file upload"""
    order = get_object_or_404(SalesOrder, pk=order_id)
    
    if request.method == 'POST' and request.FILES.get('po_file'):
        order.customer_po_file = request.FILES['po_file']
        order.save()
        messages.success(request, 'Customer PO file uploaded successfully.')
        return redirect('sales_order_detail', pk=order.order_id)
    
    return render(request, 'sales/upload_customer_po.html', {'order': order})

@login_required
def upload_supplier_invoice(request, invoice_id):
    """Handle supplier invoice file upload"""
    invoice = get_object_or_404(SupplierInvoice, pk=invoice_id)
    
    if request.method == 'POST' and request.FILES.get('invoice_file'):
        invoice.invoice_file = request.FILES['invoice_file']
        invoice.save()
        messages.success(request, 'Supplier invoice file uploaded successfully.')
        return redirect('supplier_invoice_detail', pk=invoice.invoice_id)
    
    return render(request, 'purchase/upload_supplier_invoice.html', {'invoice': invoice})

@login_required
def mark_invoice_paid(request, invoice_id):
    """Mark invoice as paid"""
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    
    if request.method == 'POST':
        amount_paid = Decimal(request.POST.get('amount_paid', 0))
        
        if amount_paid <= 0:
            messages.error(request, 'Amount paid must be greater than zero.')
        elif amount_paid > invoice.total_amount - invoice.amount_paid:
            messages.error(request, 'Amount paid cannot exceed the remaining balance.')
        else:
            invoice.amount_paid += amount_paid
            
            if invoice.amount_paid >= invoice.total_amount:
                invoice.status = 'paid'
            else:
                invoice.status = 'partially_paid'
                
            invoice.save()
            messages.success(request, f'Payment of {amount_paid} recorded successfully.')
        
        return redirect('invoice_detail', pk=invoice.invoice_id)
    
    return render(request, 'sales/mark_invoice_paid.html', {'invoice': invoice})

@login_required
def mark_supplier_invoice_paid(request, invoice_id):
    """Mark supplier invoice as paid"""
    invoice = get_object_or_404(SupplierInvoice, pk=invoice_id)
    
    if request.method == 'POST':
        invoice.status = 'paid'
        invoice.save()
        messages.success(request, 'Supplier invoice marked as paid.')
        return redirect('supplier_invoice_detail', pk=invoice.invoice_id)
    
    return render(request, 'purchase/mark_supplier_invoice_paid.html', {'invoice': invoice})

import vertexai
from vertexai.generative_models import GenerativeModel, Part
import re

def extract_invoice_data(pdf_file):

    vertexai.init(project="powerful-lore-471112-k7", location="us-central1")

    model = GenerativeModel("gemini-2.5-flash")

    prompt = """
    You are a highly intelligent document parser specializing in invoice data extraction.

    I will provide you with a scanned PDF page of an invoice. Your task is to accurately extract all relevant data fields from this invoice. The data can be located anywhere on the page, including headers, tables, footers, or handwritten notes.

    If any data field is unclear or missing from the image, use your trained knowledge to infer it as accurately as possible.

    Required output format (JSON):
    {
      "invoice_number": "",
      "invoice_date": "",
      "due_date": "",
      "supplier_name": "",
      "customer_name": "",
      "subtotal": null,
      "tax_amount": null,
      "total_amount": null,
      "currency": "",
      "line_items": [
        {
          "description": "",
          "quantity": null,
          "unit_price": null,
          "total": null
        }
      ],
      "notes": ""
    }

    Important Notes:
    - Extract all available data from the invoice.
    - If a field is not present in the invoice, leave its value as an empty string, null, or an empty list, as appropriate.
    - Accurately parse numerical values for prices, quantities, and totals.
    - Output should always be in English and in strict JSON format only (no extra text).
    """

    try:
        pdf_part = Part.from_data(
            mime_type="application/pdf",
            data=pdf_file.read()
        )

        response = model.generate_content(
            [prompt, pdf_part],
            generation_config={"temperature": 0.1}
        )

        # Extract JSON from response
        json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        data = json.loads(json_str)
        return data

    except (AttributeError, json.JSONDecodeError) as e:
        return {
            "success": False,
            "error": "Error parsing JSON from Gemini response.",
            "traceback": traceback.format_exc()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

# Update the InvoiceListView to pass status options
class InvoiceListView(ListView):
    model = Invoice_VAI
    template_name = 'purchase/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_options'] = Invoice_VAI.INVOICE_STATUS
        return context
    

class InvoiceDetailView(DetailView):
    model = Invoice_VAI
    template_name = 'purchase/invoice_detail.html'
    context_object_name = 'invoice'

class InvoiceUploadView(View):
    def get(self, request):
        form = InvoiceUploadForm()
        return render(request, 'purchase/upload_invoice.html', {'form': form})

    def post(self, request):
        form = InvoiceUploadForm(request.POST, request.FILES)
        if form.is_valid():
            pdf_file = request.FILES['invoice_file']
            try:
                extracted_data = extract_invoice_data(pdf_file)
                if not extracted_data.get('success', True):
                    return JsonResponse(extracted_data, status=500)

                # Save data to Django models
                try:
                    invoice = Invoice_VAI(
                        invoice_number=extracted_data.get('invoice_number'),
                        invoice_date=extracted_data.get('invoice_date'),
                        due_date=extracted_data.get('due_date'),
                        total_amount=extracted_data.get('total_amount', 0),
                        customer_name=extracted_data.get('customer_name'),
                        vendor_name=extracted_data.get('supplier_name'),
                    )
                    invoice.save()

                    for item_data in extracted_data.get('line_items', []):
                        InvoiceItem_VAI.objects.create(
                            invoice=invoice,
                            description=item_data.get('description'),
                            quantity=item_data.get('quantity', 0),
                            price_per_unit=item_data.get('unit_price', 0),
                            total=item_data.get('total', 0),
                        )

                    # return JsonResponse({
                    #     "success": True,
                    #     "message": "Invoice data extracted and saved successfully.",
                    #     "invoice_id": invoice.invoice_id
                    # })
                    messages.success(request, 'Invoice uploaded and processed successfully.')
                    return redirect('invoice_detail_vai', pk=invoice.invoice_id)

                except Exception as e:
                    return JsonResponse({
                        "success": False,
                        "error": "Error saving data to models.",
                        "details": str(e),
                        "traceback": traceback.format_exc()
                    }, status=500)
                
            except Exception as e:
                messages.error(request, f'Error processing invoice: {str(e)}')
                return render(request, 'purchase/upload_invoice.html', {'form': form})
        return render(request, 'purchase/upload_invoice.html', {'form': form})
    
def update_invoice_status(request, pk):
    if request.method == 'POST' and request.is_ajax():
        invoice = get_object_or_404(Invoice_VAI, pk=pk)
        new_status = request.POST.get('status')
        
        if new_status in dict(Invoice_VAI.INVOICE_STATUS):
            invoice.status = new_status
            invoice.save()
            return JsonResponse({'success': True, 'new_status': invoice.get_status_display()})
    
    return JsonResponse({'success': False})