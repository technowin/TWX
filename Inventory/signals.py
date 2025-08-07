# inventory/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StockEntry, InventoryAlert
from django.utils import timezone

@receiver(post_save, sender=StockEntry)
def check_stock_levels(sender, instance, **kwargs):
    product = instance.product
    location = instance.location
    
    # Check for low stock alerts
    current_stock = product.current_stock
    if current_stock <= product.min_stock_level:
        InventoryAlert.objects.update_or_create(
            product=product,
            warehouse=location.warehouse if location else None,
            location=location,
            alert_type='LOW_STOCK',
            defaults={
                'threshold': product.min_stock_level,
                'current_value': current_stock,
                'is_active': True,
                'acknowledged': False
            }
        )
    
    # Check for expiring items (if expiry date is set)
    if instance.expiry_date:
        days_to_expiry = (instance.expiry_date - timezone.now().date()).days
        if days_to_expiry <= 30:  # Alert for items expiring within 30 days
            InventoryAlert.objects.update_or_create(
                product=product,
                warehouse=location.warehouse if location else None,
                location=location,
                alert_type='EXPIRING',
                batch_number=instance.batch_number,
                defaults={
                    'threshold': days_to_expiry,
                    'current_value': instance.quantity,
                    'is_active': True,
                    'acknowledged': False
                }
            )