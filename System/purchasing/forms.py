# purchasing/forms.py
from django import forms
from .models import Supplier, PurchaseOrder, PurchaseBill, SupplierEvaluation

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            'code', 'name', 'supplier_type', 'email', 'phone', 'mobile',
            'tax_id', 'registration_number', 'credit_limit', 'payment_terms',
            'discount_percent', 'purchase_representative', 'is_approved'
        ]
        widgets = {
            'credit_limit': forms.NumberInput(attrs={'step': '0.01'}),
            'discount_percent': forms.NumberInput(attrs={'step': '0.01', 'max': '100'}),
            'payment_terms': forms.NumberInput(attrs={'min': '0'}),
        }

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            'supplier', 'order_date', 'expected_delivery_date', 'priority',
            'reference', 'supplier_reference', 'warehouse', 'delivery_address', 'notes'
        ]
        widgets = {
            'order_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'delivery_address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class PurchaseBillForm(forms.ModelForm):
    class Meta:
        model = PurchaseBill
        fields = [
            'supplier', 'purchase_order', 'bill_date', 'due_date',
            'supplier_invoice_number', 'reference', 'payment_terms'
        ]
        widgets = {
            'bill_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'payment_terms': forms.Textarea(attrs={'rows': 2}),
        }