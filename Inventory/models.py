# inventory/models/product.py
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from django.urls import reverse
from Account.models import CustomUser
from django.db.models.functions import Coalesce
from django.db.models import Sum, Value

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, 
                             null=True, blank=True, related_name='children')
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    slug = models.SlugField(max_length=150, unique=True, editable=False)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('category-detail', kwargs={'slug': self.slug})
    
    @property
    def has_children(self):
        return self.children.exists()

class Product(models.Model):
    TYPE_CHOICES = [
        ('SIMPLE', 'Simple Product'),
        ('VARIABLE', 'Variable Product'),
        ('BUNDLE', 'Product Bundle'),
    ]
    
    sku = models.CharField(max_length=50, unique=True, verbose_name="SKU")
    upc = models.CharField(max_length=30, unique=True, blank=True, null=True, verbose_name="UPC/Barcode")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True, editable=False)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='SIMPLE')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    weight = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)  # in kg
    dimensions = models.CharField(max_length=50, blank=True, help_text="LxWxH in cm")
    min_stock_level = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    def get_absolute_url(self):
        return reverse('product-detail', kwargs={'slug': self.slug})
    
    @property
    def current_stock(self):
        return self.stock_entries.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    @property
    def is_low_stock(self):
        return self.current_stock <= self.min_stock_level
    

    @property
    def current_stock(self):
        # This is the property that can be used in Python code
        return self.stock_entries.aggregate(
            total=Coalesce(Sum('quantity'), Value(0))
        )['total']
    
    @classmethod
    def with_current_stock(cls):
        # Use this when you need to query products with their stock
        return cls.objects.annotate(
            current_stock=Coalesce(Sum('stock_entries__quantity'), Value(0))
        )

    def get_stock_at_location(self, location):
        """
        Returns current stock quantity at specified location.
        Positive values = available stock, Zero/negative = out of stock
        """
        from django.db.models import Sum
        
        aggregates = self.stock_entries.filter(
            location=location
        ).aggregate(
            total_in=Sum('quantity', filter=models.Q(quantity__gt=0)),
            total_out=Sum('quantity', filter=models.Q(quantity__lt=0))
        )
        
        total_in = aggregates['total_in'] or 0
        total_out = aggregates['total_out'] or 0
        
        return total_in + total_out  # out is negative

    def get_available_locations(self):
        """
        Returns queryset of locations where this product has stock > 0
        """
        from django.db.models import Sum
        
        return StorageLocation.objects.filter(
            stock_entries__product=self
        ).annotate(
            total_in=Sum('stock_entries__quantity', filter=models.Q(stock_entries__quantity__gt=0)),
            total_out=Sum('stock_entries__quantity', filter=models.Q(stock_entries__quantity__lt=0))
        ).annotate(
            current_stock=models.F('total_in') + models.F('total_out')
        ).filter(
            current_stock__gt=0
        ).distinct()

    def get_stock_summary(self):
        """
        Returns summary of stock across all locations
        Format: {location_id: {'location': obj, 'quantity': int}, ...}
        """
        from collections import defaultdict
        
        summary = defaultdict(int)
        entries = self.stock_entries.select_related('location').all()
        
        for entry in entries:
            summary[entry.location] += entry.quantity
        
        return {
            'total': sum(summary.values()),
            'locations': [
                {'location': loc, 'quantity': qty} 
                for loc, qty in summary.items()
            ]
        }

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=100, blank=True)
    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"Image for {self.product.name}"

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=50)  # e.g., "Color", "Size"
    value = models.CharField(max_length=50)  # e.g., "Red", "XL"
    sku_suffix = models.CharField(max_length=10)  # e.g., "-RED", "-XL"
    additional_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    image = models.ForeignKey(ProductImage, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.name}: {self.value}"
    
    @property
    def full_sku(self):
        return f"{self.product.sku}{self.sku_suffix}"
    
    @property
    def final_price(self):
        return self.product.selling_price + self.additional_price
    


# inventory/models/warehouse.py
from django.db import models
from django.core.validators import MinValueValidator

class Warehouse(models.Model):
    WAREHOUSE_TYPES = [
        ('MAIN', 'Main Warehouse'),
        ('REGIONAL', 'Regional Warehouse'),
        ('RETAIL', 'Retail Store'),
        ('ONLINE', 'Online Fulfillment Center'),
    ]
    
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=WAREHOUSE_TYPES, default='MAIN')
    address = models.TextField()
    contact_person = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=20)
    contact_email = models.EmailField()
    total_capacity = models.DecimalField(max_digits=10, decimal_places=2, help_text="In cubic meters")
    used_capacity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @property
    def capacity_percentage(self):
        if self.total_capacity == 0:
            return 0
        return (self.used_capacity / self.total_capacity) * 100
    
    def update_capacity(self):
        # from .inventory import StockEntry
        total_volume = sum(
            entry.product.weight * entry.quantity 
            for entry in StockEntry.objects.filter(location__warehouse=self)
            if entry.product.weight
        )
        self.used_capacity = total_volume
        self.save()

class StorageLocation(models.Model):
    LOCATION_TYPES = [
        ('SHELF', 'Shelf'),
        ('BIN', 'Bin'),
        ('RACK', 'Rack'),
        ('PALLET', 'Pallet'),
        ('ROOM', 'Room'),
    ]
    
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='locations')
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=LOCATION_TYPES, default='SHELF')
    max_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_volume = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('warehouse', 'code')
        ordering = ['warehouse', 'code']
    
    def __str__(self):
        return f"{self.warehouse.code} - {self.code} ({self.name})"
    
    @property
    def current_weight(self):
        # from .Inventory import StockEntry
        return sum(
            entry.product.weight * entry.quantity 
            for entry in StockEntry.objects.filter(location=self)
            if entry.product.weight
        ) or 0
    
    @property
    def weight_percentage(self):
        if not self.max_weight:
            return 0
        return (self.current_weight / self.max_weight) * 100
    
    @property
    def current_volume(self):
        #from .inventory import StockEntry
        return sum(
            (entry.product.weight or 0) * entry.quantity 
            for entry in StockEntry.objects.filter(location=self)
        ) or 0
    

