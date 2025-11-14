from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.db.models import Sum
# from SalesPurchase.views import get_component_max_price

from Account.models import CustomUser

class Component(models.Model):
    CATEGORY_CHOICES = [
        ('Mechanical', 'Mechanical'),
        ('Electrical', 'Electrical'),
        ('Electronic', 'Electronic'),
        ('Sealing', 'Sealing'),
        ('Plastic', 'Plastic'),
        ('Metal', 'Metal'),
        ('Chemical', 'Chemical'),
        ('Structural', 'Structural'),
        ('Electro-Mechanical', 'Electro-Mechanical'),
        ('Other', 'Other'),
    ]
    PURCHASE_TYPE_CHOICES = [
        ('Inhouse', 'Inhouse'),
        ('Purchase', 'Purchase'),
        ('Outsource', 'Outsource'),
        ('Manufactured', 'Manufactured'),
    ]
    # ... existing fields ...
    purchase_type = models.CharField(max_length=100, choices=PURCHASE_TYPE_CHOICES, default='Purchase')
    part_number = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default='Mechanical')
    unit_of_measure = models.CharField(max_length=20, default='Each')
    material = models.CharField(max_length=100, blank=True)
    tolerance = models.CharField(max_length=50, blank=True)
    finish = models.CharField(max_length=50, blank=True)
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    thumbnail = models.ImageField(upload_to='component_thumbs/', null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_components')
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.part_number} - {self.description[:50]}"
    
    def get_absolute_url(self):
        return reverse('component_detail', kwargs={'pk': self.pk})

class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class ComponentSupplier(models.Model):
    component = models.ForeignKey(Component, on_delete=models.CASCADE, related_name='suppliers')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    supplier_part_number = models.CharField(max_length=50)
    lead_time_days = models.PositiveIntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    is_approved = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('component', 'supplier', 'supplier_part_number')
    
    def __str__(self):
        return f"{self.component} from {self.supplier}"

class InventoryLocation(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=10, unique=True)
    
    def __str__(self):
        return self.name

class Inventory(models.Model):
    component = models.ForeignKey(Component, on_delete=models.CASCADE, related_name='inventory')
    location = models.ForeignKey(InventoryLocation, on_delete=models.CASCADE)
    quantity_on_hand = models.PositiveIntegerField(default=0)
    quantity_allocated = models.PositiveIntegerField(default=0)
    min_stock_level = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('component', 'location')
    
    def __str__(self):
        return f"{self.component} at {self.location}"
    
    @property
    def available_quantity(self):
        return self.quantity_on_hand - self.quantity_allocated

#Manasi-31/7/25

class InventoryHistory(models.Model):
    component = models.ForeignKey('Component', on_delete=models.CASCADE, related_name='inventory_history')
    location = models.ForeignKey('InventoryLocation', on_delete=models.SET_NULL, null=True, blank=True)
    snapshot_date = models.DateField(default=timezone.now)
    quantity_on_hand = models.PositiveIntegerField()
    quantity_allocated = models.PositiveIntegerField()
    available_quantity = models.IntegerField()  # quantity_on_hand - quantity_allocated

    class Meta:
        unique_together = ('component', 'location', 'snapshot_date')
        ordering = ['component', 'snapshot_date']

    def __str__(self):
        return f"{self.component.part_number} - {self.snapshot_date}"
    

    #Manasi 1-8-25
class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('receipt', 'Receipt'),
        ('issue', 'Issue'), 
        ('adjustment', 'Adjustment'),
    ]
    
    component = models.ForeignKey('Component', on_delete=models.CASCADE)  # Uses existing model
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    date = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(max_length=100)  # PO#, MO#, etc.
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    location = models.ForeignKey('InventoryLocation', on_delete=models.CASCADE, null=True, blank=True)  # Uses existing model
    
    class Meta:
        indexes = [
            models.Index(fields=['component', 'date']),  # Speeds up demand analysis
        ]
    
    def __str__(self):
        return f"{self.transaction_type} of {self.quantity} {self.component.part_number}"
    


class MonthlyComponentDemand(models.Model):
    component = models.ForeignKey(
        Component,
        on_delete=models.CASCADE,
        to_field='part_number',
        db_column='component_id'
    )
    month = models.DateField()
    total_issued = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'BOM_monthlycomponentdemand'
        unique_together = ('component', 'month')

    def __str__(self):
        return f"{self.component.part_number} - {self.month} - {self.total_issued}"


    
class PurchaseReceipt(models.Model):
    requisition = models.ForeignKey(
        'MaterialPlan.PurchaseRequisition',  # Explicit app_label.ModelName reference
        on_delete=models.CASCADE,
        verbose_name='Requisition'
    )
    actual_receipt_date = models.DateTimeField()
    quantity_received = models.DecimalField(max_digits=12, decimal_places=3)
    accepted_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='Accepted By'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Purchase Receipts"

    @property
    def actual_lead_time(self):
        return (self.actual_receipt_date - self.requisition.created_at).days

