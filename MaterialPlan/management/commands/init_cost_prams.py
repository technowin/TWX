# inventory/management/commands/init_cost_params.py
from django.core.management.base import BaseCommand
from BOM.models import Component, ComponentCostParameter

class Command(BaseCommand):
    help = 'Initializes cost parameters for all components'

    def handle(self, *args, **options):
        for component in Component.objects.all():
            ComponentCostParameter.objects.get_or_create(
                component=component,
                defaults={
                    'ordering_cost': 50.00,  # Default value
                    'holding_cost_pct': 25.00  # 25% annual carrying cost
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Initialized cost parameters for all components'))