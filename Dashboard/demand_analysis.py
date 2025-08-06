# services/demand_analysis.py
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from BOM.models import InventoryTransaction

def get_monthly_issued_components():
    return (
        InventoryTransaction.objects
        .filter(transaction_type='issue')
        .annotate(month=TruncMonth('date'))
        .values('component', 'month')
        .annotate(total_issued=Sum('quantity'))
        .order_by('component', 'month')
    )
