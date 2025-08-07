# inventory/admin.py
from django.contrib import admin
from .models import *
from django.utils.safestring import mark_safe

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'current_stock', 'selling_price', 'is_active')
    list_filter = ('category', 'is_active', 'type')
    search_fields = ('name', 'sku', 'upc', 'description')
    inlines = [ProductImageInline, ProductVariantInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'sku', 'upc', 'description', 'category', 'type', 'is_active')
        }),
        ('Pricing', {
            'fields': ('cost_price', 'selling_price'),
            'classes': ('collapse',)
        }),
        ('Inventory', {
            'fields': ('min_stock_level',),
            'classes': ('collapse',)
        }),
        ('Physical Attributes', {
            'fields': ('weight', 'dimensions'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'type', 'capacity_percentage', 'is_active')
    list_filter = ('type', 'is_active')
    search_fields = ('name', 'code', 'address')

# inventory/admin.py
@admin.register(StorageLocation)
class StorageLocationAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'warehouse', 'type', 'current_weight', 'current_volume', 'is_active')
    list_filter = ('warehouse', 'type', 'is_active')
    search_fields = ('code', 'name', 'warehouse__name')
    readonly_fields = ('current_weight', 'current_volume')
    
    fieldsets = (
        (None, {
            'fields': ('warehouse', 'code', 'name', 'type', 'is_active')
        }),
        ('Capacity', {
            'fields': ('max_weight', 'current_weight', 'max_volume', 'current_volume'),
            'classes': ('collapse',)
        }),
        ('Additional', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ('product', 'location', 'quantity', 'entry_type', 'date_received')
    list_filter = ('entry_type', 'location__warehouse')
    search_fields = ('product__name', 'product__sku', 'batch_number')

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'from_location', 'to_location', 'quantity', 'movement_type', 'confirmed')
    list_filter = ('movement_type', 'confirmed', 'product__category')
    search_fields = ('product__name', 'product__sku', 'reference')


# inventory/admin.py
@admin.register(InventoryAlert)
class InventoryAlertAdmin(admin.ModelAdmin):
    list_display = ('product', 'get_alert_type_display', 'warehouse', 'location', 'threshold', 'is_active', 'acknowledged')
    list_filter = ('alert_type', 'is_active', 'acknowledged', 'warehouse')
    search_fields = ('product__name', 'product__sku', 'batch_number')
    actions = ['acknowledge_alerts']
    
    def acknowledge_alerts(self, request, queryset):
        queryset.update(acknowledged=True, acknowledged_by=request.user, acknowledged_at=timezone.now())
        self.message_user(request, f"{queryset.count()} alerts acknowledged")
    acknowledge_alerts.short_description = "Mark selected alerts as acknowledged"



@admin.register(ProductBarcode)
class ProductBarcodeAdmin(admin.ModelAdmin):
    list_display = ('product', 'variant', 'barcode_format', 'barcode_data', 'is_primary')
    list_filter = ('barcode_format', 'is_primary')
    search_fields = ('product__name', 'product__sku', 'barcode_data')
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" style="max-height: 100px;" />')
        return "-"
    image_preview.short_description = "Barcode Preview"