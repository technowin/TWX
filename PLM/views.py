from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render

from BOM.models import Component, Inventory, InventoryLocation,BOMHeader
from MaterialPlan.models import ProductionOrder


def plm_index(request):
    # Fetch all production orders
    production_orders = ProductionOrder.objects.all().order_by('-created_at')
    
    context = {
        "production_orders": production_orders
    }
    return render(request, "PLM/index.html", context)


from django.utils.timezone import now

    
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponseBadRequest


def update_inventory(request):
    production_order_number = request.GET.get("po_order")
    bom_header_name = request.GET.get("bom_header")
    quantity = request.GET.get("quantity")

    if not production_order_number or not bom_header_name or not quantity:
        return HttpResponseBadRequest("Missing parameters")

    try:
        quantity = int(quantity)
    except ValueError:
        return HttpResponseBadRequest("Invalid quantity")

    # ✅ Update inventory
    update_inventory_from_action(bom_header_name, quantity, location_id=1)

    # ✅ Update ProductionOrder status = 8 for matching production order + bom component
    try:
        production_order = ProductionOrder.objects.get(order_number=production_order_number)
        bom_header = BOMHeader.objects.get(name=bom_header_name)

        # if relation exists in ProductionOrder → component (adjust field name accordingly)
        ProductionOrder.objects.filter(
            id=production_order.id,
            bom=bom_header
        ).update(order_status=8)

    except ProductionOrder.DoesNotExist:
        return HttpResponseBadRequest("Production order not found")
    except BOMHeader.DoesNotExist:
        return HttpResponseBadRequest("BOM header not found")

    return redirect("plm_index")

def update_inventory_from_action(bom_header_name, quantity, location_id=1):

    """
    Insert or update Inventory based on BOMHeader name (component name) and quantity.
    
    :param bom_header_name: BOM component name (string)
    :param quantity: Quantity to add/update
    :param location_id: Optional InventoryLocation ID (if multiple locations exist)
    """

    try:
        # Step 1: Get component by name (same as BOM header name)
        component = Component.objects.get(part_number=bom_header_name)

        # Step 2: Choose location
        if location_id:
            location = InventoryLocation.objects.get(id=location_id)
        else:
            # Default: first location
            location = InventoryLocation.objects.first()

        # Step 3: Find or create inventory row
        inventory, created = Inventory.objects.get_or_create(
            component=component,
            location=location,
            defaults={
                "quantity_on_hand": 0,
                "quantity_allocated": 0,
                "min_stock_level": quantity
            }
        )

        if not created:
            # Update existing row → add to min_stock_level
            inventory.min_stock_level = inventory.min_stock_level + quantity
            inventory.last_updated = now()
            inventory.save(update_fields=["min_stock_level", "last_updated"])

        return inventory

    except Component.DoesNotExist:
        raise ValueError(f"No Component found with name '{bom_header_name}'")
    
def generate_invoice(request):
    return
    





