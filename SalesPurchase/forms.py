from django import forms
from .models import *
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

# Base form class for consistent styling
class BootstrapForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if field.widget.attrs.get('class'):
                if 'form-control' not in field.widget.attrs['class']:
                    field.widget.attrs['class'] += ' form-control'
                # if 'form-select' not in field.widget.attrs['class']:
                #     field.widget.attrs['class'] += ' form-select'
            else:
                if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                    field.widget.attrs['class'] = 'form-select'
                elif isinstance(field.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                    field.widget.attrs['class'] = 'form-check-input'
                elif not isinstance(field.widget, forms.FileInput):
                    field.widget.attrs['class'] = 'form-control'
            
            # Add placeholder if it's a text input and has a label
            if (isinstance(field.widget, (forms.TextInput, forms.Textarea, forms.NumberInput)) and 
                field.label and not field.widget.attrs.get('placeholder')):
                field.widget.attrs['placeholder'] = f'Enter {field.label.lower()}'

# Required inline formset
class RequiredInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make first form required
        if self.forms and not self.forms[0].has_changed():
            self.forms[0].empty_permitted = False

# Customer Forms
class CustomerForm(BootstrapForm):
    class Meta:
        model = Customer
        fields = '__all__'
        exclude = ['customer_id', 'created_by', 'created_date', 'last_modified']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and Customer.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("A customer with this email already exists.")
        return email

class CustomerPricingForm(BootstrapForm):
    class Meta:
        model = CustomerPricing
        fields = '__all__'
        exclude = ['pricing_id', 'created_by', 'created_date']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'component': forms.Select(attrs={'class': 'form-select'}),
            'bom': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'effective_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'min_order_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        component = cleaned_data.get('component')
        bom = cleaned_data.get('bom')
        effective_date = cleaned_data.get('effective_date')
        expiry_date = cleaned_data.get('expiry_date')
        price = cleaned_data.get('price')

        # Validate that either component or BOM is selected, but not both
        if not component and not bom:
            raise ValidationError("Either component or BOM must be specified.")

        if component and bom:
            raise ValidationError("Only one of component or BOM can be specified, not both.")

        # Validate price
        if price is not None and price <= 0:
            raise ValidationError("Price must be greater than zero.")

        # Validate date ranges
        if effective_date and effective_date < timezone.now().date():
            raise ValidationError("Effective date cannot be in the past.")

        if expiry_date and effective_date and expiry_date <= effective_date:
            raise ValidationError("Expiry date must be after effective date.")

        return cleaned_data

# Sales Module Forms
class RFQForm(BootstrapForm):
    class Meta:
        model = RFQ
        fields = '__all__'
        exclude = ['rfq_id', 'rfq_number', 'created_by', 'created_date', 'last_modified']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'rfq_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'required_by_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        rfq_date = cleaned_data.get('rfq_date')
        required_by_date = cleaned_data.get('required_by_date')

        if rfq_date and required_by_date:
            if required_by_date < rfq_date:
                # raise ValidationError("Required by date cannot be before RFQ date.")
                self.add_error('required_by_date', "Required by date cannot be before RFQ date.")

            elif required_by_date < timezone.now().date():
                # raise ValidationError("Required by date cannot be in the past.")
                self.add_error('required_by_date', "Required by date cannot be in the past.")

        return cleaned_data

class RFQItemForm(BootstrapForm):
    class Meta:
        model = RFQItem
        fields = '__all__'
        exclude = ['item_id']
        widgets = {
            'rfq': forms.HiddenInput(),
            'item_type': forms.Select(attrs={'class': 'form-select item-type-select'}),
            'component': forms.Select(attrs={'class': 'form-select component-select'}),
            'bom': forms.Select(attrs={'class': 'form-select bom-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'target_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'specifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        return quantity
    
    def clean_target_price(self):
        target_price = self.cleaned_data.get('target_price')
        if target_price is not None and target_price < 0:
            raise ValidationError("Target price cannot be negative.")
        return target_price

RFQItemFormSet = inlineformset_factory(
    RFQ, RFQItem, form=RFQItemForm,
    extra=1, can_delete=True, can_order=False,
    formset=RequiredInlineFormSet
)

class QuotationForm(BootstrapForm):
    class Meta:
        model = Quotation
        fields = '__all__'
        exclude = ['quotation_id', 'quotation_number', 'subtotal', 'tax_amount', 'total_amount', 'created_by', 'created_date', 'last_modified']
        widgets = {
            'rfq': forms.Select(attrs={'class': 'form-select'}),
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'quotation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control'}),
            'incoterms': forms.TextInput(attrs={'class': 'form-control'}),
            'delivery_time': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        quotation_date = cleaned_data.get('quotation_date')
        expiry_date = cleaned_data.get('expiry_date')
        
        if quotation_date and expiry_date:
            if expiry_date < quotation_date:
                raise ValidationError("Expiry date cannot be before quotation date.")
            
            if expiry_date < timezone.now().date():
                raise ValidationError("Expiry date cannot be in the past.")
        
        return cleaned_data

class QuotationItemForm(BootstrapForm):
    class Meta:
        model = QuotationItem
        fields = '__all__'
        exclude = ['item_id']
        widgets = {
            'quotation': forms.HiddenInput(),
            'rfq_item': forms.HiddenInput(),
            'item_type': forms.Select(attrs={'class': 'form-select item-type-select'}),
            'component': forms.Select(attrs={'class': 'form-select component-select'}),
            'bom': forms.Select(attrs={'class': 'form-select bom-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
        }
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        return quantity
    
    def clean_unit_price(self):
        unit_price = self.cleaned_data.get('unit_price')
        if unit_price <= 0:
            raise ValidationError("Unit price must be greater than zero.")
        return unit_price
    
    def clean_tax_rate(self):
        tax_rate = self.cleaned_data.get('tax_rate')
        if tax_rate < 0:
            raise ValidationError("Tax rate cannot be negative.")
        if tax_rate > 100:
            raise ValidationError("Tax rate cannot exceed 100%.")
        return tax_rate

QuotationItemFormSet = inlineformset_factory(
    Quotation, QuotationItem, form=QuotationItemForm,
    extra=1, can_delete=True, can_order=False,
    formset=RequiredInlineFormSet
)

class SalesOrderForm(BootstrapForm):
    class Meta:
        model = SalesOrder
        fields = '__all__'
        exclude = ['order_id', 'order_number', 'subtotal', 'tax_amount', 'total_amount', 'created_by', 'created_date', 'last_modified']
        widgets = {
            'quotation': forms.Select(attrs={'class': 'form-select'}),
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'customer_po_number': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_po_file': forms.FileInput(attrs={'class': 'form-control'}),
            'order_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        order_date = cleaned_data.get('order_date')
        delivery_date = cleaned_data.get('delivery_date')
        
        if order_date and delivery_date:
            if delivery_date < order_date:
                raise ValidationError("Delivery date cannot be before order date.")
            
            if delivery_date < timezone.now().date():
                raise ValidationError("Delivery date cannot be in the past.")
        
        return cleaned_data

class SalesOrderItemForm(BootstrapForm):
    class Meta:
        model = SalesOrderItem
        fields = '__all__'
        exclude = ['item_id', 'line_total']
        widgets = {
            'sales_order': forms.HiddenInput(),
            'quotation_item': forms.HiddenInput(),
            'item_type': forms.Select(attrs={'class': 'form-select item-type-select'}),
            'component': forms.Select(attrs={'class': 'form-select component-select'}),
            'bom': forms.Select(attrs={'class': 'form-select bom-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
        }
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        return quantity
    
    def clean_unit_price(self):
        unit_price = self.cleaned_data.get('unit_price')
        if unit_price <= 0:
            raise ValidationError("Unit price must be greater than zero.")
        return unit_price
    
    def clean_tax_rate(self):
        tax_rate = self.cleaned_data.get('tax_rate')
        if tax_rate < 0:
            raise ValidationError("Tax rate cannot be negative.")
        if tax_rate > 100:
            raise ValidationError("Tax rate cannot exceed 100%.")
        return tax_rate

SalesOrderItemFormSet = inlineformset_factory(
    SalesOrder, SalesOrderItem, form=SalesOrderItemForm,
    extra=1, can_delete=True, can_order=False,
    formset=RequiredInlineFormSet
)

class InvoiceForm(BootstrapForm):
    class Meta:
        model = Invoice
        fields = '__all__'
        exclude = ['invoice_id', 'invoice_number', 'subtotal', 'tax_amount', 'total_amount', 'created_by', 'created_date', 'last_modified']
        widgets = {
            'sales_order': forms.Select(attrs={'class': 'form-select'}),
            'invoice_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        invoice_date = cleaned_data.get('invoice_date')
        due_date = cleaned_data.get('due_date')
        amount_paid = cleaned_data.get('amount_paid', 0)
        total_amount = cleaned_data.get('total_amount', 0)
        
        if invoice_date and due_date:
            if due_date < invoice_date:
                raise ValidationError("Due date cannot be before invoice date.")
            
            if due_date < timezone.now().date():
                raise ValidationError("Due date cannot be in the past.")
        
        if amount_paid > total_amount:
            raise ValidationError("Amount paid cannot exceed total amount.")
        
        return cleaned_data
    
    def clean_amount_paid(self):
        amount_paid = self.cleaned_data.get('amount_paid', 0)
        if amount_paid < 0:
            raise ValidationError("Amount paid cannot be negative.")
        return amount_paid

from django.forms import inlineformset_factory

class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['sales_order_item', 'item_type', 'component', 'bom', 'description', 
                 'quantity', 'unit_price', 'tax_rate', 'line_total']
        widgets = {
            'sales_order_item': forms.HiddenInput(),
            'item_type': forms.HiddenInput(),
            'component': forms.HiddenInput(),
            'bom': forms.HiddenInput(),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.01', 'step': '0.01'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'line_total': forms.HiddenInput(),
        }

# Create formset factory
InvoiceItemFormSet = inlineformset_factory(
    Invoice, 
    InvoiceItem, 
    form=InvoiceItemForm, 
    extra=1,  # Allow one empty form by default
    can_delete=True
)

# Purchase Module Forms
class PurchaseRFQForm(BootstrapForm):
    class Meta:
        model = PurchaseRFQ
        fields = '__all__'
        exclude = ['rfq_id', 'rfq_number', 'created_by', 'created_date', 'last_modified']
        widgets = {
            'requisition': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

class PurchaseRFQItemForm(BootstrapForm):
    class Meta:
        model = PurchaseRFQItem
        fields = '__all__'
        exclude = ['item_id']
        widgets = {
            'rfq': forms.HiddenInput(),
            'component': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'specifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'required_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        return quantity

PurchaseRFQItemFormSet = inlineformset_factory(
    PurchaseRFQ, PurchaseRFQItem, form=PurchaseRFQItemForm,
    extra=1, can_delete=True, can_order=False,
    formset=RequiredInlineFormSet
)

class PurchaseRFQSupplierForm(BootstrapForm):
    class Meta:
        model = PurchaseRFQSupplier
        fields = '__all__'
        exclude = ['rfq_supplier_id', 'sent_date', 'response_date', 'status']
        widgets = {
            'rfq': forms.HiddenInput(),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
        }

PurchaseRFQSupplierFormSet = inlineformset_factory(
    PurchaseRFQ, PurchaseRFQSupplier, form=PurchaseRFQSupplierForm,
    extra=1, can_delete=True, can_order=False,
    formset=RequiredInlineFormSet
)

class SupplierResponseForm(BootstrapForm):
    class Meta:
        model = SupplierResponse
        fields = '__all__'
        exclude = ['response_id']
        widgets = {
            'rfq_supplier': forms.HiddenInput(),
            'rfq_item': forms.HiddenInput(),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'lead_time_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'min_order_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'validity_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def clean_unit_price(self):
        unit_price = self.cleaned_data.get('unit_price')
        if unit_price <= 0:
            raise ValidationError("Unit price must be greater than zero.")
        return unit_price
    
    def clean_lead_time_days(self):
        lead_time_days = self.cleaned_data.get('lead_time_days')
        if lead_time_days < 0:
            raise ValidationError("Lead time cannot be negative.")
        return lead_time_days
    
    def clean_min_order_quantity(self):
        min_order_quantity = self.cleaned_data.get('min_order_quantity')
        if min_order_quantity < 0:
            raise ValidationError("Minimum order quantity cannot be negative.")
        return min_order_quantity
    
    def clean_validity_days(self):
        validity_days = self.cleaned_data.get('validity_days')
        if validity_days < 0:
            raise ValidationError("Validity days cannot be negative.")
        return validity_days

class PurchaseOrderForm(BootstrapForm):
    class Meta:
        model = PurchaseOrder
        fields = '__all__'
        exclude = ['po_id', 'po_number', 'subtotal', 'tax_amount', 'total_amount', 'created_by', 'created_date', 'last_modified']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'rfq': forms.Select(attrs={'class': 'form-select'}),
            'order_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expected_delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        order_date = cleaned_data.get('order_date')
        expected_delivery_date = cleaned_data.get('expected_delivery_date')
        
        if order_date and expected_delivery_date:
            if expected_delivery_date < order_date:
                raise ValidationError("Expected delivery date cannot be before order date.")
            
            if expected_delivery_date < timezone.now().date():
                raise ValidationError("Expected delivery date cannot be in the past.")
        
        return cleaned_data

class PurchaseOrderItemForm(BootstrapForm):
    class Meta:
        model = PurchaseOrderItem
        fields = '__all__'
        exclude = ['item_id', 'line_total', 'received_quantity']
        widgets = {
            'purchase_order': forms.HiddenInput(),
            'component': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
        }
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        return quantity
    
    def clean_unit_price(self):
        unit_price = self.cleaned_data.get('unit_price')
        if unit_price <= 0:
            raise ValidationError("Unit price must be greater than zero.")
        return unit_price
    
    def clean_tax_rate(self):
        tax_rate = self.cleaned_data.get('tax_rate')
        if tax_rate < 0:
            raise ValidationError("Tax rate cannot be negative.")
        if tax_rate > 100:
            raise ValidationError("Tax rate cannot exceed 100%.")
        return tax_rate

PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder, PurchaseOrderItem, form=PurchaseOrderItemForm,
    extra=1, can_delete=True, can_order=False,
    formset=RequiredInlineFormSet
)

class GoodsReceivedNoteForm(BootstrapForm):
    class Meta:
        model = GoodsReceivedNote
        fields = '__all__'
        exclude = ['grn_id', 'grn_number', 'created_date', 'last_modified']
        widgets = {
            'purchase_order': forms.Select(attrs={'class': 'form-select'}),
            'received_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'received_by': forms.Select(attrs={'class': 'form-select'}),
            'verified_by': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        received_date = cleaned_data.get('received_date')
        
        if received_date and received_date > timezone.now().date():
            raise ValidationError("Received date cannot be in the future.")
        
        return cleaned_data

class GRNItemForm(BootstrapForm):
    class Meta:
        model = GRNItem
        fields = '__all__'
        exclude = ['item_id']
        widgets = {
            'grn': forms.HiddenInput(),
            'po_item': forms.Select(attrs={'class': 'form-select'}),
            'quantity_received': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'quantity_accepted': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'quality_status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    def __init__(self, *args, **kwargs):
        po = kwargs.pop('purchase_order', None)
        super().__init__(*args, **kwargs)
        if po:
            self.fields['po_item'].queryset = po.items.all()
    
    def clean_quantity_received(self):
        quantity_received = self.cleaned_data.get('quantity_received')
        if quantity_received < 0:
            raise ValidationError("Quantity received cannot be negative.")
        return quantity_received
    
    def clean_quantity_accepted(self):
        quantity_accepted = self.cleaned_data.get('quantity_accepted')
        quantity_received = self.cleaned_data.get('quantity_received')
        
        if quantity_accepted < 0:
            raise ValidationError("Quantity accepted cannot be negative.")
        
        if quantity_received is not None and quantity_accepted > quantity_received:
            raise ValidationError("Quantity accepted cannot exceed quantity received.")
        
        return quantity_accepted

GRNItemFormSet = inlineformset_factory(
    GoodsReceivedNote, GRNItem, form=GRNItemForm,
    extra=1, can_delete=True, can_order=False,
    formset=RequiredInlineFormSet
)

class SupplierInvoiceForm(BootstrapForm):
    class Meta:
        model = SupplierInvoice
        fields = '__all__'
        exclude = ['invoice_id', 'created_by', 'created_date', 'last_modified']
        widgets = {
            'invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'purchase_order': forms.Select(attrs={'class': 'form-select'}),
            'grn': forms.Select(attrs={'class': 'form-select'}),
            'invoice_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'invoice_file': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        invoice_date = cleaned_data.get('invoice_date')
        due_date = cleaned_data.get('due_date')
        amount = cleaned_data.get('amount', 0)
        tax_amount = cleaned_data.get('tax_amount', 0)
        total_amount = cleaned_data.get('total_amount', 0)
        
        if invoice_date and due_date:
            if due_date < invoice_date:
                raise ValidationError("Due date cannot be before invoice date.")
            
            if due_date < timezone.now().date():
                raise ValidationError("Due date cannot be in the past.")
        
        if total_amount != amount + tax_amount:
            raise ValidationError("Total amount must equal amount plus tax amount.")
        
        return cleaned_data
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount', 0)
        if amount < 0:
            raise ValidationError("Amount cannot be negative.")
        return amount
    
    def clean_tax_amount(self):
        tax_amount = self.cleaned_data.get('tax_amount', 0)
        if tax_amount < 0:
            raise ValidationError("Tax amount cannot be negative.")
        return tax_amount
    
    def clean_total_amount(self):
        total_amount = self.cleaned_data.get('total_amount', 0)
        if total_amount < 0:
            raise ValidationError("Total amount cannot be negative.")
        return total_amount