class ComponentCostParameter(models.Model):
    component = models.OneToOneField('Component', on_delete=models.CASCADE)  # Uses existing model
    ordering_cost = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)  # Per-order cost
    holding_cost_pct = models.DecimalField(max_digits=5, decimal_places=2, default=25.00)  # Annual % of unit cost
    
    def __str__(self):
        return f"Cost params for {self.component.part_number}"

class BOMHeader(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Active', 'Active'),
        ('Obsolete', 'Obsolete'),
        ('Pending Approval', 'Pending Approval'),
        ('Approved', 'Approved'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    revision = models.CharField(max_length=10, default='1.0')
    total_material_cost = models.CharField(max_length=255, blank=True, null=True)
    wastage_value = models.IntegerField(null=True,blank=True)
    overall_cost = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=100, choices=STATUS_CHOICES, default='Draft')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_boms')
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    parent_bom = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_boms')
    
    def __str__(self):
        return f"{self.name}"
    
    def get_absolute_url(self):
        return reverse('bom_detail', kwargs={'pk': self.pk})
    
    @property
    def total_components(self):
        return self.items.count()
    
    @property
    def total_cost(self):
        return sum(item.extended_cost for item in self.items.all())

class BOMItem(models.Model):
    bom = models.ForeignKey(BOMHeader, on_delete=models.CASCADE, related_name='items')
    component = models.ForeignKey(Component, on_delete=models.CASCADE)
    supplier =models.ForeignKey(Supplier, on_delete=models.CASCADE,null=True,blank=True)
    price = models.DecimalField(null=True,blank=True,max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=10, decimal_places=2,null=True,blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    reference_designators = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    sort_order = models.CharField(max_length=20)  # Stores hierarchical position like "1", "1.1", "1.2.1"
    level = models.IntegerField(default=0)  # Depth in hierarchy (1 for top level, 2 for second level, etc.)
    position = models.IntegerField(default=0)
    class Meta:
        # ordering = ['sort_order']
        unique_together = ('bom', 'component', 'reference_designators')
    
    def __str__(self):
        return f"{self.quantity} x {self.component} in {self.bom}"
    
    # def save(self, *args, **kwargs):
    #     # Automatically set price and cost if not provided
    #     if not self.price or not self.cost:
    #         max_price = get_component_max_price(self.component)
    #         self.price = max_price
    #         self.cost = max_price
    #     super().save(*args, **kwargs)

    @property
    def extended_cost(self):
        # Get the lowest cost from approved suppliers
        supplier_info = self.component.suppliers.filter(is_approved=True).order_by('cost').first()
        if supplier_info:
            return self.quantity * supplier_info.cost
        return 0

class Document(models.Model):
    DOCUMENT_TYPES = [
        ('Datasheet', 'Datasheet'),
        ('Drawing', 'Drawing'),
        ('Instruction', 'Instruction'),
        ('Certificate', 'Certificate'),
        ('Other', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    document_type = models.CharField(max_length=100, choices=DOCUMENT_TYPES, default='Datasheet')
    file = models.FileField(upload_to='documents/')
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    uploaded_date = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)
    
    # Relationships
    component = models.ForeignKey(Component, on_delete=models.CASCADE, null=True, blank=True, related_name='documents')
    bom = models.ForeignKey(BOMHeader, on_delete=models.CASCADE, null=True, blank=True, related_name='documents')
    
    def __str__(self):
        return self.name

class BOMRevision(models.Model):
    bom = models.ForeignKey(BOMHeader, on_delete=models.CASCADE, related_name='revisions')
    revision = models.CharField(max_length=10)
    change_reason = models.TextField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    snapshot_data = models.JSONField()  # Stores the complete BOM structure at time of revision
    
    class Meta:
        unique_together = ('bom', 'revision')
        ordering = ['-created_date']
    
    def __str__(self):
        return f"{self.bom.name} - Rev {self.revision}"

class Comment(models.Model):
    bom = models.ForeignKey(BOMHeader, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    text = models.TextField()
    created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_date']
    
    def __str__(self):
        return f"Comment by {self.author} on {self.bom}"

class ApprovalRequest(models.Model):
    bom = models.ForeignKey(BOMHeader, on_delete=models.CASCADE, related_name='approval_requests')
    requested_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='requested_approvals')
    requested_date = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_requests')
    approved_date = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_requests')
    rejected_date = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-requested_date']
    
    def __str__(self):
        return f"Approval for {self.bom.name}"
    
    @property
    def status(self):
        if self.approved_by:
            return "Approved"
        elif self.rejected_by:
            return "Rejected"
        return "Pending"
    

# Add to your models.py

class StockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('receipt', 'Stock Receipt'),
        ('issue', 'Stock Issue'),
        ('adjustment', 'Stock Adjustment'),
        ('transfer', 'Stock Transfer'),
        ('allocation', 'Production Allocation'),
        ('deallocation', 'Production Deallocation'),
    ]
    
    SOURCE_TYPES = [
        ('purchase', 'Purchase Order'),
        ('production', 'Production Order'),
        ('adjustment', 'Manual Adjustment'),
        ('transfer', 'Location Transfer'),
        ('bom', 'BOM Allocation'),
    ]
    
    component = models.ForeignKey(Component, on_delete=models.CASCADE, related_name='stock_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES, blank=True)
    source_reference = models.CharField(max_length=100, blank=True)  # PO#, MO#, BOM#, etc.
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    location = models.ForeignKey(InventoryLocation, on_delete=models.CASCADE)
    related_location = models.ForeignKey(InventoryLocation, on_delete=models.CASCADE, null=True, blank=True, 
                                        related_name='related_transfers')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['component', 'created_date']),
            models.Index(fields=['source_type', 'source_reference']),
        ]
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.component.part_number} - {self.quantity}"
    
    def save(self, *args, **kwargs):
        # Update inventory levels when saving transaction
        super().save(*args, **kwargs)
        self.update_inventory_levels()
    
    # def update_inventory_levels(self):
    #     # Get or create inventory record
    #     inventory, created = Inventory.objects.get_or_create(
    #         component=self.component,
    #         location=self.location,
    #         defaults={
    #             'quantity_on_hand': 0,
    #             'quantity_allocated': 0,
    #             'min_stock_level': 0
    #         }
    #     )
        
    #     # Update based on transaction type
    #     if self.transaction_type == 'receipt':
    #         inventory.quantity_on_hand += self.quantity
    #     elif self.transaction_type == 'issue':
    #         inventory.quantity_on_hand -= self.quantity
    #     elif self.transaction_type == 'allocation':
    #         inventory.quantity_allocated += self.quantity
    #     elif self.transaction_type == 'deallocation':
    #         inventory.quantity_allocated -= self.quantity
    #     elif self.transaction_type == 'adjustment':
    #         inventory.quantity_on_hand = self.quantity  # Direct adjustment
        
    #     inventory.save()


