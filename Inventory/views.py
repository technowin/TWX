# Inventory/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic.edit import FormView
from django.db.models import Sum, F, Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import *
from .forms import *

class ThemeContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get theme preference from session or default to light
        theme = self.request.session.get('theme', 'light')
        context['theme'] = theme
        return context

# Product Management Views
class ProductListView(ListView):
    model = Product
    template_name = 'Inventory/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('category')
        search_query = self.request.GET.get('search')
        category_filter = self.request.GET.get('category')
        stock_filter = self.request.GET.get('stock')
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(sku__icontains=search_query) |
                Q(upc__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        if category_filter:
            queryset = queryset.filter(category__id=category_filter)
        
        if stock_filter == 'low':
            queryset = queryset.annotate(total_stock=Sum('stock_entries__quantity'))
            queryset = queryset.filter(total_stock__lte=F('min_stock_level'))
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['search_query'] = self.request.GET.get('search', '')
        context['category_filter'] = self.request.GET.get('category', '')
        context['stock_filter'] = self.request.GET.get('stock', '')
        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = 'Inventory/product_detail.html'
    context_object_name = 'product'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        
        # Stock information
        stock_entries = product.stock_entries.select_related('location', 'location__warehouse')
        stock_by_location = {}
        
        for entry in stock_entries:
            loc = entry.location
            if loc not in stock_by_location:
                stock_by_location[loc] = 0
            stock_by_location[loc] += entry.quantity
        
        context['stock_by_location'] = stock_by_location
        context['total_stock'] = sum(stock_by_location.values())
        context['movements'] = product.movements.order_by('-moved_at')[:10]
        
        return context

class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'Inventory/product_form.html'
    permission_required = 'inventory.add_product'
    success_message = "Product created successfully!"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_formset'] = ProductImageFormSet(self.request.POST, self.request.FILES)
            context['variant_formset'] = ProductVariantFormSet(self.request.POST)
        else:
            context['image_formset'] = ProductImageFormSet()
            context['variant_formset'] = ProductVariantFormSet()
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context['image_formset']
        variant_formset = context['variant_formset']
        
        if image_formset.is_valid() and variant_formset.is_valid():
            self.object = form.save()
            image_formset.instance = self.object
            image_formset.save()
            variant_formset.instance = self.object
            variant_formset.save()
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))
    
    def get_success_url(self):
        return reverse_lazy('product-detail', kwargs={'pk': self.object.pk})

class ProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'Inventory/product_form.html'
    permission_required = 'inventory.change_product'
    success_message = "Product updated successfully!"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_formset'] = ProductImageFormSet(self.request.POST, self.request.FILES, instance=self.object)
            context['variant_formset'] = ProductVariantFormSet(self.request.POST, instance=self.object)
        else:
            context['image_formset'] = ProductImageFormSet(instance=self.object)
            context['variant_formset'] = ProductVariantFormSet(instance=self.object)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context['image_formset']
        variant_formset = context['variant_formset']
        
        if image_formset.is_valid() and variant_formset.is_valid():
            self.object = form.save()
            image_formset.instance = self.object
            image_formset.save()
            variant_formset.instance = self.object
            variant_formset.save()
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))
    
    def get_success_url(self):
        return reverse_lazy('product-detail', kwargs={'pk': self.object.pk})

