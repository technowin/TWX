from django.core.management.base import BaseCommand
from BOM.models import Inventory, InventoryHistory  # adjust if needed
from datetime import date

class Command(BaseCommand):
    help = "Takes daily snapshot of current inventory"

    def handle(self, *args, **kwargs):
        today = date.today()
        for inv in Inventory.objects.select_related('component', 'location'):
            InventoryHistory.objects.update_or_create(
                component=inv.component,
                location=inv.location,
                snapshot_date=today,
                defaults={
                    'quantity_on_hand': inv.quantity_on_hand,
                    'quantity_allocated': inv.quantity_allocated,
                    'available_quantity': inv.available_quantity,
                }
            )
        self.stdout.write(self.style.SUCCESS("Inventory snapshot saved for today."))
