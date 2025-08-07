# inventory/views.py
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
    template_name = 'inventory/product_list.html'
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
    template_name = 'inventory/product_detail.html'
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
    template_name = 'inventory/product_form.html'
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
    template_name = 'inventory/product_form.html'
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
    template_name = 'inventory/warehouse_list.html'
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
    template_name = 'inventory/warehouse_detail.html'
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

# inventory/views.py
class WarehouseCreateView(CreateView):
    model = Warehouse
    form_class = WarehouseForm
    template_name = 'inventory/warehouse_form.html'
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
    template_name = 'inventory/warehouse_form.html'
    permission_required = 'inventory.change_warehouse'
    success_message = "Warehouse updated successfully!"

    def get_success_url(self):
        return reverse_lazy('warehouse-detail', kwargs={'pk': self.object.pk})
    
# Stock Management Views
class StockEntryCreateView(CreateView):
    model = StockEntry
    form_class = StockEntryForm
    template_name = 'inventory/stockentry_form.html'
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
    template_name = 'inventory/stockmovement_form.html'
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
    template_name = 'inventory/stockmovement_confirm.html'
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

# inventory/views.py
class StorageLocationCreateView(CreateView):
    model = StorageLocation
    form_class = StorageLocationForm
    template_name = 'inventory/storage_location_form.html'
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

    def get_success_url(self):
        return reverse_lazy('warehouse-detail', kwargs={'pk': self.object.warehouse.pk})

class StorageLocationUpdateView(UpdateView):
    model = StorageLocation
    form_class = StorageLocationForm
    template_name = 'inventory/storage_location_form.html'
    permission_required = 'inventory.change_storagelocation'
    success_message = "Storage location updated successfully!"

    def get_success_url(self):
        return reverse_lazy('warehouse-detail', kwargs={'pk': self.object.warehouse.pk})

class StorageLocationDetailView(DetailView):
    model = StorageLocation
    template_name = 'inventory/storage_location_detail.html'
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
    

# inventory/views.py
class InventoryAlertListView(ListView):
    model = InventoryAlert
    template_name = 'inventory/alert_list.html'
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
    

# inventory/views.py
class BarcodeListView(ListView):
    model = ProductBarcode
    template_name = 'inventory/barcode_list.html'
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
    template_name = 'inventory/barcode_form.html'
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
    
# inventory/views.py
def get_product_variants(request):
    product_id = request.GET.get('product_id')
    variants = ProductVariant.objects.filter(product_id=product_id).values('id', 'name', 'value')
    return JsonResponse(list(variants), safe=False)