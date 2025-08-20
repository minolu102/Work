# sales/forms.py
from django import forms
from .models import Customer, SalesOrder, SalesInvoice, SalesPayment

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'code', 'name', 'customer_type', 'email', 'phone', 'mobile',
            'tax_id', 'registration_number', 'credit_limit', 'payment_terms',
            'discount_percent', 'sales_representative'
        ]
        widgets = {
            'credit_limit': forms.NumberInput(attrs={'step': '0.01'}),
            'discount_percent': forms.NumberInput(attrs={'step': '0.01', 'max': '100'}),
            'payment_terms': forms.NumberInput(attrs={'min': '0'}),
        }

class SalesOrderForm(forms.ModelForm):
    class Meta:
        model = SalesOrder
        fields = [
            'customer', 'order_date', 'expected_delivery_date',
            'reference', 'customer_po', 'warehouse', 'delivery_address', 'notes'
        ]
        widgets = {
            'order_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'delivery_address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class SalesInvoiceForm(forms.ModelForm):
    class Meta:
        model = SalesInvoice
        fields = [
            'customer', 'sales_order', 'invoice_date', 'due_date',
            'reference', 'customer_po', 'payment_terms'
        ]
        widgets = {
            'invoice_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'payment_terms': forms.Textarea(attrs={'rows': 2}),
        }