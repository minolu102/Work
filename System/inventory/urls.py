# inventory/urls.py
from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('products/', views.product_list, name='product_list'),
    path('products/<uuid:product_id>/', views.product_detail, name='product_detail'),
    path('products/create/', views.create_product, name='create_product'),
    
    path('stock-moves/', views.stock_movements, name='stock_movements'),
    path('stock-moves/create/', views.create_stock_move, name='create_stock_move'),
    
    path('adjustments/', views.stock_adjustments, name='stock_adjustments'),
    path('adjustments/create/', views.create_stock_adjustment, name='create_stock_adjustment'),
    path('adjustments/<uuid:adjustment_id>/', views.stock_adjustment_detail, name='stock_adjustment_detail'),
    
    path('warehouses/', views.warehouse_list, name='warehouse_list'),
    path('warehouses/<uuid:warehouse_id>/', views.warehouse_detail, name='warehouse_detail'),
    
    path('reports/inventory/', views.inventory_report, name='inventory_report'),
    path('reports/stock-valuation/', views.stock_valuation_report, name='stock_valuation_report'),
]