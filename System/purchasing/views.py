# purchasing/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q, F, Avg, Count
from django.utils import timezone
from django.core.paginator import Paginator
from .models import Supplier, PurchaseOrder, PurchaseBill, PurchasePayment
from .forms import SupplierForm, PurchaseOrderForm, PurchaseBillForm
from inventory.models import Product
# Create your views here.

@login_required
def supplier_list(request):
    """รายการผู้จำหน่าย"""
    suppliers = Supplier.objects.filter(
        company=request.user.profile.company,
        is_active=True
    ).order_by('code')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        suppliers = suppliers.filter(
            Q(code__icontains=search) |
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )
    
    # Filter by approval status
    approved_only = request.GET.get('approved', '')
    if approved_only:
        suppliers = suppliers.filter(is_approved=True)
    
    # Pagination
    paginator = Paginator(suppliers, 20)
    page = request.GET.get('page')
    suppliers = paginator.get_page(page)
    
    context = {
        'suppliers': suppliers,
        'search': search,
        'approved_only': approved_only,
        'title': 'Supplier List - รายการผู้จำหน่าย'
    }
    return render(request, 'purchasing/supplier_list.html', context)

@login_required
def purchase_order_list(request):
    """รายการใบสั่งซื้อ"""
    orders = PurchaseOrder.objects.filter(
        company=request.user.profile.company
    ).select_related('supplier', 'purchase_representative').order_by('-order_date')
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        orders = orders.filter(status=status)
    
    # Filter by priority
    priority = request.GET.get('priority', '')
    if priority:
        orders = orders.filter(priority=priority)
    
    # Filter pending approval
    pending_approval = request.GET.get('pending_approval', '')
    if pending_approval:
        orders = orders.filter(requires_approval=True, approved_by__isnull=True)
    
    # Pagination
    paginator = Paginator(orders, 20)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    context = {
        'orders': orders,
        'status': status,
        'priority': priority,
        'pending_approval': pending_approval,
        'title': 'Purchase Orders - ใบสั่งซื้อ'
    }
    return render(request, 'purchasing/purchase_order_list.html', context)

@login_required
def create_purchase_order(request):
    """สร้างใบสั่งซื้อใหม่"""
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.company = request.user.profile.company
            order.purchase_representative = request.user
            order.created_by = request.user
            
            # Generate PO number
            sequence = Sequence.objects.get_or_create(
                sequence_type='purchase_order',
                defaults={'prefix': 'PO', 'current_number': 0}
            )[0]
            order.po_number = sequence.get_next_number()
            
            # Check if requires approval (based on amount threshold)
            if order.total_amount > 100000:  # 100,000 THB threshold
                order.requires_approval = True
            
            order.save()
            
            messages.success(request, 'Purchase order created successfully.')
            return redirect('purchasing:purchase_order_detail', order_id=order.id)
    else:
        form = PurchaseOrderForm()
        form.fields['supplier'].queryset = Supplier.objects.filter(
            company=request.user.profile.company,
            is_active=True,
            is_approved=True
        )
    
    context = {
        'form': form,
        'title': 'Create Purchase Order'
    }
    return render(request, 'purchasing/purchase_order_form.html', context)

@login_required
def purchase_bill_list(request):
    """รายการบิลซื้อ"""
    bills = PurchaseBill.objects.filter(
        company=request.user.profile.company
    ).select_related('supplier').order_by('-bill_date')
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        bills = bills.filter(status=status)
    
    # Filter overdue bills
    show_overdue = request.GET.get('overdue', '')
    if show_overdue:
        bills = bills.filter(
            due_date__lt=timezone.now().date(),
            status__in=['confirmed', 'partial_paid']
        )
    
    # Pagination
    paginator = Paginator(bills, 20)
    page = request.GET.get('page')
    bills = paginator.get_page(page)
    
    # Summary statistics
    total_outstanding = PurchaseBill.objects.filter(
        company=request.user.profile.company,
        status__in=['confirmed', 'partial_paid', 'overdue']
    ).aggregate(total=Sum('outstanding_amount'))['total'] or 0
    
    overdue_count = PurchaseBill.objects.filter(
        company=request.user.profile.company,
        due_date__lt=timezone.now().date(),
        status__in=['confirmed', 'partial_paid']
    ).count()
    
    context = {
        'bills': bills,
        'status': status,
        'show_overdue': show_overdue,
        'total_outstanding': total_outstanding,
        'overdue_count': overdue_count,
        'title': 'Purchase Bills - บิลซื้อ'
    }
    return render(request, 'purchasing/purchase_bill_list.html', context)