# Warehouse Management Views
class WarehouseListView(ListView):
    model = Warehouse
    template_name = 'Inventory/warehouse_list.html'
    context_object_name = 'warehouses'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search')
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(code__icontains=search_query) |
                Q(address__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context

class WarehouseDetailView(DetailView):
    model = Warehouse
    template_name = 'Inventory/warehouse_detail.html'
    context_object_name = 'warehouse'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        warehouse = self.get_object()
        
        # Get all locations in this warehouse
        locations = warehouse.locations.all()
        context['locations'] = locations
        
        # Get stock summary for this warehouse
        stock_entries = StockEntry.objects.filter(location__warehouse=warehouse)
        product_stock = {}
        
        for entry in stock_entries:
            if entry.product not in product_stock:
                product_stock[entry.product] = 0
            product_stock[entry.product] += entry.quantity
        
        context['product_stock'] = product_stock
        context['total_products'] = len(product_stock)
        context['total_items'] = sum(product_stock.values())
        
        return context

# Inventory/views.py
class WarehouseCreateView(CreateView):
    model = Warehouse
    form_class = WarehouseForm
    template_name = 'Inventory/warehouse_form.html'
    permission_required = 'inventory.add_warehouse'
    success_message = "Warehouse created successfully!"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('warehouse-detail', kwargs={'pk': self.object.pk})

class WarehouseUpdateView(UpdateView):
    model = Warehouse
    form_class = WarehouseForm
    template_name = 'Inventory/warehouse_form.html'
    permission_required = 'inventory.change_warehouse'
    success_message = "Warehouse updated successfully!"

    def get_success_url(self):
        return reverse_lazy('warehouse-detail', kwargs={'pk': self.object.pk})
    
# Stock Management Views
class StockEntryCreateView(CreateView):
    model = StockEntry
    form_class = StockEntryForm
    template_name = 'Inventory/stockentry_form.html'
    permission_required = 'inventory.add_stockentry'
    success_message = "Stock entry recorded successfully!"
    
    def get_initial(self):
        initial = super().get_initial()
        product_id = self.request.GET.get('product')
        if product_id:
            initial['product'] = get_object_or_404(Product, pk=product_id)
        return initial
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('product-detail', kwargs={'pk': self.object.product.pk})

class StockMovementCreateView(CreateView):
    model = StockMovement
    form_class = StockMovementForm
    template_name = 'Inventory/stockmovement_form.html'
    permission_required = 'inventory.add_stockmovement'
    success_message = "Stock movement created successfully!"
    
    def get_initial(self):
        initial = super().get_initial()
        product_id = self.request.GET.get('product')
        if product_id:
            initial['product'] = get_object_or_404(Product, pk=product_id)
        return initial
    
    def form_valid(self, form):
        form.instance.moved_by = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('stockmovement-detail', kwargs={'pk': self.object.pk})

class StockMovementConfirmView(UpdateView):
    model = StockMovement
    fields = []
    template_name = 'Inventory/stockmovement_confirm.html'
    permission_required = 'inventory.change_stockmovement'
    success_message = "Stock movement confirmed and stock levels updated!"
    
    def form_valid(self, form):
        form.instance.confirm_movement(self.request.user)
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('stockmovement-detail', kwargs={'pk': self.object.pk})

# AJAX Views for dynamic forms
def get_locations_for_warehouse(request):
    warehouse_id = request.GET.get('warehouse_id')
    locations = StorageLocation.objects.filter(warehouse_id=warehouse_id).order_by('code')
    return JsonResponse(list(locations.values('id', 'code', 'name')), safe=False)

def get_product_details(request):
    product_id = request.GET.get('product_id')
    product = get_object_or_404(Product, pk=product_id)
    data = {
        'name': product.name,
        'sku': product.sku,
        'current_stock': product.current_stock,
        'image_url': product.images.first().image.url if product.images.exists() else '',
    }
    return JsonResponse(data)

# Inventory/views.py
class StorageLocationCreateView(CreateView):
    model = StorageLocation
    form_class = StorageLocationForm
    template_name = 'Inventory/storage_location_form.html'
    permission_required = 'inventory.add_storagelocation'
    success_message = "Storage location created successfully!"

    def get_initial(self):
        initial = super().get_initial()
        warehouse_pk = self.kwargs.get('warehouse_pk')
        if warehouse_pk:
            initial['warehouse'] = get_object_or_404(Warehouse, pk=warehouse_pk)
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['warehouse_pk'] = self.kwargs.get('warehouse_pk')
        return context
    
    def get_success_url(self):
        return reverse_lazy('warehouse-detail', kwargs={'pk': self.object.warehouse.pk})
    
class StorageLocationUpdateView(UpdateView):
    model = StorageLocation
    form_class = StorageLocationForm
    template_name = 'Inventory/storage_location_form.html'
    permission_required = 'inventory.change_storagelocation'
    success_message = "Storage location updated successfully!"

    def get_success_url(self):
        return reverse_lazy('warehouse-detail', kwargs={'pk': self.object.warehouse.pk})

class StorageLocationDetailView(DetailView):
    model = StorageLocation
    template_name = 'Inventory/storage_location_detail.html'
    context_object_name = 'location'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        location = self.get_object()
        
        # Get stock entries for this location
        stock_entries = location.stock_entries.select_related('product')
        product_stock = {}
        
        for entry in stock_entries:
            if entry.product not in product_stock:
                product_stock[entry.product] = 0
            product_stock[entry.product] += entry.quantity
        
        context['product_stock'] = product_stock
        context['total_items'] = sum(product_stock.values())
        
        return context
    

# Inventory/views.py
class InventoryAlertListView(ListView):
    model = InventoryAlert
    template_name = 'Inventory/alert_list.html'
    context_object_name = 'alerts'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('product', 'warehouse', 'location')
        alert_type = self.request.GET.get('type')
        status = self.request.GET.get('status')
        
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        if status == 'active':
            queryset = queryset.filter(is_active=True, acknowledged=False)
        elif status == 'acknowledged':
            queryset = queryset.filter(acknowledged=True)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['alert_types'] = InventoryAlert.ALERT_TYPES
        context['current_type'] = self.request.GET.get('type')
        context['current_status'] = self.request.GET.get('status')
        return context

class AcknowledgeAlertView(View):
    permission_required = 'inventory.change_inventoryalert'
    
    def post(self, request, pk):
        alert = get_object_or_404(InventoryAlert, pk=pk)
        alert.acknowledge(request.user)
        messages.success(request, f"Alert acknowledged successfully!")
        return redirect('alert-list')
    

# Inventory/views.py
class BarcodeListView(ListView):
    model = ProductBarcode
    template_name = 'Inventory/barcode_list.html'
    context_object_name = 'barcodes'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('product', 'variant')
        product_id = self.request.GET.get('product')
        
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.all()
        return context

class BarcodeCreateView(CreateView):
    model = ProductBarcode
    form_class = BarcodeGenerateForm
    template_name = 'Inventory/barcode_form.html'
    permission_required = 'inventory.add_productbarcode'
    success_message = "Barcode generated successfully!"
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Generate the barcode image
        self.object.generate_barcode_image()
        
        # Set as primary if needed
        if form.cleaned_data['is_primary']:
            ProductBarcode.objects.filter(product=self.object.product).exclude(pk=self.object.pk).update(is_primary=False)
            self.object.is_primary = True
            self.object.save()
        
        return response
    
    def get_success_url(self):
        return reverse_lazy('barcode-list')

class SetPrimaryBarcodeView(View):
    permission_required = 'inventory.change_productbarcode'
    
    def post(self, request, pk):
        barcode = get_object_or_404(ProductBarcode, pk=pk)
        ProductBarcode.objects.filter(product=barcode.product).update(is_primary=False)
        barcode.is_primary = True
        barcode.save()
        messages.success(request, f"Barcode {barcode.barcode_data} set as primary for {barcode.product.name}")
        return redirect('barcode-list')
    
# Inventory/views.py
def get_product_variants(request):
    product_id = request.GET.get('product_id')
    variants = ProductVariant.objects.filter(product_id=product_id).values('id', 'name', 'value')
    return JsonResponse(list(variants), safe=False)


# Inventory/views.py
class CategoryDetailView(DetailView):
    model = Category
    template_name = 'Inventory/category_detail.html'
    context_object_name = 'category'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()
        
        # Get all products in this category
        products = Product.objects.filter(category=category)
        context['products'] = products
        
        # Get subcategories
        context['subcategories'] = category.children.all()
        
        return context
    

# Inventory/views.py
class CategoryCreateView(CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'Inventory/category_form.html'
    permission_required = 'inventory.add_category'
    success_message = "Category created successfully!"

    def get_initial(self):
        initial = super().get_initial()
        parent_pk = self.request.GET.get('parent')
        if parent_pk:
            initial['parent'] = get_object_or_404(Category, pk=parent_pk)
        return initial

    def get_success_url(self):
        return reverse_lazy('category-detail', kwargs={'slug': self.object.slug})

class CategoryUpdateView(UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'Inventory/category_form.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    permission_required = 'inventory.change_category'
    success_message = "Category updated successfully!"

    def get_success_url(self):
        return reverse_lazy('category-detail', kwargs={'slug': self.object.slug})
    
# Inventory/views.py
class CategoryListView(ListView):
    model = Category
    template_name = 'Inventory/category_list.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        return Category.objects.filter(parent__isnull=True)  # Only show top-level categories
    



# inventory/views/dashboard.py
from django.shortcuts import render
from django.db.models import Sum, Count, F, Q, ExpressionWrapper, DecimalField
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.db.models import Value

@login_required
def inventory_dashboard(request):
    # Inventory Summary Metrics
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_warehouses = Warehouse.objects.count()
    
    # Calculate inventory value by summing (stock_entries.quantity * product.cost_price)
    inventory_value = StockEntry.objects.annotate(
        entry_value=ExpressionWrapper(
            F('quantity') * F('product__cost_price'),
            output_field=DecimalField()
        )
    ).aggregate(total_value=Sum('entry_value'))['total_value'] or 0
    
    # Low Stock Alerts - we'll do this differently since we can't use the property in query
    low_stock_products = Product.objects.annotate(
        total_stock=Coalesce(Sum('stock_entries__quantity'), 0)
    ).filter(
        total_stock__lte=F('min_stock_level')
    ).count()
    
    # Warehouse Capacity
    warehouses = Warehouse.objects.annotate(
        available_capacity=F('total_capacity') - F('used_capacity')
    ).order_by('-used_capacity')[:5]
    
    # Recent Stock Movements
    recent_movements = StockMovement.objects.select_related(
        'product', 'from_location', 'to_location'
    ).order_by('-moved_at')[:10]
    
    # Inventory Alerts
    active_alerts = InventoryAlert.objects.filter(
        is_active=True, acknowledged=False
    ).select_related('product', 'warehouse', 'location')[:5]
    
    # Category Distribution
    categories = Category.objects.annotate(
        product_count=Count('products')
    ).order_by('-product_count')[:10]
    
    # Stock Movement Analysis (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    movement_types = StockMovement.objects.filter(
        moved_at__gte=thirty_days_ago
    ).values('movement_type').annotate(
        count=Count('id'),
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')
    
    # Warehouse Stock Levels
    warehouse_stock = Warehouse.objects.annotate(
        total_items=Coalesce(
            Sum('locations__stock_entries__quantity', output_field=DecimalField()),
            Value(0, output_field=DecimalField())
        ),
        total_value=Coalesce(
            Sum(
                ExpressionWrapper(
                    F('locations__stock_entries__quantity') * 
                    F('locations__stock_entries__product__cost_price'),
                    output_field=DecimalField()
                )
            ),
            Value(0, output_field=DecimalField())
        )
    ).order_by('-total_value')[:5]


    # Expiring Stock (next 30 days)
    expiring_soon = StockEntry.objects.filter(
        expiry_date__gte=timezone.now().date(),
        expiry_date__lte=timezone.now().date() + timedelta(days=30)
    ).select_related('product', 'location').order_by('expiry_date')[:5]
    
    context = {
        'total_products': total_products,
        'total_categories': total_categories,
        'total_warehouses': total_warehouses,
        'inventory_value': inventory_value,
        'low_stock_products': low_stock_products,
        'warehouses': warehouses,
        'recent_movements': recent_movements,
        'active_alerts': active_alerts,
        'categories': categories,
        'movement_types': movement_types,
        'warehouse_stock': warehouse_stock,
        'expiring_soon': expiring_soon,
    }
    
    return render(request, 'Inventory/dashboard.html', context)

@login_required
def stock_movement_list(request):
    movements = StockMovement.objects.select_related(
        'product', 'from_location', 'to_location', 'moved_by'
    ).order_by('-moved_at')
    
    # Add pagination
    paginator = Paginator(movements, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'movement_types': StockMovement.MOVEMENT_TYPES,
    }
    return render(request, 'inventory/stock_movement_list.html', context)