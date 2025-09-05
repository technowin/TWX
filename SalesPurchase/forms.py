from django import forms
from .models import *
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

class CustomerForm(forms.ModelForm):
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

class CustomerPricingForm(forms.ModelForm):
    class Meta:
        model = CustomerPricing
        fields = '__all__'
        exclude = ['pricing_id', 'created_by', 'created_date']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'component': forms.Select(attrs={'class': 'form-select'}),
            'bom': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
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
        
        # Validate that either component or BOM is selected, but not both
        if not component and not bom:
            raise ValidationError("Either component or BOM must be specified.")
        
        if component and bom:
            raise ValidationError("Only one of component or BOM can be specified, not both.")
        
        # Validate date ranges
        if effective_date and effective_date < timezone.now().date():
            raise ValidationError("Effective date cannot be in the past.")
        
        if expiry_date and effective_date and expiry_date <= effective_date:
            raise ValidationError("Expiry date must be after effective date.")
        
        return cleaned_data
    
class RFQForm(forms.ModelForm):
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
                raise ValidationError("Required by date cannot be before RFQ date.")
            
            if required_by_date < timezone.now().date():
                raise ValidationError("Required by date cannot be in the past.")
        
        return cleaned_data

class RFQItemForm(forms.ModelForm):
    class Meta:
        model = RFQItem
        fields = '__all__'
        exclude = ['item_id']
        widgets = {
            'rfq': forms.HiddenInput(),
            'item_type': forms.Select(attrs={'class': 'form-select item-type-select'}),
            'component': forms.Select(attrs={'class': 'form-select component-select'}),
            'bom': forms.Select(attrs={'class': 'form-select bom-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'target_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'specifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

RFQItemFormSet = inlineformset_factory(
    RFQ, RFQItem, form=RFQItemForm,
    extra=1, can_delete=True, can_order=False
)

class QuotationForm(forms.ModelForm):
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

class QuotationItemForm(forms.ModelForm):
    class Meta:
        model = QuotationItem
        fields = '__all__'
        exclude = ['item_id', 'line_total']
        widgets = {
            'quotation': forms.HiddenInput(),
            'rfq_item': forms.HiddenInput(),
            'item_type': forms.Select(attrs={'class': 'form-select item-type-select'}),
            'component': forms.Select(attrs={'class': 'form-select component-select'}),
            'bom': forms.Select(attrs={'class': 'form-select bom-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control'}),
        }

QuotationItemFormSet = inlineformset_factory(
    Quotation, QuotationItem, form=QuotationItemForm,
    extra=1, can_delete=True, can_order=False
)

class SalesOrderForm(forms.ModelForm):
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

class SalesOrderItemForm(forms.ModelForm):
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
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control'}),
        }

SalesOrderItemFormSet = inlineformset_factory(
    SalesOrder, SalesOrderItem, form=SalesOrderItemForm,
    extra=1, can_delete=True, can_order=False
)

class InvoiceForm(forms.ModelForm):
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
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
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

class PurchaseRFQForm(forms.ModelForm):
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

class PurchaseRFQItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseRFQItem
        fields = '__all__'
        exclude = ['item_id']
        widgets = {
            'rfq': forms.HiddenInput(),
            'component': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'specifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'required_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

PurchaseRFQItemFormSet = inlineformset_factory(
    PurchaseRFQ, PurchaseRFQItem, form=PurchaseRFQItemForm,
    extra=1, can_delete=True, can_order=False
)

class PurchaseRFQSupplierForm(forms.ModelForm):
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
    extra=1, can_delete=True, can_order=False
)

class SupplierResponseForm(forms.ModelForm):
    class Meta:
        model = SupplierResponse
        fields = '__all__'
        exclude = ['response_id']
        widgets = {
            'rfq_supplier': forms.HiddenInput(),
            'rfq_item': forms.HiddenInput(),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'lead_time_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'min_order_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'validity_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class PurchaseOrderForm(forms.ModelForm):
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

class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = '__all__'
        exclude = ['item_id', 'line_total', 'received_quantity']
        widgets = {
            'purchase_order': forms.HiddenInput(),
            'component': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control'}),
        }

PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder, PurchaseOrderItem, form=PurchaseOrderItemForm,
    extra=1, can_delete=True, can_order=False
)

class GoodsReceivedNoteForm(forms.ModelForm):
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

class GRNItemForm(forms.ModelForm):
    class Meta:
        model = GRNItem
        fields = '__all__'
        exclude = ['item_id']
        widgets = {
            'grn': forms.HiddenInput(),
            'po_item': forms.Select(attrs={'class': 'form-select'}),
            'quantity_received': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity_accepted': forms.NumberInput(attrs={'class': 'form-control'}),
            'quality_status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

GRNItemFormSet = inlineformset_factory(
    GoodsReceivedNote, GRNItem, form=GRNItemForm,
    extra=1, can_delete=True, can_order=False
)

class SupplierInvoiceForm(forms.ModelForm):
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
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
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
    

# forms.py - Add formset improvements
from django.forms import BaseInlineFormSet

class RequiredInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make first form required
        if self.forms and not self.forms[0].has_changed():
            self.forms[0].empty_permitted = False

# Update all formset definitions to use the required formset
RFQItemFormSet = inlineformset_factory(
    RFQ, RFQItem, form=RFQItemForm,
    extra=1, can_delete=True, can_order=False,
    formset=RequiredInlineFormSet
)

QuotationItemFormSet = inlineformset_factory(
    Quotation, QuotationItem, form=QuotationItemForm,
    extra=1, can_delete=True, can_order=False,
    formset=RequiredInlineFormSet
)

SalesOrderItemFormSet = inlineformset_factory(
    SalesOrder, SalesOrderItem, form=SalesOrderItemForm,
    extra=1, can_delete=True, can_order=False,
    formset=RequiredInlineFormSet
)

PurchaseRFQItemFormSet = inlineformset_factory(
    PurchaseRFQ, PurchaseRFQItem, form=PurchaseRFQItemForm,
    extra=1, can_delete=True, can_order=False,
    formset=RequiredInlineFormSet
)

PurchaseRFQSupplierFormSet = inlineformset_factory(
    PurchaseRFQ, PurchaseRFQSupplier, form=PurchaseRFQSupplierForm,
    extra=1, can_delete=True, can_order=False,
    formset=RequiredInlineFormSet
)

PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder, PurchaseOrderItem, form=PurchaseOrderItemForm,
    extra=1, can_delete=True, can_order=False,
    formset=RequiredInlineFormSet
)

GRNItemFormSet = inlineformset_factory(
    GoodsReceivedNote, GRNItem, form=GRNItemForm,
    extra=1, can_delete=True, can_order=False,
    formset=RequiredInlineFormSet
)