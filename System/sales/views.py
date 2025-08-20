# sales/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Q, F
from django.utils import timezone
from django.core.paginator import Paginator
from .models import Customer, SalesOrder, SalesInvoice, SalesPayment
from .forms import CustomerForm, SalesOrderForm, SalesInvoiceForm
from inventory.models import Product
# Create your views here.

@login_required
def customer_list(request):
    """รายการลูกค้า"""
    customers = Customer.objects.filter(
        company=request.user.profile.company,
        is_active=True
    ).order_by('code')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        customers = customers.filter(
            Q(code__icontains=search) |
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )
    
    # Filter by customer type
    customer_type = request.GET.get('customer_type', '')
    if customer_type:
        customers = customers.filter(customer_type=customer_type)
    
    # Pagination
    paginator = Paginator(customers, 20)
    page = request.GET.get('page')
    customers = paginator.get_page(page)
    
    context = {
        'customers': customers,
        'search': search,
        'customer_type': customer_type,
        'title': 'Customer List - รายการลูกค้า'
    }
    return render(request, 'sales/customer_list.html', context)

@login_required
def customer_detail(request, customer_id):
    """รายละเอียดลูกค้า"""
    customer = get_object_or_404(
        Customer,
        id=customer_id,
        company=request.user.profile.company
    )
    
    # Recent orders
    recent_orders = customer.sales_orders.filter(
        is_active=True
    ).order_by('-order_date')[:10]
    
    # Outstanding invoices
    outstanding_invoices = customer.sales_invoices.filter(
        status__in=['confirmed', 'partial_paid', 'overdue']
    ).order_by('due_date')
    
    # Payment history
    recent_payments = customer.payments.filter(
        status='confirmed'
    ).order_by('-payment_date')[:10]
    
    # Statistics
    total_orders = customer.sales_orders.filter(is_active=True).count()
    total_sales = customer.sales_invoices.filter(
        status__in=['confirmed', 'paid', 'partial_paid']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    outstanding_balance = customer.get_outstanding_balance()
    credit_available = customer.get_credit_available()
    
    context = {
        'customer': customer,
        'recent_orders': recent_orders,
        'outstanding_invoices': outstanding_invoices,
        'recent_payments': recent_payments,
        'total_orders': total_orders,
        'total_sales': total_sales,
        'outstanding_balance': outstanding_balance,
        'credit_available': credit_available,
        'title': f'Customer Details - {customer.name}'
    }
    return render(request, 'sales/customer_detail.html', context)

@login_required
def sales_order_list(request):
    """รายการใบสั่งขาย"""
    orders = SalesOrder.objects.filter(
        company=request.user.profile.company
    ).select_related('customer', 'sales_representative').order_by('-order_date')
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        orders = orders.filter(status=status)
    
    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        orders = orders.filter(order_date__gte=date_from)
    if date_to:
        orders = orders.filter(order_date__lte=date_to)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(customer__name__icontains=search) |
            Q(customer_po__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(orders, 20)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    context = {
        'orders': orders,
        'status': status,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
        'title': 'Sales Orders - ใบสั่งขาย'
    }
    return render(request, 'sales/sales_order_list.html', context)

@login_required
def create_sales_order(request):
    """สร้างใบสั่งขายใหม่"""
    if request.method == 'POST':
        form = SalesOrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.company = request.user.profile.company
            order.sales_representative = request.user
            order.created_by = request.user
            
            # Generate order number
            sequence = Sequence.objects.get_or_create(
                sequence_type='sales_order',
                defaults={'prefix': 'SO', 'current_number': 0}
            )[0]
            order.order_number = sequence.get_next_number()
            order.save()
            
            messages.success(request, 'Sales order created successfully.')
            return redirect('sales:sales_order_detail', order_id=order.id)
    else:
        form = SalesOrderForm()
        form.fields['customer'].queryset = Customer.objects.filter(
            company=request.user.profile.company,
            is_active=True
        )
        form.fields['warehouse'].queryset = Warehouse.objects.filter(
            company=request.user.profile.company,
            is_active=True
        )
    
    context = {
        'form': form,
        'title': 'Create Sales Order'
    }
    return render(request, 'sales/sales_order_form.html', context)

@login_required
def sales_invoice_list(request):
    """รายการใบกำกับภาษี"""
    invoices = SalesInvoice.objects.filter(
        company=request.user.profile.company
    ).select_related('customer').order_by('-invoice_date')
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        invoices = invoices.filter(status=status)
    
    # Filter overdue invoices
    show_overdue = request.GET.get('overdue', '')
    if show_overdue:
        invoices = invoices.filter(
            due_date__lt=timezone.now().date(),
            status__in=['confirmed', 'partial_paid']
        )
    
    # Pagination
    paginator = Paginator(invoices, 20)
    page = request.GET.get('page')
    invoices = paginator.get_page(page)
    
    # Summary statistics
    total_outstanding = SalesInvoice.objects.filter(
        company=request.user.profile.company,
        status__in=['confirmed', 'partial_paid', 'overdue']
    ).aggregate(total=Sum('outstanding_amount'))['total'] or 0
    
    overdue_count = SalesInvoice.objects.filter(
        company=request.user.profile.company,
        due_date__lt=timezone.now().date(),
        status__in=['confirmed', 'partial_paid']
    ).count()
    
    context = {
        'invoices': invoices,
        'status': status,
        'show_overdue': show_overdue,
        'total_outstanding': total_outstanding,
        'overdue_count': overdue_count,
        'title': 'Sales Invoices - ใบกำกับภาษี'
    }
    return render(request, 'sales/sales_invoice_list.html', context)

@login_required
def sales_report(request):
    """รายงานการขาย"""
    company = request.user.profile.company
    
    # Date range filter
    date_from = request.GET.get('date_from', timezone.now().date().replace(day=1))
    date_to = request.GET.get('date_to', timezone.now().date())
    
    # Sales summary
    invoices = SalesInvoice.objects.filter(
        company=company,
        invoice_date__range=[date_from, date_to],
        status__in=['confirmed', 'paid', 'partial_paid']
    )
    
    total_sales = invoices.aggregate(total=Sum('total_amount'))['total'] or 0
    total_invoices = invoices.count()
    average_order_value = total_sales / total_invoices if total_invoices > 0 else 0
    
    # Sales by customer
    customer_sales = invoices.values(
        'customer__name'
    ).annotate(
        total_amount=Sum('total_amount'),
        invoice_count=Count('id')
    ).order_by('-total_amount')[:10]
    
    # Sales by product
    invoice_lines = SalesInvoiceLine.objects.filter(
        invoice__company=company,
        invoice__invoice_date__range=[date_from, date_to],
        invoice__status__in=['confirmed', 'paid', 'partial_paid']
    )
    
    product_sales = invoice_lines.values(
        'product__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_amount=Sum('line_total')
    ).order_by('-total_amount')[:10]
    
    # Monthly trend (last 12 months)
    from django.db.models.functions import TruncMonth
    from datetime import date, timedelta
    
    twelve_months_ago = date.today() - timedelta(days=365)
    monthly_sales = SalesInvoice.objects.filter(
        company=company,
        invoice_date__gte=twelve_months_ago,
        status__in=['confirmed', 'paid', 'partial_paid']
    ).annotate(
        month=TruncMonth('invoice_date')
    ).values('month').annotate(
        total_amount=Sum('total_amount'),
        invoice_count=Count('id')
    ).order_by('month')
    
    context = {
        'date_from': date_from,
        'date_to': date_to,
        'total_sales': total_sales,
        'total_invoices': total_invoices,
        'average_order_value': average_order_value,
        'customer_sales': customer_sales,
        'product_sales': product_sales,
        'monthly_sales': monthly_sales,
        'title': 'Sales Report - รายงานการขาย'
    }
    return render(request, 'sales/sales_report.html', context)

@login_required
def create_customer(request):
    """Create customer placeholder"""
    return render(request, 'sales/customer_form.html', {'title': 'Create Customer'})

@login_required
def sales_order_detail(request, order_id):
    """Sales order detail placeholder"""
    return render(request, 'sales/sales_order_detail.html', {'title': 'Sales Order Detail'})

@login_required
def confirm_sales_order(request, order_id):
    """Confirm sales order placeholder"""
    return render(request, 'sales/confirm_sales_order.html', {'title': 'Confirm Sales Order'})

@login_required
def delivery_order_list(request):
    """Delivery order list placeholder"""
    return render(request, 'sales/delivery_order_list.html', {'title': 'Delivery Orders'})

@login_required
def delivery_order_detail(request, delivery_id):
    """Delivery order detail placeholder"""
    return render(request, 'sales/delivery_order_detail.html', {'title': 'Delivery Order Detail'})

@login_required
def create_delivery_order(request):
    """Create delivery order placeholder"""
    return render(request, 'sales/delivery_order_form.html', {'title': 'Create Delivery Order'})

@login_required
def sales_invoice_detail(request, invoice_id):
    """Sales invoice detail placeholder"""
    return render(request, 'sales/sales_invoice_detail.html', {'title': 'Sales Invoice Detail'})

@login_required
def create_sales_invoice(request):
    """Create sales invoice placeholder"""
    return render(request, 'sales/sales_invoice_form.html', {'title': 'Create Sales Invoice'})

@login_required
def print_invoice(request, invoice_id):
    """Print sales invoice placeholder"""
    return render(request, 'sales/print_invoice.html', {'title': 'Print Invoice'})

@login_required
def payment_list(request):
    """Payment list placeholder"""
    return render(request, 'sales/payment_list.html', {'title': 'Payment List'})

@login_required
def payment_detail(request, payment_id):
    """Payment detail placeholder"""
    return render(request, 'sales/payment_detail.html', {'title': 'Payment Detail'})

@login_required
def create_payment(request):
    """Create payment placeholder"""
    return render(request, 'sales/payment_form.html', {'title': 'Create Payment'})

@login_required
def customer_statement(request):
    """Customer statement report placeholder"""
    return render(request, 'sales/customer_statement.html', {'title': 'Customer Statement'})