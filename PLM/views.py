from django.shortcuts import render

from MaterialPlan.models import ProductionOrder


def plm_index(request):
    # Fetch all production orders
    production_orders = ProductionOrder.objects.all().order_by('-created_at')
    
    context = {
        "production_orders": production_orders
    }
    return render(request, "PLM/index.html", context)
