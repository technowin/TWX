# inventory/management/commands/backfill_transactions.py
from django.core.management.base import BaseCommand
from django.db import transaction
from BOM.models import InventoryHistory, InventoryTransaction
from datetime import timedelta

class Command(BaseCommand):
    help = 'Backfills InventoryTransaction from InventoryHistory'

    def handle(self, *args, **options):
        with transaction.atomic():
            count = 0
            for history in InventoryHistory.objects.all():
                # Create issue transactions (consumption)
                if history.quantity_allocated > 0:
                    InventoryTransaction.objects.create(
                        component=history.component,
                        quantity=history.quantity_allocated,
                        transaction_type='issue',
                        date=history.snapshot_date,
                        location=history.location,
                        reference=f'HISTORY-{history.id}'
                    )
                    count += 1
                
                # Create receipt transactions (restocking)
                if history.quantity_on_hand > 0:
                    InventoryTransaction.objects.create(
                        component=history.component,
                        quantity=history.quantity_on_hand,
                        transaction_type='receipt',
                        date=history.snapshot_date - timedelta(days=1),  # Assume received day before
                        location=history.location,
                        reference=f'HISTORY-{history.id}'
                    )
                    count += 1

            self.stdout.write(self.style.SUCCESS(f'Created {count} transaction records'))