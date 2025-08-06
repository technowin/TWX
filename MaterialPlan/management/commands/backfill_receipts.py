# inventory/management/commands/backfill_receipts.py
from django.core.management.base import BaseCommand
from django.db.models import Q
from MaterialPlan.models import PurchaseRequisition
from BOM.models import  PurchaseReceipt
from datetime import timedelta

class Command(BaseCommand):
    help = 'Backfills PurchaseReceipt from completed PurchaseRequisitions'

    def handle(self, *args, **options):
        completed_reqs = PurchaseRequisition.objects.filter(
            Q(status='received') | Q(status='ordered'),
            expected_delivery_date__isnull=False
        )
        
        for req in completed_reqs:
            PurchaseReceipt.objects.get_or_create(
                requisition=req,
                defaults={
                    'actual_receipt_date': req.expected_delivery_date,
                    'quantity_received': req.quantity,
                    'accepted_by': req.created_by,
                    'notes': 'Auto-generated during backfill'
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created {completed_reqs.count()} receipt records'))