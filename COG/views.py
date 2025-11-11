from django.http import JsonResponse
from django.shortcuts import render

from BOM.models import *
from COG.models import *
from MachinePlanning.models import *

# Create your views here.
def bom_dropdown_view(request):
    """Simple view that renders the BOM dropdown"""
    bom_headers = BOMHeader.objects.all()
    
    context = {
        'bom_headers': bom_headers
    }
    return render(request, 'COG/cog_details.html', context)

def get_bom_details(request):
    """API endpoint to get BOM details using request.GET"""
    bom_id = request.GET.get('bom_id')
    
    if not bom_id:
        return JsonResponse({
            'success': False,
            'error': 'BOM ID is required'
        }, status=400)
    
    try:
        bom_header = BOMHeader.objects.get(id=bom_id)
        bom_items = BOMItem.objects.filter(bom=bom_header).select_related('component', 'supplier')
        
        # Prepare BOM items data
        items_data = []
        for item in bom_items:
            items_data.append({
                'sort_order': item.sort_order,
                'part_number': item.component.part_number if item.component else '',
                'description': item.component.description if item.component else '',
                'quantity': float(item.quantity),
                'ref_des': item.reference_designators,
                'purchase_type': item.component.purchase_type if item.component else '',
                'category': item.component.category if item.component else '',
                'unit': item.component.unit_of_measure if item.component else '',
                'price': float(item.price) if item.price else 0,
                'item_cost': float(item.cost) if item.cost else 0,
            })
        
        # Get Routing Cost Data
        routing_data = get_routing_cost_data(bom_header)
        other_costs_data = get_other_costs_data(bom_header, routing_data)

        
        response_data = {
            'success': True,
            'bom_header': {
                'name': bom_header.name,
                'description': bom_header.description,
                'revision': bom_header.revision,
                'total_material_cost': bom_header.total_material_cost,
                'wastage_value': bom_header.wastage_value,
                'overall_cost': bom_header.overall_cost,
                'status': bom_header.status,
            },
            'bom_items': items_data,
            'routing_data': routing_data,
            'other_costs_data': other_costs_data,
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

def get_routing_cost_data(bom_header):
    """Calculate routing cost data for BOM"""
    try:
        # Get routing master for this BOM - using component field instead of bom
        routing_masters = RoutingMaster.objects.filter(component=bom_header)
        routing_details_data = []
        total_routing_cost = 0
        
        for routing_master in routing_masters:
            # Get all routing details for this routing master
            routing_details = RoutingDetail.objects.filter(routing=routing_master)
            
            for detail in routing_details:

                machine_capacity = round(1 / detail.machine_capacity, 4)
                employee_capacity = round(1 / detail.employee_capacity, 4)

                # Calculate machine cost
                machine_cost_per_hour = calculate_machine_cost_per_unit(detail)
                
                # Calculate employee cost
                employee_cost_per_hour = calculate_employee_cost_per_unit(detail)
                
                # Total cost for this operation
                total_operation_cost = (machine_capacity * machine_cost_per_hour) + (employee_capacity * employee_cost_per_hour)
                total_routing_cost += total_operation_cost
                
                
                routing_details_data.append({
                    'sequence': detail.sequence,
                    'operation': detail.operation.name if detail.operation else '',
                    'work_center': detail.work_center.name if detail.work_center else '',
                    'machine_time_per_unit_hr': machine_capacity,
                    'employee_time_per_unit_hr': employee_capacity,
                    'machine_cost': round(machine_cost_per_hour, 2),
                    'employee_cost': round(employee_cost_per_hour, 2),
                    'total_operation_cost': round(total_operation_cost, 2)
                })
        
        return {
            'routing_details': routing_details_data,
            'total_routing_cost': round(total_routing_cost, 2)
        }
        
    except Exception as e:
        print(f"Error calculating routing cost: {str(e)}")
        return {
            'routing_details': [],
            'total_routing_cost': 0
        }

def calculate_machine_cost_per_unit(routing_detail):
    """Calculate average machine cost per hour for routing detail"""
    try:
        if not routing_detail.work_center:
            return 0
            
        total_machine_cost_per_hour = 0
        total_machines_count = 0
        
        # Get workstation IDs (comma separated) from work center
        workstation_ids = routing_detail.work_center.workstation_ids
        if workstation_ids:
            workstation_id_list = [int(id.strip()) for id in workstation_ids.split(',') if id.strip()]
            
            # Get all workstations
            workstations = WorkStations.objects.filter(id__in=workstation_id_list)
            
            for workstation in workstations:
                # Get machine IDs (comma separated) from workstation
                machine_ids = workstation.machine
                if machine_ids:
                    machine_id_list = [int(id.strip()) for id in machine_ids.split(',') if id.strip()]
                    total_machines_count += len(machine_id_list)
                    
                    # Get machine capabilities for cost calculation for all machines
                    machine_capabilities = MachineCapabilities.objects.filter(
                        machine__id__in=machine_id_list,
                        name__in=['Electricity', 'Consumables', 'Depreciation', 'Maintenance']
                    )
                    
                    # Calculate total cost for all machines
                    machine_costs = {}
                    for capability in machine_capabilities:
                        machine_id = capability.machine.id
                        if machine_id not in machine_costs:
                            machine_costs[machine_id] = 0
                        
                        try:
                            cost_value = float(capability.value) if capability.value else 0
                            machine_costs[machine_id] += cost_value
                        except (ValueError, TypeError):
                            continue
                    
                    # Add all machine costs to total
                    for machine_cost in machine_costs.values():
                        total_machine_cost_per_hour += machine_cost
        
        # Calculate average machine cost per hour
        if total_machines_count > 0:
            average_machine_cost_per_hour = total_machine_cost_per_hour / total_machines_count
            return average_machine_cost_per_hour
        else:
            return 0
            
    except Exception as e:
        print(f"Error calculating machine cost: {str(e)}")
        return 0

def calculate_employee_cost_per_unit(routing_detail):
    """Calculate employee cost per hour for routing detail"""
    try:
        if not routing_detail.operation:
            return 0
            
        # Get cost per hour from operation - return as is
        cost_per_hour = routing_detail.operation.cost_per_hour
        if cost_per_hour:
            try:
                return float(cost_per_hour)
            except (ValueError, TypeError):
                return 0
        return 0
            
    except Exception as e:
        print(f"Error calculating employee cost: {str(e)}")
        return 0

def get_other_costs_data(bom_header, routing_data):
    """Calculate other costs (Packaging, Overhead, Rent) for BOM"""
    try:
        # Calculate total production time per unit
        production_time_per_unit = calculate_production_time_per_unit(routing_data)
        
        # Get cost elements for this BOM
        cost_elements = CostElement.objects.filter(bom_header=bom_header)
        other_costs_details = []
        total_other_cost = 0
        
        for cost_element in cost_elements:
            # Get cost element values
            cost_values = CostElementValue.objects.filter(cost_key=cost_element)
            
            for cost_value in cost_values:
                calculated_cost = 0
                element_name = cost_element.name.lower()
                
                if 'rent' in element_name:
                    # Rent is stored as per month, convert to per hour then to per unit
                    rent_per_month = float(cost_value.value) if cost_value.value else 0
                    rent_per_hour = rent_per_month / (30 * 24)  # Assuming 30 days month, 24 hours per day
                    calculated_cost = rent_per_hour * production_time_per_unit
                    unit_info = 'per month'
                    
                else:
                    # Packaging, Overhead, etc. - stored as per hour
                    cost_per_hour = float(cost_value.value) if cost_value.value else 0
                    calculated_cost = cost_per_hour * production_time_per_unit
                    unit_info = 'per hour'
                
                other_costs_details.append({
                    'name': cost_element.name,
                    'value': float(cost_value.value) if cost_value.value else 0,
                    'unit': unit_info,
                    'calculated_cost': round(calculated_cost, 2)
                })
                
                total_other_cost += calculated_cost
        
        return {
            'production_time_per_unit': round(production_time_per_unit, 4),
            'other_costs_details': other_costs_details,
            'total_other_cost': round(total_other_cost, 2)
        }
        
    except Exception as e:
        print(f"Error calculating other costs: {str(e)}")
        return {
            'production_time_per_unit': 0,
            'other_costs_details': [],
            'total_other_cost': 0
        }
def calculate_production_time_per_unit(routing_data):
    """Calculate total production time per unit (in hours)"""
    try:
        total_machine_time = 0
        total_employee_time = 0
        
        for routing_detail in routing_data['routing_details']:
            # Sum all machine times per unit
            if routing_detail.get('machine_time_per_unit_hr'):
                try:
                    machine_time = float(routing_detail['machine_time_per_unit_hr'])
                    total_machine_time += machine_time
                except (ValueError, TypeError):
                    pass
            
            # Sum all employee times per unit
            if routing_detail.get('employee_time_per_unit_hr'):
                try:
                    employee_time = float(routing_detail['employee_time_per_unit_hr'])
                    total_employee_time += employee_time
                except (ValueError, TypeError):
                    pass
        
        # Take the bigger value (bottleneck)
        production_time_per_unit = max(total_machine_time, total_employee_time)
        return production_time_per_unit
        
    except Exception as e:
        print(f"Error calculating production time: {str(e)}")
        return 0