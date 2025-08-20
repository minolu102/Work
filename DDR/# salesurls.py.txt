# sales/urls.py
from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('', views.sales_order_list, name='sales_order_list'),
    
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/<uuid:customer_id>/', views.customer_detail, name='customer_detail'),
    path('customers/create/', views.create_customer, name='create_customer'),
    
    path('orders/', views.sales_order_list, name='sales_order_list'),
    path('orders/<uuid:order_id>/', views.sales_order_detail, name='sales_order_detail'),
    path('orders/create/', views.create_sales_order, name='create_sales_order'),
    path('orders/<uuid:order_id>/confirm/', views.confirm_sales_order, name='confirm_sales_order'),
    
    path('deliveries/', views.delivery_order_list, name='delivery_order_list'),
    path('deliveries/<uuid:delivery_id>/', views.delivery_order_detail, name='delivery_order_detail'),
    path('deliveries/create/', views.create_delivery_order, name='create_delivery_order'),
    
    path('invoices/', views.sales_invoice_list, name='sales_invoice_list'),
    path('invoices/<uuid:invoice_id>/', views.sales_invoice_detail, name='sales_invoice_detail'),
    path('invoices/create/', views.create_sales_invoice, name='create_sales_invoice'),
    path('invoices/<uuid:invoice_id>/print/', views.print_invoice, name='print_invoice'),
    
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/<uuid:payment_id>/', views.payment_detail, name='payment_detail'),
    path('payments/create/', views.create_payment, name='create_payment'),
    
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/customer-statement/', views.customer_statement, name='customer_statement'),
]