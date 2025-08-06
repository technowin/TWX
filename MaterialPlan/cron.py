from django_cron import CronJobBase, Schedule
from datetime import date
from django.db.models import Sum
from BOM.models import Inventory, InventoryHistory

class SnapshotInventoryJob(CronJobBase):
    RUN_EVERY_MINS = 1440  # every 24 hours

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'MaterialPlan.snapshot_inventory_job'  # must be unique

    def do(self):
        # Aggregate live inventory data
        total_on_hand = Inventory.objects.aggregate(Sum('quantity_on_hand'))['quantity_on_hand__sum'] or 0
        total_allocated = Inventory.objects.aggregate(Sum('quantity_allocated'))['quantity_allocated__sum'] or 0
        available = total_on_hand - total_allocated

        # Save snapshot to InventoryHistory
        InventoryHistory.objects.create(
            location='Main Warehouse',
            snapshot_date=date.today(),
            quantity_on_hand=total_on_hand,
            quantity_allocated=total_allocated,
            available_quantity=available
        )
