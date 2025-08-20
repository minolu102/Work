# inventory/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from core.models import BaseModel, Company, Category, Sequence
# Create your models here.

class ProductCategory(BaseModel):
    """หมวดหมู่สินค้า"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    parent_category = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    
    class Meta:
        unique_together = ['company', 'code']
        verbose_name_plural = "Product Categories"
        
    def __str__(self):
        return f"{self.code} - {self.name}"

class Brand(BaseModel):
    """ยี่ห้อสินค้า"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    logo = models.ImageField(upload_to='brands/', null=True, blank=True)
    
    class Meta:
        unique_together = ['company', 'code']
        
    def __str__(self):
        return self.name

class UnitOfMeasure(BaseModel):
    """หน่วยนับ"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    base_unit = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    conversion_factor = models.DecimalField(max_digits=10, decimal_places=4, default=1)
    
    class Meta:
        unique_together = ['company', 'code']
        
    def __str__(self):
        return f"{self.name} ({self.symbol})"

class Product(BaseModel):
    """สินค้า"""
    PRODUCT_TYPES = [
        ('product', 'Product'),
        ('service', 'Service'),
        ('consumable', 'Consumable'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='product')
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, null=True, blank=True)
    
    # Units
    base_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='base_products')
    purchase_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='purchase_products')
    sales_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='sales_products')
    
    # Pricing
    cost_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    sale_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='THB')
    
    # Inventory tracking
    track_inventory = models.BooleanField(default=True)
    quantity_on_hand = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    quantity_available = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    quantity_reserved = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    
    # Stock control
    reorder_level = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    maximum_stock = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    minimum_stock = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    
    # Product information
    barcode = models.CharField(max_length=100, unique=True, null=True, blank=True)
    internal_reference = models.CharField(max_length=100, null=True, blank=True)
    weight = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    volume = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    # Status flags
    can_be_sold = models.BooleanField(default=True)
    can_be_purchased = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['company', 'code']
        ordering = ['code']
        
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def update_stock_quantities(self):
        """อัพเดทจำนวนสินค้าคงคลัง"""
        stock_moves = self.stock_moves.filter(state='done')
        
        total_in = stock_moves.filter(move_type='in').aggregate(
            models.Sum('quantity'))['quantity__sum'] or 0
        total_out = stock_moves.filter(move_type='out').aggregate(
            models.Sum('quantity'))['quantity__sum'] or 0
        
        self.quantity_on_hand = total_in - total_out
        self.quantity_available = self.quantity_on_hand - self.quantity_reserved
        self.save(update_fields=['quantity_on_hand', 'quantity_available'])
    
    def is_low_stock(self):
        """ตรวจสอบว่าสินค้าใกล้หมด"""
        return self.quantity_on_hand <= self.reorder_level

class Warehouse(BaseModel):
    """คลังสินค้า"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    address = models.TextField()
    warehouse_type = models.CharField(max_length=20, choices=[
        ('main', 'Main Warehouse'),
        ('transit', 'Transit Warehouse'),
        ('production', 'Production Warehouse'),
        ('quality', 'Quality Control'),
    ], default='main')
    is_default = models.BooleanField(default=False)
    manager = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    
    class Meta:
        unique_together = ['company', 'code']
        
    def __str__(self):
        return f"{self.code} - {self.name}"

class Location(BaseModel):
    """ตำแหน่งในคลัง"""
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='locations')
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    location_type = models.CharField(max_length=20, choices=[
        ('storage', 'Storage'),
        ('receiving', 'Receiving'),
        ('shipping', 'Shipping'),
        ('quality', 'Quality Control'),
        ('production', 'Production'),
    ], default='storage')
    parent_location = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        unique_together = ['warehouse', 'code']
        
    def __str__(self):
        return f"{self.warehouse.code}/{self.code} - {self.name}"

class StockMove(BaseModel):
    """การเคลื่อนไหวสินค้า"""
    MOVE_TYPES = [
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('transfer', 'Transfer'),
        ('adjust', 'Adjustment'),
    ]
    
    STATE_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    reference = models.CharField(max_length=100)
    move_type = models.CharField(max_length=20, choices=MOVE_TYPES)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_moves')
    
    # Locations
    source_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='source_moves', null=True, blank=True)
    destination_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='destination_moves', null=True, blank=True)
    
    # Quantities
    quantity = models.DecimalField(max_digits=15, decimal_places=4, validators=[MinValueValidator(0)])
    unit_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Dates
    scheduled_date = models.DateTimeField()
    actual_date = models.DateTimeField(null=True, blank=True)
    
    # Status
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='draft')
    reason = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-scheduled_date']
        
    def __str__(self):
        return f"{self.reference} - {self.product.code} ({self.quantity})"
    
    def save(self, *args, **kwargs):
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)
        
        if self.state == 'done':
            self.product.update_stock_quantities()

class StockValuation(BaseModel):
    """การประเมินมูลค่าสินค้าคงคลัง"""
    VALUATION_METHODS = [
        ('fifo', 'FIFO - First In First Out'),
        ('lifo', 'LIFO - Last In First Out'),
        ('average', 'Weighted Average'),
        ('standard', 'Standard Cost'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='valuations')
    stock_move = models.ForeignKey(StockMove, on_delete=models.CASCADE, related_name='valuations')
    
    quantity = models.DecimalField(max_digits=15, decimal_places=4)
    unit_cost = models.DecimalField(max_digits=15, decimal_places=2)
    total_value = models.DecimalField(max_digits=15, decimal_places=2)
    valuation_method = models.CharField(max_length=20, choices=VALUATION_METHODS, default='average')
    
    remaining_qty = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    remaining_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.product.code} - {self.quantity} @ {self.unit_cost}"

class StockAdjustment(BaseModel):
    """การปรับปรุงสินค้าคงคลัง"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    adjustment_number = models.CharField(max_length=50, unique=True)
    adjustment_date = models.DateField()
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    reason = models.TextField()
    
    state = models.CharField(max_length=20, choices=[
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], default='draft')
    
    approved_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-adjustment_date']
        
    def __str__(self):
        return f"{self.adjustment_number} - {self.adjustment_date}"

class StockAdjustmentLine(BaseModel):
    """รายการปรับปรุงสินค้าคงคลัง"""
    adjustment = models.ForeignKey(StockAdjustment, on_delete=models.CASCADE, related_name='adjustment_lines')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    
    theoretical_qty = models.DecimalField(max_digits=15, decimal_places=4, default=0)  # จำนวนตามระบบ
    actual_qty = models.DecimalField(max_digits=15, decimal_places=4, default=0)       # จำนวนจริง
    difference_qty = models.DecimalField(max_digits=15, decimal_places=4, default=0)   # ส่วนต่าง
    
    unit_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    reason = models.CharField(max_length=255, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        self.difference_qty = self.actual_qty - self.theoretical_qty
        self.total_value = self.difference_qty * self.unit_cost
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.product.code} - Diff: {self.difference_qty}"

