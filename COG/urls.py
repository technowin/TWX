

from django.urls import path
from COG.views import bom_dropdown_view, get_bom_details

app_name = 'cog'

urlpatterns = [

path('product_cog/', bom_dropdown_view, name='product_cog'),
path('get-bom-details/', get_bom_details, name='get_bom_details'),

]