@login_required
def purchase_report(request):
    """รายงานการซื้อ"""
    company = request.user.profile.company
    
    # Date range filter
    date_from = request.GET.get('date_from', timezone.now().date().replace(day=1))
    date_to = request.GET.get('date_to', timezone.now().date())
    
    # Purchase summary
    bills = PurchaseBill.objects.filter(
        company=company,
        bill_date__range=[date_from, date_to],
        status__in=['confirmed', 'paid', 'partial_paid']
    )
    
    total_purchases = bills.aggregate(total=Sum('total_amount'))['total'] or 0
    total_bills = bills.count()
    average_bill_value = total_purchases / total_bills if total_bills > 0 else 0
    
    # Purchases by supplier
    supplier_purchases = bills.values(
        'supplier__name'
    ).annotate(
        total_amount=Sum('total_amount'),
        bill_count=Count('id')
    ).order_by('-total_amount')[:10]
    
    # Top purchased products
    bill_lines = PurchaseBillLine.objects.filter(
        bill__company=company,
        bill__bill_date__range=[date_from, date_to],
        bill__status__in=['confirmed', 'paid', 'partial_paid']
    )
    
    product_purchases = bill_lines.values(
        'product__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_amount=Sum('line_total')
    ).order_by('-total_amount')[:10]
    
    # Supplier performance
    supplier_performance = Supplier.objects.filter(
        company=company,
        is_active=True
    ).annotate(
        avg_quality=Avg('quality_rating'),
        avg_delivery=Avg('delivery_rating'),
        avg_service=Avg('service_rating'),
        total_orders=Count('purchase_orders', filter=Q(purchase_orders__status='confirmed'))
    ).order_by('-avg_quality')[:10]
    
    context = {
        'date_from': date_from,
        'date_to': date_to,
        'total_purchases': total_purchases,
        'total_bills': total_bills,
        'average_bill_value': average_bill_value,
        'supplier_purchases': supplier_purchases,
        'product_purchases': product_purchases,
        'supplier_performance': supplier_performance,
        'title': 'Purchase Report - รายงานการซื้อ'
    }
    return render(request, 'purchasing/purchase_report.html', context)

@login_required
def supplier_detail(request, supplier_id):
    """Supplier detail placeholder"""
    return render(request, 'purchasing/supplier_detail.html', {'title': 'Supplier Detail'})

@login_required
def create_supplier(request):
    """Create supplier placeholder"""
    return render(request, 'purchasing/supplier_form.html', {'title': 'Create Supplier'})

@login_required
def purchase_order_detail(request, order_id):
    """Purchase order detail placeholder"""
    return render(request, 'purchasing/purchase_order_detail.html', {'title': 'Purchase Order Detail'})

@login_required
def approve_purchase_order(request, order_id):
    """Approve purchase order placeholder"""
    return render(request, 'purchasing/approve_purchase_order.html', {'title': 'Approve Purchase Order'})

@login_required
def purchase_receipt_list(request):
    """Purchase receipt list placeholder"""
    return render(request, 'purchasing/purchase_receipt_list.html', {'title': 'Purchase Receipts'})

@login_required
def purchase_receipt_detail(request, receipt_id):
    """Purchase receipt detail placeholder"""
    return render(request, 'purchasing/purchase_receipt_detail.html', {'title': 'Purchase Receipt Detail'})

@login_required
def create_purchase_receipt(request):
    """Create purchase receipt placeholder"""
    return render(request, 'purchasing/purchase_receipt_form.html', {'title': 'Create Purchase Receipt'})

@login_required
def purchase_payment_list(request):
    """Purchase payment list placeholder"""
    return render(request, 'purchasing/purchase_payment_list.html', {'title': 'Purchase Payments'})

@login_required
def purchase_payment_detail(request, payment_id):
    """Purchase payment detail placeholder"""
    return render(request, 'purchasing/purchase_payment_detail.html', {'title': 'Purchase Payment Detail'})

@login_required
def create_purchase_payment(request):
    """Create purchase payment placeholder"""
    return render(request, 'purchasing/purchase_payment_form.html', {'title': 'Create Purchase Payment'})

@login_required
def purchase_bill_detail(request, bill_id):
    """Purchase bill detail placeholder"""
    bill = get_object_or_404(PurchaseBill, id=bill_id, company=request.user.profile.company)
    
    context = {
        'bill': bill,
        'title': f'Purchase Bill Detail - {bill.bill_number}'
    }
    return render(request, 'purchasing/purchase_bill_detail.html', context)

