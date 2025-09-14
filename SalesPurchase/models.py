from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
from Account.models import CustomUser
from BOM.models import *
from MaterialPlan.models import *
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone

CURRENCY_CHOICES = (
        ('USD', 'USD - US Dollar'),
        ('EUR', 'EUR - Euro'),
        ('GBP', 'GBP - British Pound'),
        ('JPY', 'JPY - Japanese Yen'),
        ('CAD', 'CAD - Canadian Dollar'),
        ('AUD', 'AUD - Australian Dollar'),
        ('CHF', 'CHF - Swiss Franc'),
        ('CNY', 'CNY - Chinese Yuan'),
        ('INR', 'INR - Indian Rupee'),
        ('SGD', 'SGD - Singapore Dollar'),
        ('AED', 'AED - UAE Dirham'),
        ('SAR', 'SAR - Saudi Riyal'),
    )

# Sales Models
class Customer(models.Model):
    CUSTOMER_TYPES = (
        ('individual', 'Individual'),
        ('business', 'Business'),
    )
    
    customer_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=CUSTOMER_TYPES, default='business')
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    payment_terms = models.CharField(max_length=100, default='Net 30')
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='customers_created')
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class CustomerPricing(models.Model):
    pricing_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='pricing_records')
    component = models.ForeignKey(Component, on_delete=models.CASCADE, null=True, blank=True)
    bom = models.ForeignKey(BOMHeader, on_delete=models.CASCADE, null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    effective_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    min_order_quantity = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('customer', 'component', 'effective_date')
        verbose_name_plural = "Customer Pricing"
    
    def __str__(self):
        if self.component:
            return f"{self.customer.name} - {self.component.part_number} - {self.price}"
        else:
            return f"{self.customer.name} - {self.bom.name} - {self.price}"

class RFQ(models.Model):
    RFQ_STATUS = (
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('quoted', 'Quoted'),
        ('closed', 'Closed'),
    )
    
    rfq_id = models.AutoField(primary_key=True)
    rfq_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='rfqs')
    contact_person = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    rfq_date = models.DateField()
    required_by_date = models.DateField()
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    status = models.CharField(max_length=20, choices=RFQ_STATUS, default='draft')
    notes = models.TextField(blank=True, null=True)
    attachment = models.FileField(upload_to='rfq_attachments/', blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='rfqs_created')
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.rfq_number:
            last_rfq = RFQ.objects.order_by('-created_date').first()
            if last_rfq:
                last_number = int(last_rfq.rfq_number.split('-')[-1])
                self.rfq_number = f"RFQ-{str(last_number + 1).zfill(5)}"
            else:
                self.rfq_number = "RFQ-00001"
        super().save(*args, **kwargs)
    
    @property
    def item_count(self):
        return self.items.count()
    
    @property
    def total_quantity(self):
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    def get_absolute_url(self):
        return reverse('rfq_detail', kwargs={'pk': self.pk})
    
    def can_create_quotation(self):
        return self.status in ['draft', 'sent'] and self.items.exists()
    
    def __str__(self):
        return self.rfq_number

class RFQItem(models.Model):
    ITEM_TYPE = (
        ('part', 'Part'),
        ('product', 'Product'),
    )
    
    item_id = models.AutoField(primary_key=True)
    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name='items')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE)
    component = models.ForeignKey(Component, on_delete=models.CASCADE, null=True, blank=True)
    bom = models.ForeignKey(BOMHeader, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    target_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, 
                                     validators=[MinValueValidator(Decimal('0.01'))])
    specifications = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        if self.component:
            return f"{self.rfq.rfq_number} - {self.component.part_number}"
        else:
            return f"{self.rfq.rfq_number} - {self.bom.name}"

class Quotation(models.Model):
    QUOTATION_STATUS = (
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    )
    
    quotation_id = models.AutoField(primary_key=True)
    quotation_number = models.CharField(max_length=50, unique=True)
    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, null=True, blank=True, related_name='rfq_quotations')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='customer_quotations')
    quotation_date = models.DateField()
    expiry_date = models.DateField()
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD') 
    status = models.CharField(max_length=20, choices=QUOTATION_STATUS, default='draft')
    payment_terms = models.CharField(max_length=100, default='Net 30')
    incoterms = models.CharField(max_length=50, blank=True, null=True)
    delivery_time = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='quotations_created')
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.quotation_number:
            last_quote = Quotation.objects.order_by('-created_date').first()
            if last_quote:
                last_number = int(last_quote.quotation_number.split('-')[-1])
                self.quotation_number = f"QT-{str(last_number + 1).zfill(5)}"
            else:
                self.quotation_number = "QT-00001"
        super().save(*args, **kwargs)

    @property
    def item_count(self):
        return self.items.count()
    
    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date() if self.expiry_date else False
    
    def get_absolute_url(self):
        return reverse('quotation_detail', kwargs={'pk': self.pk})
    
    def can_create_order(self):
        return self.status in ['sent', 'accepted'] and self.items.exists()
    
    def __str__(self):
        return self.quotation_number