# inventory/models/inventory.py
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator

class StockEntry(models.Model):
    ENTRY_TYPES = [
        ('PURCHASE', 'Purchase'),
        ('TRANSFER_IN', 'Transfer In'),
        ('ADJUSTMENT', 'Adjustment'),
        ('RETURN', 'Customer Return'),
        ('PRODUCTION', 'Production'),
    ]
    
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='stock_entries')
    location = models.ForeignKey('StorageLocation', on_delete=models.CASCADE, related_name='stock_entries')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    entry_type = models.CharField(max_length=15, choices=ENTRY_TYPES)
    reference = models.CharField(max_length=100, blank=True)  # PO number, transfer ID, etc.
    batch_number = models.CharField(max_length=50, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    date_received = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Stock Entries"
        ordering = ['-date_received']
    
    def __str__(self):
        return f"{self.quantity} x {self.product} at {self.location}"

    @property
    def days_left(self):
        if not self.expiry_date:
            return None
        return (self.expiry_date - timezone.now().date()).days

class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('TRANSFER', 'Transfer'),
        ('SALES', 'Sales'),
        ('ADJUSTMENT', 'Adjustment'),
        ('DAMAGE', 'Damage'),
        ('LOSS', 'Loss'),
    ]
    
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='movements')
    from_location = models.ForeignKey('StorageLocation', on_delete=models.CASCADE, 
                                    related_name='outgoing_movements', null=True, blank=True)
    to_location = models.ForeignKey('StorageLocation', on_delete=models.CASCADE, 
                                  related_name='incoming_movements', null=True, blank=True)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    movement_type = models.CharField(max_length=15, choices=MOVEMENT_TYPES)
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    moved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    moved_at = models.DateTimeField(default=timezone.now)
    confirmed = models.BooleanField(default=False)
    confirmed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='confirmed_movements')
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-moved_at']
    
    def __str__(self):
        return f"{self.quantity} x {self.product} from {self.from_location} to {self.to_location}"
    
    def save(self, *args, **kwargs):
        if self.confirmed and not self.confirmed_at:
            self.confirmed_at = timezone.now()
        super().save(*args, **kwargs)
    
    def confirm_movement(self, user):
        if not self.confirmed:
            self.confirmed = True
            self.confirmed_by = user
            self.confirmed_at = timezone.now()
            self.save()
            # Update stock levels
            self.update_stock_levels()
    
    def update_stock_levels(self):
        if self.from_location:
            # Remove from source location
            StockEntry.objects.create(
                product=self.product,
                location=self.from_location,
                quantity=-self.quantity,
                entry_type='TRANSFER_OUT',
                reference=f"Movement {self.id}",
                created_by=self.moved_by
            )
        
        if self.to_location:
            # Add to destination location
            StockEntry.objects.create(
                product=self.product,
                location=self.to_location,
                quantity=self.quantity,
                entry_type='TRANSFER_IN',
                reference=f"Movement {self.id}",
                created_by=self.moved_by
            )

    

# inventory/models/inventory.py
class InventoryAlert(models.Model):
    ALERT_TYPES = [
        ('LOW_STOCK', 'Low Stock'),
        ('EXPIRING', 'Expiring Soon'),
        ('EXCESS', 'Excess Stock'),
        ('NON_MOVING', 'Non-Moving Stock'),
    ]
    
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='alerts')
    warehouse = models.ForeignKey('Warehouse', on_delete=models.CASCADE, null=True, blank=True)
    location = models.ForeignKey('StorageLocation', on_delete=models.CASCADE, null=True, blank=True)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    threshold = models.DecimalField(max_digits=10, decimal_places=2)
    current_value = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_alert_type_display()} alert for {self.product}"
    
    def acknowledge(self, user):
        self.acknowledged = True
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save()


# inventory/models/product.py
class ProductBarcode(models.Model):
    FORMAT_CHOICES = [
        ('CODE128', 'Code 128'),
        ('CODE39', 'Code 39'),
        ('EAN13', 'EAN-13'),
        ('UPC', 'UPC-A'),
        ('QR', 'QR Code'),
    ]
    
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='barcodes')
    variant = models.ForeignKey('ProductVariant', on_delete=models.SET_NULL, null=True, blank=True)
    barcode_format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='CODE128')
    barcode_data = models.CharField(max_length=50, unique=True)
    image = models.ImageField(upload_to='barcodes/', null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_primary', 'product']
    
    def __str__(self):
        return f"{self.barcode_format} - {self.barcode_data}"
    
    def save(self, *args, **kwargs):
        if not self.barcode_data:
            if self.variant:
                self.barcode_data = self.variant.full_sku
            else:
                self.barcode_data = self.product.sku
        super().save(*args, **kwargs)
        
        # Generate barcode image if not exists
        if not self.image:
            self.generate_barcode_image()
    
    def generate_barcode_image(self):
        import barcode
        from barcode.writer import ImageWriter
        from io import BytesIO
        from django.core.files import File
        
        barcode_class = barcode.get_barcode_class(self.barcode_format.lower())
        barcode_instance = barcode_class(self.barcode_data, writer=ImageWriter())
        
        buffer = BytesIO()
        barcode_instance.write(buffer)
        
        filename = f"{self.product.sku}_{self.barcode_format}.png"
        self.image.save(filename, File(buffer), save=False)
        self.save()