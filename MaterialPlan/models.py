# models.py
from datetime import timedelta
import uuid
from venv import logger
from django.db import models
from django.contrib.auth import get_user_model
from BOM.models import Component, BOMHeader, Supplier, ComponentSupplier, InventoryLocation, Inventory
from django.db.models import Sum

User = get_user_model()

class MaterialPlan(models.Model):
    PLAN_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('executed', 'Executed'),
        ('cancelled', 'Cancelled'),
    ]
    
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    sales_order_reference = models.CharField(max_length=100, blank=True, null=True)
    production_order = models.ForeignKey('ProductionOrder', on_delete=models.SET_NULL, null=True, blank=True)
    bom = models.ForeignKey(BOMHeader, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    status = models.CharField(max_length=20, choices=PLAN_STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_material_plans')
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)
    due_date = models.DateField()
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Material Plan"
        verbose_name_plural = "Material Plans"
    
    def __str__(self):
        return f"{self.name} - v{self.version} ({self.get_status_display()})"
    
    def calculate_requirements(self):
        """
        Explodes the BOM and calculates all material requirements for this plan.
        Handles multi-level BOMs recursively and considers inventory availability.
        """
        from django.db import transaction
        from BOM.models import BOMItem,Inventory

        # Clear existing items to avoid duplicates
        self.items.all().delete()

        def explode_bom(bom_id, level=0, multiplier=1, parent_item=None):
            """
            Recursively explodes a BOM and creates MaterialPlanItems
            :param bom_id: BOM_Header ID to explode
            :param level: Current BOM level (0 = top level)
            :param multiplier: Quantity multiplier from parent BOM
            :param parent_item: Parent MaterialPlanItem for tracking hierarchy
            """
            # Get all items in this BOM
            bom_items = BOMItem.objects.filter(bom_id=bom_id).select_related('component')

            for bom_item in bom_items:
                # Calculate total quantity needed (BOM quantity × production quantity × parent multiplier)
                required_qty = bom_item.quantity * self.quantity * multiplier

                # Get available inventory (sum across all locations)
                inventory_available = Inventory.objects.filter(
                    component=bom_item.component
                ).aggregate(
                    total=Sum('quantity_on_hand') - Sum('quantity_allocated')
                )['total'] or 0

                # Get preferred supplier (first approved supplier by cost)
                preferred_supplier = bom_item.component.componentsupplier_set.filter(
                    is_approved=True
                ).order_by('cost').first()

                # Calculate quantities needed
                to_be_purchased = max(0, required_qty - inventory_available) if bom_item.component.purchase_type == 'Purchased' else 0
                to_be_manufactured = required_qty if bom_item.component.purchase_type == 'Manufactured' else 0

                # Create MaterialPlanItem
                plan_item = MaterialPlanItem.objects.create(
                    plan=self,
                    component=bom_item.component,
                    quantity_required=required_qty,
                    quantity_available=inventory_available,
                    quantity_to_purchase=to_be_purchased,
                    quantity_to_produce=to_be_manufactured,
                    quantity_reserved=0,
                    required_date=self.due_date - timedelta(days=preferred_supplier.lead_time_days if preferred_supplier else 0),
                    lead_time_days=preferred_supplier.lead_time_days if preferred_supplier else 0,
                    supplier=preferred_supplier.supplier if preferred_supplier else None,
                    status='pending',
                    level=level,
                    parent_item=parent_item
                )

                # If component has its own BOM, explode it recursively
                if hasattr(bom_item.component, 'bom'):
                    explode_bom(
                        bom_item.component.bom.id,
                        level + 1,
                        bom_item.quantity,  # Pass the BOM line item quantity as multiplier
                        plan_item
                    )

        # Start the BOM explosion from the plan's BOM
        try:
            with transaction.atomic():
                explode_bom(self.bom.id)

                # Check for critical shortages and create alerts
                self.check_shortages()

        except Exception as e:
            # Log error and re-raise
            logger.error(f"Failed to calculate requirements for plan {self.id}: {str(e)}")
            raise

    def check_shortages(self):
        """
        Creates MaterialShortageAlert for any critical shortages in this plan
        """
        from datetime import date

        for item in self.items.all():
            if item.quantity_to_purchase > 0:
                # Calculate potential delay (today + lead time vs required date)
                lead_time_date = date.today() + timedelta(days=item.lead_time_days)
                potential_delay = max(0, (lead_time_date - item.required_date).days)

                if potential_delay > 0 or item.quantity_available < (item.quantity_required * 0.1):  # Less than 10% available
                    MaterialShortageAlert.objects.create(
                        plan=self,
                        component=item.component,
                        required_quantity=item.quantity_required,
                        available_quantity=item.quantity_available,
                        required_date=item.required_date,
                        potential_delay_days=potential_delay,
                        status='open'
                    )


class MaterialPlanItem(models.Model):
    ITEM_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reserved', 'Reserved'),
        ('partially_fulfilled', 'Partially Fulfilled'),
        ('fulfilled', 'Fulfilled'),
    ]
    
    
    plan = models.ForeignKey(MaterialPlan, on_delete=models.CASCADE, related_name='items')
    component = models.ForeignKey(Component, on_delete=models.PROTECT)
    quantity_required = models.DecimalField(max_digits=12, decimal_places=3)
    quantity_available = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    quantity_to_purchase = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    quantity_to_produce = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    quantity_reserved = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    required_date = models.DateField()
    lead_time_days = models.PositiveIntegerField(default=0)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['required_date']
        verbose_name = "Material Plan Item"
        verbose_name_plural = "Material Plan Items"
    
    def __str__(self):
        return f"{self.component.part_number} - {self.quantity_required} required"


class PurchaseRequisition(models.Model):
    REQUISITION_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('ordered', 'Ordered'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]
    
    
    plan = models.ForeignKey(MaterialPlan, on_delete=models.CASCADE, related_name='purchase_requisitions')
    plan_item = models.ForeignKey(MaterialPlanItem, on_delete=models.CASCADE, related_name='requisitions')
    component = models.ForeignKey(Component, on_delete=models.PROTECT)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4)
    required_by_date = models.DateField()
    expected_delivery_date = models.DateField()
    status = models.CharField(max_length=20, choices=REQUISITION_STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_requisitions')
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_requisitions')
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Purchase Requisition"
        verbose_name_plural = "Purchase Requisitions"
    
    def __str__(self):
        return f"PR-{self.id} for {self.component.part_number}"
    
    @property
    def total_cost(self):
        return self.quantity * self.unit_cost


class InventoryReservation(models.Model):
    
    plan = models.ForeignKey(MaterialPlan, on_delete=models.CASCADE, related_name='reservations')
    plan_item = models.ForeignKey(MaterialPlanItem, on_delete=models.CASCADE, related_name='reservations')
    inventory = models.ForeignKey(Inventory, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    reserved_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Inventory Reservation"
        verbose_name_plural = "Inventory Reservations"
    
    def __str__(self):
        return f"Reservation of {self.quantity} {self.inventory.component.unit_of_measure} for {self.plan}"


class ProductionOrder(models.Model):
    ORDER_STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    
    order_number = models.CharField(max_length=50, unique=True)
    bom = models.ForeignKey(BOMHeader, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='planned')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_production_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['start_date']
        verbose_name = "Production Order"
        verbose_name_plural = "Production Orders"
    
    def __str__(self):
        return f"PO-{self.order_number} - {self.bom.name}"


class MaterialShortageAlert(models.Model):
    ALERT_STATUS_CHOICES = [
        ('open', 'Open'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
    ]
    
    
    plan = models.ForeignKey(MaterialPlan, on_delete=models.CASCADE, related_name='alerts')
    component = models.ForeignKey(Component, on_delete=models.CASCADE)
    required_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    available_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    required_date = models.DateField()
    potential_delay_days = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=ALERT_STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolution_notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Material Shortage Alert"
        verbose_name_plural = "Material Shortage Alerts"
    
    def __str__(self):
        return f"Shortage alert for {self.component.part_number}"