from decimal import Decimal, ROUND_HALF_UP

class QuotationItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    rfq_item = models.ForeignKey(RFQItem, on_delete=models.SET_NULL, null=True, blank=True)
    item_type = models.CharField(max_length=20, choices=RFQItem.ITEM_TYPE)
    component = models.ForeignKey(Component, on_delete=models.CASCADE, null=True, blank=True)
    bom = models.ForeignKey(BOMHeader, on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField()
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        # Round to 2 decimals before saving
        self.line_total = (
            self.quantity * self.unit_price * (1 + self.tax_rate / 100)
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        super().save(*args, **kwargs)
        
        # Update quotation totals (rounded as well)
        quotation = self.quotation
        items = quotation.items.all()
        quotation.subtotal = sum(
            (item.quantity * item.unit_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            for item in items
        )
        quotation.tax_amount = sum(
            (item.quantity * item.unit_price * item.tax_rate / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            for item in items
        )
        quotation.total_amount = (quotation.subtotal + quotation.tax_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        quotation.save()
    
    def __str__(self):
        return f"{self.quotation.quotation_number} - Item"


class SalesOrder(models.Model):
    ORDER_STATUS = (
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    
    order_id = models.AutoField(primary_key=True)
    order_number = models.CharField(max_length=50, unique=True)
    quotation = models.ForeignKey(Quotation, on_delete=models.SET_NULL, null=True, blank=True, related_name='quotation_sales_orders')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='customer_sales_orders')
    customer_po_number = models.CharField(max_length=100)
    customer_po_file = models.FileField(upload_to='customer_po/', blank=True, null=True)
    order_date = models.DateField()
    delivery_date = models.DateField()
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='draft')
    payment_terms = models.CharField(max_length=100, default='Net 30')
    notes = models.TextField(blank=True, null=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='sales_orders_created')
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            last_order = SalesOrder.objects.order_by('-created_date').first()
            if last_order:
                last_number = int(last_order.order_number.split('-')[-1])
                self.order_number = f"SO-{str(last_number + 1).zfill(5)}"
            else:
                self.order_number = "SO-00001"
        super().save(*args, **kwargs)

    @property
    def item_count(self):
        return self.items.count()
    
    @property
    def progress_percentage(self):
        if self.status == 'delivered':
            return 100
        statuses = ['draft', 'confirmed', 'in_progress', 'shipped', 'delivered']
        try:
            return (statuses.index(self.status) / (len(statuses) - 1)) * 100
        except ValueError:
            return 0
    
    def get_absolute_url(self):
        return reverse('sales_order_detail', kwargs={'pk': self.pk})
    
    def __str__(self):
        return self.order_number

class SalesOrderItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    quotation_item = models.ForeignKey(QuotationItem, on_delete=models.SET_NULL, null=True, blank=True)
    item_type = models.CharField(max_length=20, choices=RFQItem.ITEM_TYPE)
    component = models.ForeignKey(Component, on_delete=models.CASCADE, null=True, blank=True)
    bom = models.ForeignKey(BOMHeader, on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField()
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price * (1 + self.tax_rate / 100)
        super().save(*args, **kwargs)
        
        # Update sales order totals
        order = self.sales_order
        items = order.items.all()
        order.subtotal = sum(item.quantity * item.unit_price for item in items)
        order.tax_amount = sum(item.quantity * item.unit_price * item.tax_rate / 100 for item in items)
        order.total_amount = order.subtotal + order.tax_amount
        order.save()
    
    def __str__(self):
        return f"{self.sales_order.order_number} - Item"

class Invoice(models.Model):
    INVOICE_STATUS = (
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    )
    
    invoice_id = models.AutoField(primary_key=True)
    invoice_number = models.CharField(max_length=50, unique=True)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='invoices')
    invoice_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=INVOICE_STATUS, default='draft')
    notes = models.TextField(blank=True, null=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='invoices_created')
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last_invoice = Invoice.objects.order_by('-created_date').first()
            if last_invoice:
                last_number = int(last_invoice.invoice_number.split('-')[-1])
                self.invoice_number = f"INV-{str(last_number + 1).zfill(5)}"
            else:
                self.invoice_number = "INV-00001"
        
        # Copy totals from sales order if not set
        if self.subtotal == 0 and self.sales_order:
            self.subtotal = self.sales_order.subtotal
            self.tax_amount = self.sales_order.tax_amount
            self.total_amount = self.sales_order.total_amount
            
        super().save(*args, **kwargs)

    @property
    def amount_due(self):
        return self.total_amount - self.amount_paid
    
    @property
    def is_overdue(self):
        return self.due_date < timezone.now().date() if self.due_date and self.status != 'paid' else False
    
    def get_absolute_url(self):
        return reverse('invoice_detail', kwargs={'pk': self.pk})
    
    def __str__(self):
        return self.invoice_number
    
    
class InvoiceItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    sales_order_item = models.ForeignKey(SalesOrderItem, on_delete=models.SET_NULL, null=True, blank=True)
    item_type = models.CharField(max_length=20, choices=RFQItem.ITEM_TYPE)
    component = models.ForeignKey(Component, on_delete=models.SET_NULL, null=True, blank=True)
    bom = models.ForeignKey(BOMHeader, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price * (1 + self.tax_rate / 100)
        super().save(*args, **kwargs)
        
        # Update invoice totals
        invoice = self.invoice
        items = invoice.items.all()
        invoice.subtotal = sum(item.quantity * item.unit_price for item in items)
        invoice.tax_amount = sum(item.quantity * item.unit_price * item.tax_rate / 100 for item in items)
        invoice.total_amount = invoice.subtotal + invoice.tax_amount
        invoice.save()
    
    def __str__(self):
        return f"{self.invoice.invoice_number} - Item"
    
# Purchase Models
class PurchaseRFQ(models.Model):
    RFQ_STATUS = (
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('received', 'Responses Received'),
        ('closed', 'Closed'),
    )
    
    rfq_id = models.AutoField(primary_key=True)
    rfq_number = models.CharField(max_length=50, unique=True)
    requisition = models.ForeignKey(PurchaseRequisition, on_delete=models.CASCADE, null=True, blank=True, related_name='purchase_rfqs')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=RFQ_STATUS, default='draft')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='purchase_rfqs_created')
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.rfq_number:
            last_rfq = PurchaseRFQ.objects.order_by('-created_date').first()
            if last_rfq:
                last_number = int(last_rfq.rfq_number.split('-')[-1])
                self.rfq_number = f"PRFQ-{str(last_number + 1).zfill(5)}"
            else:
                self.rfq_number = "PRFQ-00001"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.rfq_number

class PurchaseRFQItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    rfq = models.ForeignKey(PurchaseRFQ, on_delete=models.CASCADE, related_name='items')
    component = models.ForeignKey(Component, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    specifications = models.TextField(blank=True, null=True)
    required_date = models.DateField()
    
    def __str__(self):
        return f"{self.rfq.rfq_number} - {self.component.part_number}"

class PurchaseRFQSupplier(models.Model):
    rfq_supplier_id = models.AutoField(primary_key=True)
    rfq = models.ForeignKey(PurchaseRFQ, on_delete=models.CASCADE, related_name='suppliers')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    sent_date = models.DateTimeField(blank=True, null=True)
    response_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, default='pending')  # pending, responded, awarded
    
    class Meta:
        unique_together = ('rfq', 'supplier')
    
    def __str__(self):
        return f"{self.rfq.rfq_number} - {self.supplier.name}"

class SupplierResponse(models.Model):
    response_id = models.AutoField(primary_key=True)
    rfq_supplier = models.ForeignKey(PurchaseRFQSupplier, on_delete=models.CASCADE, related_name='responses')
    rfq_item = models.ForeignKey(PurchaseRFQItem, on_delete=models.CASCADE)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    lead_time_days = models.PositiveIntegerField()
    min_order_quantity = models.PositiveIntegerField(default=1)
    validity_days = models.PositiveIntegerField(default=30)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('rfq_supplier', 'rfq_item')
    
    def __str__(self):
        return f"{self.rfq_supplier} - {self.rfq_item.component.part_number}"

class PurchaseOrder(models.Model):
    PO_STATUS = (
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('partially_received', 'Partially Received'),
        ('fully_received', 'Fully Received'),
        ('cancelled', 'Cancelled'),
    )
    
    po_id = models.AutoField(primary_key=True)
    po_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    rfq = models.ForeignKey(PurchaseRFQ, on_delete=models.SET_NULL, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='supplier_purchase_orders')
    rfq = models.ForeignKey(PurchaseRFQ, on_delete=models.SET_NULL, null=True, blank=True, related_name='rfq_purchase_orders')
    order_date = models.DateField()
    expected_delivery_date = models.DateField()
    status = models.CharField(max_length=20, choices=PO_STATUS, default='draft')
    payment_terms = models.CharField(max_length=100, default='Net 30')
    notes = models.TextField(blank=True, null=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='purchase_orders_created')
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.po_number:
            last_po = PurchaseOrder.objects.order_by('-created_date').first()
            if last_po:
                last_number = int(last_po.po_number.split('-')[-1])
                self.po_number = f"PO-{str(last_number + 1).zfill(5)}"
            else:
                self.po_number = "PO-00001"
        super().save(*args, **kwargs)

    @property
    def received_percentage(self):
        if not self.items.exists():
            return 0
        total_ordered = self.items.aggregate(total=models.Sum('quantity'))['total'] or 0
        total_received = self.items.aggregate(total=models.Sum('received_quantity'))['total'] or 0
        return (total_received / total_ordered) * 100 if total_ordered > 0 else 0
    
    def get_absolute_url(self):
        return reverse('purchase_order_detail', kwargs={'pk': self.pk})
    
    def __str__(self):
        return self.po_number

class PurchaseOrderItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    component = models.ForeignKey(Component, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    received_quantity = models.PositiveIntegerField(default=0)
    
    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price * (1 + self.tax_rate / 100)
        super().save(*args, **kwargs)
        
        # Update purchase order totals
        po = self.purchase_order
        items = po.items.all()
        po.subtotal = sum(item.quantity * item.unit_price for item in items)
        po.tax_amount = sum(item.quantity * item.unit_price * item.tax_rate / 100 for item in items)
        po.total_amount = po.subtotal + po.tax_amount
        po.save()
    
    def __str__(self):
        return f"{self.purchase_order.po_number} - {self.component.part_number}"

class GoodsReceivedNote(models.Model):
    GRN_STATUS = (
        ('draft', 'Draft'),
        ('received', 'Received'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )
    
    grn_id = models.AutoField(primary_key=True)
    grn_number = models.CharField(max_length=50, unique=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='purchase_order_grns')
    received_date = models.DateField()
    status = models.CharField(max_length=20, choices=GRN_STATUS, default='draft')
    received_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='grns_received')
    verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='grns_verified')
    notes = models.TextField(blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.grn_number:
            last_grn = GoodsReceivedNote.objects.order_by('-created_date').first()
            if last_grn:
                last_number = int(last_grn.grn_number.split('-')[-1])
                self.grn_number = f"GRN-{str(last_number + 1).zfill(5)}"
            else:
                self.grn_number = "GRN-00001"
        super().save(*args, **kwargs)

    @property
    def can_verify(self):
        return self.status == 'received' and self.items.exists()
    
    def get_absolute_url(self):
        return reverse('grn_detail', kwargs={'pk': self.pk})
    
    def __str__(self):
        return self.grn_number

class GRNItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    grn = models.ForeignKey(GoodsReceivedNote, on_delete=models.CASCADE, related_name='items')
    po_item = models.ForeignKey(PurchaseOrderItem, on_delete=models.CASCADE)
    quantity_received = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    quantity_accepted = models.PositiveIntegerField(default=0)
    quality_status = models.CharField(max_length=20, default='pending')  # pending, accepted, rejected
    notes = models.TextField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        # Update the received quantity in the PO item
        if not self.quantity_accepted:
            self.quantity_accepted = self.quantity_received
            
        super().save(*args, **kwargs)
        
        # Update the PO item received quantity
        self.po_item.received_quantity = GRNItem.objects.filter(
            po_item=self.po_item
        ).aggregate(total=models.Sum('quantity_accepted'))['total'] or 0
        self.po_item.save()
        
        # Update the PO status based on received quantities
        po = self.po_item.purchase_order
        all_items = po.items.all()
        total_ordered = sum(item.quantity for item in all_items)
        total_received = sum(item.received_quantity for item in all_items)
        
        if total_received == 0:
            po.status = 'issued'
        elif total_received < total_ordered:
            po.status = 'partially_received'
        else:
            po.status = 'fully_received'
        po.save()
    
    def __str__(self):
        return f"{self.grn.grn_number} - {self.po_item.component.part_number}"

class SupplierInvoice(models.Model):
    INVOICE_STATUS = (
        ('draft', 'Draft'),
        ('received', 'Received'),
        ('verified', 'Verified'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    )
    
    invoice_id = models.AutoField(primary_key=True)
    invoice_number = models.CharField(max_length=100)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='invoices')
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, null=True, blank=True, related_name='purchase_order_invoices')
    grn = models.ForeignKey(GoodsReceivedNote, on_delete=models.CASCADE, null=True, blank=True, related_name='grn_invoices')
    invoice_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=INVOICE_STATUS, default='draft')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    invoice_file = models.FileField(upload_to='supplier_invoices/', blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='supplier_invoices_created')
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    @property
    def is_overdue(self):
        return self.due_date < timezone.now().date() if self.due_date and self.status != 'paid' else False
    
    def get_absolute_url(self):
        return reverse('supplier_invoice_detail', kwargs={'pk': self.pk})
    
    def __str__(self):
        return f"{self.invoice_number} - {self.supplier.name}"