class StockTake(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('adjusted', 'Adjusted'),
    ]
    
    location = models.ForeignKey(InventoryLocation, on_delete=models.CASCADE)
    conducted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='conducted_stocktakes')
    conducted_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-conducted_date']
    
    def __str__(self):
        return f"Stock Take - {self.location.name} - {self.conducted_date.strftime('%Y-%m-%d')}"
    
    @property
    def variance_value(self):
        total = 0
        for item in self.items.all():
            if item.variance != 0 and item.expected_unit_cost:
                total += abs(item.variance) * item.expected_unit_cost
        return total


class StockTakeItem(models.Model):
    stock_take = models.ForeignKey(StockTake, on_delete=models.CASCADE, related_name='items')
    component = models.ForeignKey(Component, on_delete=models.CASCADE)
    expected_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    counted_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    expected_unit_cost = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['stock_take', 'component']
    
    def __str__(self):
        return f"{self.component.part_number} - {self.stock_take}"
    
    @property
    def variance(self):
        return self.counted_quantity - self.expected_quantity
    
    @property
    def variance_percentage(self):
        if self.expected_quantity == 0:
            return 100 if self.counted_quantity > 0 else 0
        return (self.variance / self.expected_quantity) * 100


class ReorderRule(models.Model):
    COMPARISON_CHOICES = [
        ('lt', 'Less Than'),
        ('lte', 'Less Than or Equal'),
        ('eq', 'Equal'),
        ('gte', 'Greater Than or Equal'),
        ('gt', 'Greater Than'),
    ]
    
    component = models.ForeignKey(Component, on_delete=models.CASCADE, related_name='reorder_rules')
    location = models.ForeignKey(InventoryLocation, on_delete=models.CASCADE, null=True, blank=True)
    rule_type = models.CharField(max_length=20, choices=[
        ('min_max', 'Min-Max'),
        ('reorder_point', 'Reorder Point'),
        ('periodic', 'Periodic Review'),
    ], default='min_max')
    min_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    max_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    reorder_point = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    order_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    is_active = models.BooleanField(default=True)
    last_triggered = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['component', 'location']
    
    def __str__(self):
        location_str = f" at {self.location.name}" if self.location else ""
        return f"Reorder rule for {self.component.part_number}{location_str}"
    
    def check_stock_level(self):
        if self.location:
            inventory = Inventory.objects.filter(component=self.component, location=self.location).first()
        else:
            # Aggregate across all locations
            total_inventory = Inventory.objects.filter(component=self.component).aggregate(
                total_on_hand=Sum('quantity_on_hand'),
                total_allocated=Sum('quantity_allocated')
            )
            available = (total_inventory['total_on_hand'] or 0) - (total_inventory['total_allocated'] or 0)
        
        if self.rule_type == 'min_max' and inventory:
            return inventory.quantity_on_hand <= self.min_quantity
        elif self.rule_type == 'reorder_point' and inventory:
            return inventory.quantity_on_hand <= self.reorder_point
        
        return False
    
