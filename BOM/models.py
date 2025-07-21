from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.core.validators import MinValueValidator

from Account.models import CustomUser

class Component(models.Model):
    CATEGORY_CHOICES = [
        ('ME', 'Mechanical'),
        ('EL', 'Electrical'),
        ('PL', 'Plastic'),
        ('MT', 'Metal'),
        ('CH', 'Chemical'),
        ('OT', 'Other'),
    ]
    PURCHASE_TYPE_CHOICES = [
        ('IN', 'Inhouse'),
        ('PU', 'Purchase'),
        ('OS', 'Outsource'),
    ]
    # ... existing fields ...
    purchase_type = models.CharField(max_length=2, choices=PURCHASE_TYPE_CHOICES, default='PU')
    part_number = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    category = models.CharField(max_length=2, choices=CATEGORY_CHOICES, default='ME')
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

class BOMHeader(models.Model):
    STATUS_CHOICES = [
        ('DR', 'Draft'),
        ('AC', 'Active'),
        ('OB', 'Obsolete'),
        ('PE', 'Pending Approval'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    revision = models.CharField(max_length=10, default='1.0')
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default='DR')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_boms')
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    parent_bom = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_boms')
    
    def __str__(self):
        return f"{self.name} (Rev {self.revision})"
    
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
    
    @property
    def extended_cost(self):
        # Get the lowest cost from approved suppliers
        supplier_info = self.component.suppliers.filter(is_approved=True).order_by('cost').first()
        if supplier_info:
            return self.quantity * supplier_info.cost
        return 0

class Document(models.Model):
    DOCUMENT_TYPES = [
        ('DS', 'Datasheet'),
        ('DR', 'Drawing'),
        ('IN', 'Instruction'),
        ('CE', 'Certificate'),
        ('OT', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    document_type = models.CharField(max_length=2, choices=DOCUMENT_TYPES, default='DS')
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
    