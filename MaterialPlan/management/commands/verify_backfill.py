from django.utils import timezone
from datetime import timedelta
from BOM.models import Inventory
from django.core.management.base import BaseCommand
from BOM.models import Component
from BOM.models import PurchaseReceipt
from django.db.models import Count

class Command(BaseCommand):
    help = 'Verifies backfilled data integrity'

    def handle(self, *args, **options):
        self.stdout.write("=== Starting Data Verification ===")
        
        # 1. Check for components without transactions
        components_without_transactions = Component.objects.annotate(
            trans_count=Count('inventorytransaction')
        ).filter(trans_count=0)
        
        if components_without_transactions.exists():
            self.stdout.write(self.style.WARNING(
                f"\n{components_without_transactions.count()} components without transactions:"
            ))
            for comp in components_without_transactions[:10]:  # Show first 10 to avoid flooding
                self.stdout.write(f" - {comp.part_number}")
        else:
            self.stdout.write(self.style.SUCCESS(
                "\nAll components have transaction records"
            ))

        # 2. Check for receipts without linked requisitions
        receipts_without_req = PurchaseReceipt.objects.filter(
            requisition__isnull=True
        ).count()
        
        if receipts_without_req > 0:
            self.stdout.write(self.style.WARNING(
                f"\n{receipts_without_req} receipts without requisitions"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "\nAll receipts have valid requisitions"
            ))

        # 3. Check for components with inventory but no recent transactions
        stale_components = Component.objects.filter(
            inventory__quantity_on_hand__gt=0
        ).exclude(
            inventorytransaction__date__gte=timezone.now() - timedelta(days=30)
        ).distinct().count()
        
        if stale_components > 0:
            self.stdout.write(self.style.WARNING(
                f"\n{stale_components} components have inventory but no recent transactions"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "\nAll stocked components have recent transactions"
            ))

        self.stdout.write(self.style.SUCCESS("\nVerification complete!"))

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix detected issues where possible'
        )