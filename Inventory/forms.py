# inventory/forms.py
from django import forms
from django.forms import ModelForm, inlineformset_factory
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from .models import *

class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            # Add form-control class to all widgets except checkboxes and radio buttons
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                field.widget.attrs['class'] = 'form-control'
            
            # Add form-select class to select elements
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            
            # Add form-check-input to checkboxes
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            
            # Add placeholder if it's a CharField and no placeholder exists
            if isinstance(field, forms.CharField) and not field.widget.attrs.get('placeholder'):
                field.widget.attrs['placeholder'] = field.label
            
            # Add floating labels for text inputs
            if isinstance(field.widget, (forms.TextInput, forms.NumberInput, forms.EmailInput, forms.DateInput)):
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'
            
            # Add specific handling for date fields
            if isinstance(field.widget, forms.DateInput):
                field.widget.attrs['class'] += ' datepicker'
                field.widget.attrs['type'] = 'date'
            
            # Add aria-describedby for help text
            if field.help_text:
                field.widget.attrs['aria-describedby'] = f"{field_name}Help"
            
            # Add is-invalid class if field has errors
            if field_name in self.errors:
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' is-invalid'

class CategoryForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'parent', 'description', 'image', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_active': _('Active'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit parent choices to avoid circular references
        if self.instance.pk:
            self.fields['parent'].queryset = Category.objects.exclude(
                pk=self.instance.pk
            ).exclude(
                parent__pk=self.instance.pk
            )

class ProductForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = Product
        fields = [
            'sku', 'upc', 'name', 'description', 'category', 'type',
            'cost_price', 'selling_price', 'weight', 'dimensions',
            'min_stock_level', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'upc': 'UPC/Barcode',
            'is_active': _('Active'),
        }
        help_texts = {
            'dimensions': _('Format: Length×Width×Height in cm (e.g., 10×5×2)'),
            'min_stock_level': _('Minimum quantity before low stock alerts are triggered'),
        }

    def clean_sku(self):
        sku = self.cleaned_data['sku']
        if not sku.isalnum():
            raise ValidationError(_('SKU can only contain letters and numbers.'))
        return sku.upper()

    def clean_selling_price(self):
        selling_price = self.cleaned_data['selling_price']
        cost_price = self.cleaned_data.get('cost_price', 0)
        
        if selling_price < cost_price:
            raise ValidationError(
                _('Selling price cannot be lower than cost price.')
            )
        return selling_price

class ProductImageForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text', 'is_featured', 'order']
        widgets = {
            'image': forms.FileInput(attrs={
                'accept': 'image/*',
                'class': 'form-control'
            }),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_featured': _('Featured Image'),
        }

class ProductVariantForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = ProductVariant
        fields = ['name', 'value', 'sku_suffix', 'additional_price', 'image']
        widgets = {
            'additional_price': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def clean_sku_suffix(self):
        sku_suffix = self.cleaned_data['sku_suffix']
        if sku_suffix and not sku_suffix.startswith('-'):
            return f"-{sku_suffix}"
        return sku_suffix

class WarehouseForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = Warehouse
        fields = [
            'code', 'name', 'type', 'address', 'contact_person',
            'contact_phone', 'contact_email', 'total_capacity', 'is_active'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'contact_email': forms.EmailInput(attrs={'placeholder': 'email@example.com'}),
        }
        labels = {
            'is_active': _('Active'),
        }

    def clean_code(self):
        code = self.cleaned_data['code']
        return code.upper()

class StorageLocationForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = StorageLocation
        fields = [
            'warehouse', 'code', 'name', 'type', 
            'max_weight', 'max_volume', 'notes', 'is_active'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_active': _('Active'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make warehouse field readonly if editing
        if self.instance and self.instance.pk:
            self.fields['warehouse'].disabled = True
            self.fields['warehouse'].widget.attrs['class'] = 'form-control bg-light'

    def clean_code(self):
        code = self.cleaned_data['code']
        warehouse = self.cleaned_data.get('warehouse') or self.instance.warehouse
        
        if not warehouse:
            return code
            
        # Check for duplicate code in the same warehouse
        qs = StorageLocation.objects.filter(warehouse=warehouse, code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            raise ValidationError(
                _('A location with this code already exists in this warehouse.')
            )
        
        return code.upper()

class StockEntryForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = StockEntry
        fields = [
            'product', 'location', 'quantity', 'entry_type', 'reference',
            'batch_number', 'expiry_date', 'notes'
        ]
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit location choices based on warehouse if warehouse is known
        if 'location' in self.fields and 'initial' in kwargs:
            warehouse_id = kwargs['initial'].get('warehouse')
            if warehouse_id:
                self.fields['location'].queryset = StorageLocation.objects.filter(
                    warehouse_id=warehouse_id
                )

class StockMovementForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = StockMovement
        fields = [
            'product', 'from_location', 'to_location', 'quantity',
            'movement_type', 'reference', 'notes'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        from_location = cleaned_data.get('from_location')
        to_location = cleaned_data.get('to_location')
        
        if not from_location and not to_location:
            raise ValidationError(
                _("At least one location (source or destination) must be specified.")
            )
        
        if from_location and to_location and from_location == to_location:
            raise ValidationError(
                _("Source and destination locations cannot be the same.")
            )
        
        # Check available stock if moving from a location
        if from_location:
            product = cleaned_data.get('product')
            quantity = cleaned_data.get('quantity', 0)
            
            if product and quantity > 0:
                total_stock = StockEntry.objects.filter(
                    product=product,
                    location=from_location
                ).aggregate(total=models.Sum('quantity'))['total'] or 0
                
                if quantity > total_stock:
                    raise ValidationError(
                        _("Not enough stock available at the source location. "
                          "Available: %(available)s")
                        % {'available': total_stock}
                    )
        
        return cleaned_data

class InventoryAlertForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = InventoryAlert
        fields = ['product', 'warehouse', 'location', 'alert_type', 'threshold', 'is_active']
        widgets = {
            'threshold': forms.NumberInput(attrs={'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_active': _('Active'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['location'].queryset = StorageLocation.objects.none()
        
        if 'warehouse' in self.data:
            try:
                warehouse_id = int(self.data.get('warehouse'))
                self.fields['location'].queryset = StorageLocation.objects.filter(
                    warehouse_id=warehouse_id
                ).order_by('code')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.warehouse:
            self.fields['location'].queryset = self.instance.warehouse.locations.all()

class BarcodeGenerateForm(BootstrapFormMixin, forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    variant = forms.ModelChoiceField(
        queryset=ProductVariant.objects.none(), 
        required=False,
        label="Variant (optional)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    barcode_format = forms.ChoiceField(
        choices=ProductBarcode.FORMAT_CHOICES,
        initial='CODE128',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_primary = forms.BooleanField(
        required=False,
        initial=True,
        label="Set as primary barcode",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'product' in self.data:
            try:
                product_id = int(self.data.get('product'))
                self.fields['variant'].queryset = ProductVariant.objects.filter(
                    product_id=product_id
                ).order_by('name', 'value')
            except (ValueError, TypeError):
                pass
        elif self.initial.get('product'):
            self.fields['variant'].queryset = ProductVariant.objects.filter(
                product=self.initial['product']
            ).order_by('name', 'value')

# Formset for product images
ProductImageFormSet = inlineformset_factory(
    Product, ProductImage, form=ProductImageForm,
    extra=1, can_delete=True, can_order=True,
    widgets={
        'DELETE': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'ORDER': forms.NumberInput(attrs={'class': 'form-control'}),
    }
)

# Formset for product variants
ProductVariantFormSet = inlineformset_factory(
    Product, ProductVariant, form=ProductVariantForm,
    extra=1, can_delete=True,
    widgets={
        'DELETE': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    }
)