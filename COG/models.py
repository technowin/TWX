from django.db import models

from MachinePlanning.models import *
from BOM.models import *

# Create your models here.
class CostElement(models.Model):
    """Defines the name and unit for each cost element (like electricity, packaging, etc.)"""
    name = models.CharField(max_length=255, unique=True)
    unit_of_measure = models.CharField(max_length=50, blank=True, null=True)
    bom_header = models.ForeignKey(BOMHeader, on_delete=models.CASCADE, related_name='bom_cost_values')

    class Meta:
        db_table = 'cost_element'
        verbose_name = 'Cost Element'
        verbose_name_plural = 'Cost Element'

    def __str__(self):
        return f"{self.name} ({self.unit_of_measure})" if self.unit_of_measure else self.name


class CostElementValue(models.Model):
    """Stores the actual cost values for each BOM record, linked to a cost element key"""
    cost_key = models.ForeignKey(CostElement, on_delete=models.CASCADE, related_name='cost_values')
    value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='cost_values_created')
    updated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='cost_values_updated')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cost_element_value'
        verbose_name = 'Cost Element Value'
        verbose_name_plural = 'Cost Element Values'

    def __str__(self):
        return f"{self.cost_key.name}: {self.value}"

class COGMaster(models.Model):
    bom_header = models.ForeignKey(BOMHeader, on_delete=models.CASCADE, related_name='bom_cog_values')
    routing_cost = models.CharField(max_length=10)
    material_cost =models.CharField(max_length=10)
    routing_cost = models.CharField(max_length=10)
    other_cost = models.CharField(max_length=10,null=True,blank=True)
    total_prodcution_cost = models.CharField(max_length=10)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='cog_values_created')
    updated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='cog_values_updated')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.bom_header.name}: {self.total_prodcution_cost}"
    
    class Meta:
        db_table = 'cog_master'
    
class COGDetail(models.Model):
    cog = models.ForeignKey(COGMaster, on_delete=models.CASCADE, related_name='cog_detail')
    operation = models.ForeignKey(Operation,on_delete=models.CASCADE, related_name='cog_operation')
    workcenter = models.ForeignKey(WorkCenters, on_delete=models.CASCADE, related_name='cog_workcenter')
    workstation = models.CharField(max_length=10)
    machine =  models.CharField(max_length=10)
    employee =  models.CharField(max_length=10)
    machine_capacity = models.CharField(max_length=10)
    employee_capacity =  models.CharField(max_length=10)
    machine_cost = models.CharField(max_length=10)
    employee_cost = models.CharField(max_length=10)
    avg_value  = models.CharField(max_length=10)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='cog_detail_created')
    updated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='cog_detail_updated')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'cog_detail'