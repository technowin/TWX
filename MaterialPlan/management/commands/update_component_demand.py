# management/commands/update_component_demand.py

from django.core.management.base import BaseCommand
from BOM.models import MonthlyComponentDemand
from Dashboard.demand_analysis import get_monthly_issued_components

class Command(BaseCommand):
    help = 'Update monthly component demand summary'

    def handle(self, *args, **options):
        summary = get_monthly_issued_components()
        for row in summary:
            MonthlyComponentDemand.objects.update_or_create(
                component_id=row['component'],
                month=row['month'],
                defaults={'total_issued': row['total_issued']}
            )
        self.stdout.write(self.style.SUCCESS("Monthly demand updated successfully."))
