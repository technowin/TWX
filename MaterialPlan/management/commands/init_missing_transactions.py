# inventory/management/commands/init_missing_transactions.py
from django.core.management.base import BaseCommand
from BOM.models import Component, InventoryTransaction
from BOM.models import Inventory  # Add this import

class Command(BaseCommand):
    help = 'Creates initial transactions for components without history'

    def handle(self, *args, **options):
        # Get components with no transactions but current inventory
        components_to_init = Component.objects.filter(
            inventorytransaction__isnull=True,
            inventory__quantity_on_hand__gt=0
        ).distinct()

        created = 0
        for component in components_to_init:
            # Get current inventory level
            total_stock = Inventory.objects.filter(
                component=component
            ).aggregate(total=sum('quantity_on_hand'))['total'] or 0

            if total_stock > 0:
                InventoryTransaction.objects.create(
                    component=component,
                    quantity=total_stock,
                    transaction_type='adjustment',
                    reference='INITIAL_STOCK',
                    notes='Auto-generated initial transaction'
                )
                created += 1

        self.stdout.write(
            self.style.SUCCESS(f'Created {created} initial transactions')
        )