from django.http import JsonResponse
from django.views import View
from django.core.serializers import serialize
import json
from .models import Component, Inventory, ComponentSupplier

class ComponentAPIView(View):
    def get(self, request, pk):
        try:
            component = Component.objects.get(pk=pk)
            
            # Get supplier information
            suppliers = []
            for cs in component.suppliers.all().select_related('supplier'):
                suppliers.append({
                    'id': cs.id,
                    'supplier_id': cs.supplier.id,
                    'supplier_name': cs.supplier.name,
                    'supplier_part_number': cs.supplier_part_number,
                    'cost': float(cs.cost),
                    'lead_time_days': cs.lead_time_days,
                    'is_approved': cs.is_approved,
                    'notes': cs.notes,
                })
            
            # Get inventory information
            inventory = []
            for inv in component.inventory.all().select_related('location'):
                inventory.append({
                    'id': inv.id,
                    'location_id': inv.location.id,
                    'location_name': inv.location.name,
                    'quantity_on_hand': inv.quantity_on_hand,
                    'quantity_allocated': inv.quantity_allocated,
                    'min_stock_level': inv.min_stock_level,
                    'last_updated': inv.last_updated.strftime("%Y-%m-%d %H:%M"),
                })
            
            # Get where used information
            where_used = []
            for item in component.bomitem_set.all().select_related('bom'):
                where_used.append({
                    'bom_id': item.bom.id,
                    'bom_name': item.bom.name,
                    'bom_revision': item.bom.revision,
                    'quantity': float(item.quantity),
                    'reference_designators': item.reference_designators,
                })
            
            # Prepare response data
            data = {
                'id': component.id,
                'part_number': component.part_number,
                'description': component.description,
                'category': component.category,
                'category_display': component.get_category_display(),
                'unit_of_measure': component.unit_of_measure,
                'material': component.material,
                'tolerance': component.tolerance,
                'finish': component.finish,
                'weight': float(component.weight) if component.weight else None,
                'thumbnail_url': component.thumbnail.url if component.thumbnail else None,
                'created_date': component.created_date.strftime("%Y-%m-%d %H:%M"),
                'last_modified': component.last_modified.strftime("%Y-%m-%d %H:%M"),
                'created_by': component.created_by.get_full_name() if component.created_by else None,
                'suppliers': suppliers,
                'inventory': inventory,
                'where_used': where_used,
            }
            
            return JsonResponse(data)
        except Component.DoesNotExist:
            return JsonResponse({'error': 'Component not found'}, status=404)