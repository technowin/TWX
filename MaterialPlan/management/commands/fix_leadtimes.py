from django.core.management.base import BaseCommand
from MaterialPlan.models import PurchaseRequisition

class Command(BaseCommand):
    help = 'Populates requisition lead times from ComponentSupplier'

    def handle(self, *args, **options):
        updated = 0
        for req in PurchaseRequisition.objects.all():
            if not hasattr(req, 'lead_time_days') or req.lead_time_days is None:
                supplier = req.component.suppliers.first()  # Gets first approved supplier
                if supplier:
                    req.lead_time_days = supplier.lead_time_days
                    req.save()
                    updated += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Updated {updated} requisitions with lead times')
        )