# admin.py
from django.contrib import admin
from .models import *
from BOM.models import *
from MaterialPlan.models import *

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'email', 'phone', 'created_date']
    list_filter = ['type', 'created_date']
    search_fields = ['name', 'email', 'contact_person']

@admin.register(CustomerPricing)
class CustomerPricingAdmin(admin.ModelAdmin):
    list_display = ['customer', 'component', 'bom', 'price', 'effective_date', 'expiry_date']
    list_filter = ['effective_date', 'expiry_date']
    search_fields = ['customer__name', 'component__part_number', 'bom__name']

@admin.register(RFQ)
class RFQAdmin(admin.ModelAdmin):
    list_display = ['rfq_number', 'customer', 'rfq_date', 'required_by_date', 'status']
    list_filter = ['status', 'rfq_date', 'required_by_date']
    search_fields = ['rfq_number', 'customer__name']

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ['quotation_number', 'customer', 'quotation_date', 'expiry_date', 'status', 'total_amount']
    list_filter = ['status', 'quotation_date', 'expiry_date']
    search_fields = ['quotation_number', 'customer__name']

@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer', 'order_date', 'delivery_date', 'status', 'total_amount']
    list_filter = ['status', 'order_date', 'delivery_date']
    search_fields = ['order_number', 'customer__name']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'sales_order', 'invoice_date', 'due_date', 'status', 'total_amount']
    list_filter = ['status', 'invoice_date', 'due_date']
    search_fields = ['invoice_number', 'sales_order__order_number']

@admin.register(PurchaseRFQ)
class PurchaseRFQAdmin(admin.ModelAdmin):
    list_display = ['rfq_number', 'title', 'status', 'created_date']
    list_filter = ['status', 'created_date']
    search_fields = ['rfq_number', 'title']

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'supplier', 'order_date', 'expected_delivery_date', 'status', 'total_amount']
    list_filter = ['status', 'order_date', 'expected_delivery_date']
    search_fields = ['po_number', 'supplier__name']

@admin.register(GoodsReceivedNote)
class GoodsReceivedNoteAdmin(admin.ModelAdmin):
    list_display = ['grn_number', 'purchase_order', 'received_date', 'status']
    list_filter = ['status', 'received_date']
    search_fields = ['grn_number', 'purchase_order__po_number']

@admin.register(SupplierInvoice)
class SupplierInvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'supplier', 'invoice_date', 'due_date', 'status', 'total_amount']
    list_filter = ['status', 'invoice_date', 'due_date']
    search_fields = ['invoice_number', 'supplier__name']

# Register all other models
admin.site.register(Component)
admin.site.register(Supplier)
admin.site.register(ComponentSupplier)
admin.site.register(InventoryLocation)
admin.site.register(Inventory)
admin.site.register(BOMHeader)
admin.site.register(BOMItem)
admin.site.register(BOMRevision)
admin.site.register(MaterialPlan)
admin.site.register(MaterialPlanItem)
admin.site.register(PurchaseRequisition)
admin.site.register(InventoryReservation)
admin.site.register(ProductionOrder)
admin.site.register(MaterialShortageAlert)