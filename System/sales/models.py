# sales/models.py
from django.db import models
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from core.models import BaseModel, Company, Address, Contact, Sequence
from inventory.models import Product, Warehouse
from accounting.models import Tax, ChartOfAccount
# Create your models here.

class Customer(BaseModel):
    """ลูกค้า"""
    CUSTOMER_TYPES = [
        ('individual', 'Individual'),
        ('company', 'Company'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES, default='individual')
    
    # Contact information
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    mobile = models.CharField(max_length=20, null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    
    # Business information
    tax_id = models.CharField(max_length=20, null=True, blank=True)
    registration_number = models.CharField(max_length=50, null=True, blank=True)
    
    # Financial settings
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    payment_terms = models.IntegerField(default=30, help_text="Payment terms in days")
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Account settings
    receivable_account = models.ForeignKey(ChartOfAccount, on_delete=models.PROTECT, null=True, blank=True)
    sales_representative = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    
    # Status
    is_blocked = models.BooleanField(default=False)
    block_reason = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        unique_together = ['company', 'code']
        ordering = ['code']
        
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_outstanding_balance(self):
        """ยอดค้างชำระ"""
        from django.db.models import Sum
        invoices = self.sales_invoices.filter(
            status__in=['confirmed', 'partial_paid']
        )
        return invoices.aggregate(
            total=Sum('outstanding_amount')
        )['total'] or 0
    
    def get_credit_available(self):
        """วงเงินคงเหลือ"""
        outstanding = self.get_outstanding_balance()
        return self.credit_limit - outstanding

class SalesOrder(BaseModel):
    """ใบสั่งขาย"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('delivered', 'Delivered'),
        ('invoiced', 'Invoiced'),
        ('cancelled', 'Cancelled'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    order_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sales_orders')
    
    # Dates
    order_date = models.DateField()
    expected_delivery_date = models.DateField(null=True, blank=True)
    
    # Order details
    reference = models.CharField(max_length=100, null=True, blank=True)
    customer_po = models.CharField(max_length=100, null=True, blank=True, verbose_name="Customer PO")
    notes = models.TextField(null=True, blank=True)
    
    # Financial
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    sales_representative = models.ForeignKey(User, on_delete=models.PROTECT)
    
    # Delivery
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    delivery_address = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-order_date', '-order_number']
        
    def __str__(self):
        return f"{self.order_number} - {self.customer.name}"
    
    def calculate_totals(self):
        """คำนวณยอดรวม"""
        lines = self.order_lines.all()
        
        self.subtotal = sum(line.line_total for line in lines)
        self.discount_amount = self.subtotal * (self.customer.discount_percent / 100)
        
        # Calculate tax
        self.tax_amount = 0
        for line in lines:
            if line.tax:
                tax_calc = line.tax.calculate_tax(line.line_total)
                self.tax_amount += tax_calc['tax_amount']
        
        self.total_amount = self.subtotal - self.discount_amount + self.tax_amount
        self.save(update_fields=['subtotal', 'discount_amount', 'tax_amount', 'total_amount'])

class SalesOrderLine(BaseModel):
    """รายการในใบสั่งขาย"""
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='order_lines')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    description = models.CharField(max_length=255, null=True, blank=True)
    quantity = models.DecimalField(max_digits=15, decimal_places=4, validators=[MinValueValidator(0)])
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    line_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    tax = models.ForeignKey(Tax, on_delete=models.PROTECT, null=True, blank=True)
    
    # Delivery tracking
    delivered_quantity = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    invoiced_quantity = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    
    class Meta:
        ordering = ['id']
        
    def save(self, *args, **kwargs):
        # Calculate line total
        if self.discount_percent > 0:
            self.discount_amount = self.quantity * self.unit_price * (self.discount_percent / 100)
        
        self.line_total = (self.quantity * self.unit_price) - self.discount_amount
        super().save(*args, **kwargs)
        
        # Update order totals
        self.order.calculate_totals()
    
    def __str__(self):
        return f"{self.product.code} x {self.quantity}"

class DeliveryOrder(BaseModel):
    """ใบส่งสินค้า"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('ready', 'Ready to Deliver'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    delivery_number = models.CharField(max_length=50, unique=True)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='delivery_orders')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    
    # Dates
    delivery_date = models.DateField()
    scheduled_delivery = models.DateTimeField(null=True, blank=True)
    actual_delivery = models.DateTimeField(null=True, blank=True)
    
    # Delivery details
    delivery_address = models.TextField()
    delivery_contact = models.CharField(max_length=255, null=True, blank=True)
    delivery_phone = models.CharField(max_length=20, null=True, blank=True)
    
    # Transportation
    vehicle_number = models.CharField(max_length=50, null=True, blank=True)
    driver_name = models.CharField(max_length=255, null=True, blank=True)
    driver_phone = models.CharField(max_length=20, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(null=True, blank=True)
    
    # Signatures
    delivered_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='deliveries_made')
    received_by_name = models.CharField(max_length=255, null=True, blank=True)
    received_by_signature = models.ImageField(upload_to='signatures/', null=True, blank=True)
    
    class Meta:
        ordering = ['-delivery_date', '-delivery_number']
        
    def __str__(self):
        return f"{self.delivery_number} - {self.customer.name}"

class DeliveryOrderLine(BaseModel):
    """รายการในใบส่งสินค้า"""
    delivery_order = models.ForeignKey(DeliveryOrder, on_delete=models.CASCADE, related_name='delivery_lines')
    order_line = models.ForeignKey(SalesOrderLine, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    quantity_ordered = models.DecimalField(max_digits=15, decimal_places=4)
    quantity_delivered = models.DecimalField(max_digits=15, decimal_places=4)
    quantity_returned = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    
    # Location tracking
    source_location = models.ForeignKey('inventory.Location', on_delete=models.PROTECT)
    
    notes = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__(self):
        return f"{self.product.code} - Delivered: {self.quantity_delivered}"

class SalesInvoice(BaseModel):
    """ใบกำกับภาษี/ใบแจ้งหนี้"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
        ('partial_paid', 'Partially Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    invoice_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sales_invoices')
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='invoices', null=True, blank=True)
    
    # Dates
    invoice_date = models.DateField()
    due_date = models.DateField()
    
    # Invoice details
    reference = models.CharField(max_length=100, null=True, blank=True)
    customer_po = models.CharField(max_length=100, null=True, blank=True)
    payment_terms = models.CharField(max_length=255, null=True, blank=True)
    
    # Financial amounts
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    outstanding_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Accounting
    journal_entry = models.ForeignKey('accounting.JournalEntry', on_delete=models.PROTECT, null=True, blank=True)
    
    class Meta:
        ordering = ['-invoice_date', '-invoice_number']
        
    def __str__(self):
        return f"{self.invoice_number} - {self.customer.name}"
    
    def calculate_totals(self):
        """คำนวณยอดรวมใบกำกับภาษี"""
        lines = self.invoice_lines.all()
        
        self.subtotal = sum(line.line_total for line in lines)
        
        # Calculate tax
        self.tax_amount = 0
        for line in lines:
            if line.tax:
                tax_calc = line.tax.calculate_tax(line.line_total)
                self.tax_amount += tax_calc['tax_amount']
        
        self.total_amount = self.subtotal - self.discount_amount + self.tax_amount
        self.outstanding_amount = self.total_amount - self.paid_amount
        
        # Update status based on payment
        if self.paid_amount == 0:
            if self.due_date < timezone.now().date():
                self.status = 'overdue'
            elif self.status not in ['draft']:
                self.status = 'confirmed'
        elif self.paid_amount >= self.total_amount:
            self.status = 'paid'
        else:
            self.status = 'partial_paid'
        
        self.save(update_fields=[
            'subtotal', 'tax_amount', 'total_amount', 'outstanding_amount', 'status'
        ])

class SalesInvoiceLine(BaseModel):
    """รายการในใบกำกับภาษี"""
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='invoice_lines')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    order_line = models.ForeignKey(SalesOrderLine, on_delete=models.CASCADE, null=True, blank=True)
    
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=15, decimal_places=4, validators=[MinValueValidator(0)])
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    line_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    tax = models.ForeignKey(Tax, on_delete=models.PROTECT, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        # Calculate line total
        if self.discount_percent > 0:
            self.discount_amount = self.quantity * self.unit_price * (self.discount_percent / 100)
        
        self.line_total = (self.quantity * self.unit_price) - self.discount_amount
        super().save(*args, **kwargs)
        
        # Update invoice totals
        self.invoice.calculate_totals()
    
    def __str__(self):
        return f"{self.product.code} x {self.quantity}"

class SalesPayment(BaseModel):
    """การรับชำระเงิน"""
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('credit_card', 'Credit Card'),
        ('mobile_banking', 'Mobile Banking'),
        ('e_wallet', 'E-Wallet'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    payment_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payments')
    
    # Payment details
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    reference = models.CharField(max_length=100, null=True, blank=True)
    
    # Bank details (for non-cash payments)
    bank_account = models.ForeignKey(ChartOfAccount, on_delete=models.PROTECT, null=True, blank=True)
    cheque_number = models.CharField(max_length=50, null=True, blank=True)
    cheque_date = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('reconciled', 'Reconciled'),
        ('bounced', 'Bounced'),
    ], default='draft')
    
    notes = models.TextField(null=True, blank=True)
    
    # Accounting
    journal_entry = models.ForeignKey('accounting.JournalEntry', on_delete=models.PROTECT, null=True, blank=True)
    
    class Meta:
        ordering = ['-payment_date', '-payment_number']
        
    def __str__(self):
        return f"{self.payment_number} - {self.customer.name} - {self.amount:,.2f}"

class SalesPaymentAllocation(BaseModel):
    """การจัดสรรเงินรับชำระ"""
    payment = models.ForeignKey(SalesPayment, on_delete=models.CASCADE, related_name='allocations')
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='payment_allocations')
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    
    class Meta:
        unique_together = ['payment', 'invoice']
        
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update invoice paid amount
        total_allocated = self.invoice.payment_allocations.aggregate(
            total=models.Sum('amount'))['total'] or 0
        self.invoice.paid_amount = total_allocated
        self.invoice.calculate_totals()
    
    def __str__(self):
        return f"{self.payment.payment_number} -> {self.invoice.invoice_number}: {self.amount:,.2f}"