# inventory/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q, F
from django.utils import timezone
from django.core.paginator import Paginator
from .models import Product, ProductCategory, Warehouse, StockMove, StockAdjustment
from .forms import ProductForm, StockMoveForm, StockAdjustmentForm

# Create your views here.

@login_required
def product_list(request):
    """รายการสินค้า"""
    products = Product.objects.filter(
        company=request.user.profile.company,
        is_active=True
    ).select_related('category', 'brand').order_by('code')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        products = products.filter(
            Q(code__icontains=search) |
            Q(name__icontains=search) |
            Q(barcode__icontains=search)
        )
    
    # Filter by category
    category_id = request.GET.get('category', '')
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Filter by low stock
    low_stock = request.GET.get('low_stock', '')
    if low_stock:
        products = products.filter(quantity_on_hand__lte=F('reorder_level'))
    
    # Pagination
    paginator = Paginator(products, 20)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    categories = ProductCategory.objects.filter(
        company=request.user.profile.company,
        is_active=True
    )
    
    context = {
        'products': products,
        'categories': categories,
        'search': search,
        'category_id': category_id,
        'low_stock': low_stock,
        'title': 'Product List - รายการสินค้า'
    }
    return render(request, 'inventory/product_list.html', context)

@login_required
def product_detail(request, product_id):
    """รายละเอียดสินค้า"""
    product = get_object_or_404(
        Product,
        id=product_id,
        company=request.user.profile.company
    )
    
    # Stock movements
    stock_moves = product.stock_moves.select_related(
        'source_location__warehouse',
        'destination_location__warehouse'
    ).filter(state='done').order_by('-actual_date')[:20]
    
    # Stock levels by warehouse
    warehouses = Warehouse.objects.filter(
        company=request.user.profile.company,
        is_active=True
    )
    
    warehouse_stock = []
    for warehouse in warehouses:
        stock_in = product.stock_moves.filter(
            destination_location__warehouse=warehouse,
            state='done'
        ).aggregate(Sum('quantity'))['quantity__sum'] or 0
        
        stock_out = product.stock_moves.filter(
            source_location__warehouse=warehouse,
            state='done'
        ).aggregate(Sum('quantity'))['quantity__sum'] or 0
        
        current_stock = stock_in - stock_out
        
        warehouse_stock.append({
            'warehouse': warehouse,
            'current_stock': current_stock
        })
    
    context = {
        'product': product,
        'stock_moves': stock_moves,
        'warehouse_stock': warehouse_stock,
        'title': f'Product Details - {product.name}'
    }
    return render(request, 'inventory/product_detail.html', context)

@login_required
def stock_movements(request):
    """การเคลื่อนไหวสต็อก"""
    moves = StockMove.objects.filter(
        company=request.user.profile.company
    ).select_related(
        'product', 'source_location', 'destination_location'
    ).order_by('-scheduled_date')
    
    # Filter by move type
    move_type = request.GET.get('move_type', '')
    if move_type:
        moves = moves.filter(move_type=move_type)
    
    # Filter by state
    state = request.GET.get('state', '')
    if state:
        moves = moves.filter(state=state)
    
    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        moves = moves.filter(scheduled_date__gte=date_from)
    if date_to:
        moves = moves.filter(scheduled_date__lte=date_to)
    
    # Pagination
    paginator = Paginator(moves, 20)
    page = request.GET.get('page')
    moves = paginator.get_page(page)
    
    context = {
        'moves': moves,
        'move_type': move_type,
        'state': state,
        'date_from': date_from,
        'date_to': date_to,
        'title': 'Stock Movements - การเคลื่อนไหวสต็อก'
    }
    return render(request, 'inventory/stock_movements.html', context)

@login_required
def create_stock_adjustment(request):
    """สร้างการปรับปรุงสต็อก"""
    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            adjustment = form.save(commit=False)
            adjustment.company = request.user.profile.company
            adjustment.created_by = request.user
            
            # Generate adjustment number
            sequence = Sequence.objects.get_or_create(
                sequence_type='stock_adjustment',
                defaults={'prefix': 'ADJ', 'current_number': 0}
            )[0]
            adjustment.adjustment_number = sequence.get_next_number()
            adjustment.save()
            
            messages.success(request, 'Stock adjustment created successfully.')
            return redirect('inventory:stock_adjustment_detail', adjustment_id=adjustment.id)
    else:
        form = StockAdjustmentForm()
        form.fields['warehouse'].queryset = Warehouse.objects.filter(
            company=request.user.profile.company,
            is_active=True
        )
    
    context = {
        'form': form,
        'title': 'Create Stock Adjustment'
    }
    return render(request, 'inventory/stock_adjustment_form.html', context)

@login_required
def inventory_report(request):
    """รายงานสินค้าคงคลัง"""
    products = Product.objects.filter(
        company=request.user.profile.company,
        is_active=True,
        track_inventory=True
    ).select_related('category', 'brand')
    
    # Calculate totals
    total_products = products.count()
    total_value = sum(p.quantity_on_hand * p.cost_price for p in products)
    low_stock_count = sum(1 for p in products if p.is_low_stock())
    
    # Group by category
    category_summary = {}
    for product in products:
        cat_name = product.category.name
        if cat_name not in category_summary:
            category_summary[cat_name] = {
                'count': 0,
                'total_qty': 0,
                'total_value': 0
            }
        category_summary[cat_name]['count'] += 1
        category_summary[cat_name]['total_qty'] += product.quantity_on_hand
        category_summary[cat_name]['total_value'] += product.quantity_on_hand * product.cost_price
    
    context = {
        'products': products,
        'total_products': total_products,
        'total_value': total_value,
        'low_stock_count': low_stock_count,
        'category_summary': category_summary,
        'title': 'Inventory Report - รายงานสินค้าคงคลัง'
    }
    return render(request, 'inventory/inventory_report.html', context)

@login_required
def create_product(request):
    """Create product placeholder"""
    return render(request, 'inventory/product_form.html', {'title': 'Create Product'})

@login_required
def create_stock_move(request):
    """Create stock move placeholder"""
    return render(request, 'inventory/stock_move_form.html', {'title': 'Create Stock Move'})

@login_required
def stock_adjustments(request):
    """Stock adjustments list placeholder"""
    return render(request, 'inventory/stock_adjustments.html', {'title': 'Stock Adjustments'})

@login_required
def stock_adjustment_detail(request, adjustment_id):
    """Stock adjustment detail placeholder"""
    return render(request, 'inventory/stock_adjustment_detail.html', {'title': 'Stock Adjustment Detail'})

@login_required
def warehouse_list(request):
    """Warehouse list placeholder"""
    warehouses = Warehouse.objects.filter(
        company=request.user.profile.company,
        is_active=True
    )
    return render(request, 'inventory/warehouse_list.html', {
        'warehouses': warehouses,
        'title': 'Warehouse List'
    })

@login_required
def warehouse_detail(request, warehouse_id):
    """Warehouse detail placeholder"""
    warehouse = get_object_or_404(
        Warehouse,
        id=warehouse_id,
        company=request.user.profile.company,
        is_active=True
    )
    return render(request, 'inventory/warehouse_detail.html', {
        'warehouse': warehouse,
        'title': f'Warehouse Detail - {warehouse.name}'
    })

@login_required
def stock_valuation_report(request):
    """Stock valuation report placeholder"""
    return render(request, 'inventory/stock_valuation_report.html', {'title': 'Stock Valuation Report'})