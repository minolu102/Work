# purchasing/urls.py
from django.urls import path
from . import views

app_name = 'purchasing'

urlpatterns = [
    path('', views.purchase_order_list, name='purchase_order_list'),
    
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/<uuid:supplier_id>/', views.supplier_detail, name='supplier_detail'),
    path('suppliers/create/', views.create_supplier, name='create_supplier'),
    
    path('orders/', views.purchase_order_list, name='purchase_order_list'),
    path('orders/<uuid:order_id>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('orders/create/', views.create_purchase_order, name='create_purchase_order'),
    path('orders/<uuid:order_id>/approve/', views.approve_purchase_order, name='approve_purchase_order'),
    
    path('receipts/', views.purchase_receipt_list, name='purchase_receipt_list'),
    path('receipts/<uuid:receipt_id>/', views.purchase_receipt_detail, name='purchase_receipt_detail'),
    path('receipts/create/', views.create_purchase_receipt, name='create_purchase_receipt'),
    
    path('bills/', views.purchase_bill_list, name='purchase_bill_list'),
    path('bills/<uuid:bill_id>/', views.purchase_bill_detail, name='purchase_bill_detail'),
    path('bills/create/', views.create_purchase_bill, name='create_purchase_bill'),
    
    path('payments/', views.purchase_payment_list, name='purchase_payment_list'),
    path('payments/<uuid:payment_id>/', views.purchase_payment_detail, name='purchase_payment_detail'),
    path('payments/create/', views.create_purchase_payment, name='create_purchase_payment'),
    
    path('reports/purchasing/', views.purchase_report, name='purchase_report'),
    path('reports/supplier-performance/', views.supplier_performance_report, name='supplier_performance_report'),
]