@login_required
def create_purchase_bill(request):
    """Create purchase bill placeholder"""
    if request.method == 'POST':
        form = PurchaseBillForm(request.POST)
        if form.is_valid():
            bill = form.save(commit=False)
            bill.company = request.user.profile.company
            bill.created_by = request.user
            
            # Generate bill number
            sequence = Sequence.objects.get_or_create(
                sequence_type='purchase_bill',
                defaults={'prefix': 'PB', 'current_number': 0}
            )[0]
            bill.bill_number = sequence.get_next_number()
            
            bill.save()
            messages.success(request, 'Purchase bill created successfully.')
            return redirect('purchasing:purchase_bill_detail', bill_id=bill.id)
    else:
        form = PurchaseBillForm()
        form.fields['supplier'].queryset = Supplier.objects.filter(
            company=request.user.profile.company,
            is_active=True,
            is_approved=True
        )
    
    context = {
        'form': form,
        'title': 'Create Purchase Bill'
    }
    return render(request, 'purchasing/purchase_bill_form.html', context)

@login_required
def approve_purchase_bill(request, bill_id):
    """Approve purchase bill placeholder"""
    bill = get_object_or_404(PurchaseBill, id=bill_id, company=request.user.profile.company)
    
    if request.method == 'POST':
        bill.status = 'approved'
        bill.approved_by = request.user
        bill.approved_date = timezone.now()
        bill.save()
        
        messages.success(request, 'Purchase bill approved successfully.')
        return redirect('purchasing:purchase_bill_detail', bill_id=bill.id)
    
    context = {
        'bill': bill,
        'title': f'Approve Purchase Bill - {bill.bill_number}'
    }
    return render(request, 'purchasing/approve_purchase_bill.html', context)

@login_required
def purchase_payment_create(request):
    """Create purchase payment placeholder"""
    if request.method == 'POST':
        form = PurchasePaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.company = request.user.profile.company
            payment.created_by = request.user
            
            # Generate payment number
            sequence = Sequence.objects.get_or_create(
                sequence_type='purchase_payment',
                defaults={'prefix': 'PP', 'current_number': 0}
            )[0]
            payment.payment_number = sequence.get_next_number()
            
            payment.save()
            messages.success(request, 'Purchase payment created successfully.')
            return redirect('purchasing:purchase_payment_detail', payment_id=payment.id)
    else:
        form = PurchasePaymentForm()
        form.fields['bill'].queryset = PurchaseBill.objects.filter(
            company=request.user.profile.company,
            status__in=['confirmed', 'partial_paid']
        )
    
    context = {
        'form': form,
        'title': 'Create Purchase Payment'
    }
    return render(request, 'purchasing/purchase_payment_form.html', context)

@login_required
def purchase_payment_detail(request, payment_id):
    """Purchase payment detail placeholder"""
    payment = get_object_or_404(PurchasePayment, id=payment_id, company=request.user.profile.company)
    
    context = {
        'payment': payment,
        'title': f'Purchase Payment Detail - {payment.payment_number}'
    }
    return render(request, 'purchasing/purchase_payment_detail.html', context)

@login_required
def purchase_payment_list(request):
    """Purchase payment list placeholder"""
    payments = PurchasePayment.objects.filter(
        company=request.user.profile.company
    ).select_related('bill').order_by('-payment_date')
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        payments = payments.filter(status=status)
    
    # Pagination
    paginator = Paginator(payments, 20)
    page = request.GET.get('page')
    payments = paginator.get_page(page)
    
    context = {
        'payments': payments,
        'status': status,
        'title': 'Purchase Payments - การชำระเงินซื้อ'
    }
    return render(request, 'purchasing/purchase_payment_list.html', context)

@login_required
def supplier_performance_report(request):
    """Supplier performance report placeholder"""
    suppliers = Supplier.objects.filter(company=request.user.profile.company, is_active=True)
    
    performance_data = []
    for supplier in suppliers:
        performance = {
            'supplier': supplier,
            'avg_quality': supplier.quality_rating,
            'avg_delivery': supplier.delivery_rating,
            'avg_service': supplier.service_rating,
            'total_orders': supplier.purchase_orders.filter(status='confirmed').count()
        }
        performance_data.append(performance)
    
    context = {
        'performance_data': performance_data,
        'title': 'Supplier Performance Report - รายงานประสิทธิภาพผู้จำหน่าย'
    }
    return render(request, 'purchasing/supplier_performance_report.html', context)