# inventory/forms.py
from django import forms
from .models import Product, ProductCategory, StockMove, StockAdjustment

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'code', 'name', 'description', 'product_type', 'category', 'brand',
            'base_uom', 'purchase_uom', 'sales_uom', 'cost_price', 'sale_price',
            'track_inventory', 'reorder_level', 'minimum_stock', 'maximum_stock',
            'barcode', 'internal_reference', 'weight', 'volume',
            'can_be_sold', 'can_be_purchased'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'cost_price': forms.NumberInput(attrs={'step': '0.01'}),
            'sale_price': forms.NumberInput(attrs={'step': '0.01'}),
            'weight': forms.NumberInput(attrs={'step': '0.0001'}),
            'volume': forms.NumberInput(attrs={'step': '0.0001'}),
        }

class StockMoveForm(forms.ModelForm):
    class Meta:
        model = StockMove
        fields = [
            'move_type', 'product', 'source_location', 'destination_location',
            'quantity', 'unit_cost', 'scheduled_date', 'reason'
        ]
        widgets = {
            'scheduled_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'quantity': forms.NumberInput(attrs={'step': '0.0001'}),
            'unit_cost': forms.NumberInput(attrs={'step': '0.01'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }

class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockAdjustment
        fields = ['adjustment_date', 'warehouse', 'reason']
        widgets = {
            'adjustment_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }