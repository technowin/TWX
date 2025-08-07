# inventory/forms.py
from django import forms
from django.forms import ModelForm, inlineformset_factory
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from .models import *
from django.db.models import Q

class BootstrapFormMixin:
    """
    Bootstrap 5 form mixin that applies consistent styling and enhancements
    to all form fields.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            # Add form-control class to all non-checkbox/radio fields
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                field.widget.attrs['class'] = 'form-control'
                
                # Add is-invalid class if field has errors
                if field_name in self.errors:
                    field.widget.attrs['class'] += ' is-invalid'
            
            # Add specific classes for checkbox and radio inputs
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs['class'] = 'form-check-input'
            
            # Add placeholder if the field has a label
            if field.label:
                field.widget.attrs['placeholder'] = field.label
            
            # Add required attribute and asterisk to label
            if field.required:
                field.widget.attrs['required'] = 'required'
                field.label_suffix = ' *'
            
            # Add floating labels for appropriate fields
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect, forms.FileInput)):
                field.widget.attrs['class'] += ' form-control-lg'

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
        help_texts = {
            'parent': _('Select a parent category if this is a subcategory'),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        if Category.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_('A category with this name already exists.'))
        return name

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
            'cost_price': forms.NumberInput(attrs={'step': '0.01'}),
            'selling_price': forms.NumberInput(attrs={'step': '0.01'}),
            'weight': forms.NumberInput(attrs={'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'upc': 'UPC/Barcode',
            'is_active': _('Active'),
        }
        help_texts = {
            'sku': _('Stock Keeping Unit - unique identifier for your product'),
            'upc': _('Universal Product Code or barcode number'),
            'min_stock_level': _('Minimum quantity before inventory alerts are triggered'),
        }

    def clean(self):
        cleaned_data = super().clean()
        cost_price = cleaned_data.get('cost_price')
        selling_price = cleaned_data.get('selling_price')
        
        if cost_price and selling_price and selling_price < cost_price:
            self.add_error('selling_price', 
                         _('Selling price cannot be less than cost price'))
        
        return cleaned_data

class ProductImageForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text', 'is_featured', 'order']
        widgets = {
            'image': forms.FileInput(attrs={
                'accept': 'image/*',
                'class': 'form-control',
            }),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'min': '0'}),
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
            'image': forms.FileInput(attrs={'accept': 'image/*'}),
        }

    def clean_sku_suffix(self):
        sku_suffix = self.cleaned_data['sku_suffix']
        if sku_suffix and not sku_suffix.isalnum():
            raise ValidationError(_('SKU suffix can only contain letters and numbers'))
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
            'contact_email': forms.EmailInput(),
            'contact_phone': forms.TextInput(attrs={'pattern': '[0-9()+ -]*'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_active': _('Active'),
        }

class StorageLocationForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = StorageLocation
        fields = [
            'warehouse', 'code', 'name', 'type', 
            'max_weight', 'max_volume', 'notes', 'is_active'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'max_weight': forms.NumberInput(attrs={'step': '0.01'}),
            'max_volume': forms.NumberInput(attrs={'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_active': _('Active'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['warehouse'].disabled = True
            self.fields['warehouse'].widget.attrs['class'] = 'form-control-plaintext'

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
            'quantity': forms.NumberInput(attrs={'min': '1'}),
        }
        help_texts = {
            'batch_number': _('Optional batch or lot number for tracking'),
            'expiry_date': _('Leave blank if product does not expire'),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity <= 0:
            raise ValidationError(_('Quantity must be greater than zero'))
        return quantity

class StockMovementForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = StockMovement
        fields = [
            'product', 'from_location', 'to_location', 'quantity',
            'movement_type', 'reference', 'notes'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={
                'min': '1',
                'class': 'form-control',
                'placeholder': _('Quantity to move')
            }),
            'movement_type': forms.Select(attrs={'class': 'form-select'}),
            'reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Reference number')
            }),
        }
        labels = {
            'from_location': _('Source Location'),
            'to_location': _('Destination Location'),
        }
        help_texts = {
            'quantity': _('Enter the quantity to move between locations'),
            'reference': _('Optional reference number for tracking'),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set querysets based on user permissions if needed
        if user and not user.is_superuser:
            # Example: Filter locations accessible to user
            pass
            
        # Add Bootstrap classes to remaining fields
        self.fields['product'].widget.attrs.update({'class': 'form-select'})
        self.fields['from_location'].widget.attrs.update({'class': 'form-select'})
        self.fields['to_location'].widget.attrs.update({'class': 'form-select'})
        
        # Dynamic location filtering
        if 'warehouse' in self.data:
            try:
                warehouse_id = int(self.data.get('warehouse'))
                self.fields['from_location'].queryset = StorageLocation.objects.filter(
                    warehouse_id=warehouse_id, is_active=True
                ).order_by('name')
                self.fields['to_location'].queryset = StorageLocation.objects.filter(
                    warehouse_id=warehouse_id, is_active=True
                ).order_by('name')
            except (ValueError, TypeError):
                pass

    def clean(self):
        cleaned_data = super().clean()
        from_location = cleaned_data.get('from_location')
        to_location = cleaned_data.get('to_location')
        quantity = cleaned_data.get('quantity')
        product = cleaned_data.get('product')
        movement_type = cleaned_data.get('movement_type')
        
        # Basic validation
        if not from_location and not to_location:
            raise ValidationError(_("At least one location must be specified."))
        
        if from_location and to_location and from_location == to_location:
            raise ValidationError(_("Source and destination cannot be the same."))
        
        # Stock availability check for outgoing movements
        if from_location and product and quantity:
            current_stock = product.get_stock_at_location(from_location)
            if current_stock < quantity:
                self.add_error(
                    'quantity',
                    _("Insufficient stock. Available: %(available)s") % {
                        'available': current_stock
                    }
                )
        
        # Additional business rule validation
        if movement_type == 'SALES' and not from_location:
            self.add_error('from_location', _("Source location required for sales movements."))
        
        if movement_type == 'TRANSFER' and (not from_location or not to_location):
            self.add_error(None, _("Both locations required for transfers."))
        
        return cleaned_data

class InventoryAlertForm(BootstrapFormMixin, ModelForm):
    class Meta:
        model = InventoryAlert
        fields = ['product', 'warehouse', 'location', 'alert_type', 'threshold', 'is_active']
        widgets = {
            'threshold': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
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
                ).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.warehouse:
            self.fields['location'].queryset = self.instance.warehouse.locations.all().order_by('name')

    def clean_threshold(self):
        threshold = self.cleaned_data['threshold']
        if threshold < 0:
            raise ValidationError(_("Threshold cannot be negative"))
        return threshold

class BarcodeGenerateForm(BootstrapFormMixin, forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        label=_("Product"),
        help_text=_("Select the product for barcode generation")
    )
    variant = forms.ModelChoiceField(
        queryset=ProductVariant.objects.none(), 
        required=False,
        label=_("Variant"),
        help_text=_("Optional: Select a specific variant")
    )
    barcode_format = forms.ChoiceField(
        choices=ProductBarcode.FORMAT_CHOICES,
        initial='CODE128',
        label=_("Barcode Format"),
        help_text=_("Select the barcode symbology")
    )
    is_primary = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Set as primary barcode"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'product' in self.data:
            try:
                product_id = int(self.data.get('product'))
                self.fields['variant'].queryset = ProductVariant.objects.filter(
                    product_id=product_id
                ).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.initial.get('product'):
            self.fields['variant'].queryset = ProductVariant.objects.filter(
                product=self.initial['product']
            ).order_by('name')

# Formsets with Bootstrap styling
class BaseFormSet(forms.BaseFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for form in self.forms:
            form.empty_permitted = False

ProductImageFormSet = inlineformset_factory(
    Product, ProductImage, form=ProductImageForm,
    extra=1, can_delete=True, can_order=True,
    formset=BaseFormSet
)

ProductVariantFormSet = inlineformset_factory(
    Product, ProductVariant, form=ProductVariantForm,
    extra=1, can_delete=True,
    formset=BaseFormSet
)

class ProductSearchForm(BootstrapFormMixin, forms.Form):
    q = forms.CharField(
        required=False,
        label=_('Search'),
        widget=forms.TextInput(attrs={
            'placeholder': _('Search by name, SKU, UPC...'),
            'autocomplete': 'off'
        })
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        label=_('Category')
    )
    in_stock = forms.BooleanField(
        required=False,
        label=_('In stock only'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    min_price = forms.DecimalField(
        required=False,
        label=_('Min price'),
        widget=forms.NumberInput(attrs={'step': '0.01'})
    )
    max_price = forms.DecimalField(
        required=False,
        label=_('Max price'),
        widget=forms.NumberInput(attrs={'step': '0.01'})
    )

    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get('min_price')
        max_price = cleaned_data.get('max_price')
        
        if min_price and max_price and min_price > max_price:
            self.add_error('max_price', _('Max price must be greater than min price'))
        
        return cleaned_data

class StockFilterForm(BootstrapFormMixin, forms.Form):
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        required=False,
        label=_('Warehouse')
    )
    location = forms.ModelChoiceField(
        queryset=StorageLocation.objects.filter(is_active=True),
        required=False,
        label=_('Location')
    )
    low_stock = forms.BooleanField(
        required=False,
        label=_('Show low stock only'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    out_of_stock = forms.BooleanField(
        required=False,
        label=_('Show out of stock items'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'warehouse' in self.data:
            try:
                warehouse_id = int(self.data.get('warehouse'))
                self.fields['location'].queryset = StorageLocation.objects.filter(
                    warehouse_id=warehouse_id, is_active=True
                )
            except (ValueError, TypeError):
                pass