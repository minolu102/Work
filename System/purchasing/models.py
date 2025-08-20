# purchasing/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from core.models import BaseModel, Company, Sequence
from inventory.models import Product, Warehouse
from accounting.models import Tax, ChartOfAccount
# Create your models here.

class Supplier(BaseModel):
    """ผู้จำหน่าย/คู่ค้า"""
    SUPPLIER_TYPES = [
        ('individual', 'Individual'),
        ('company', 'Company'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    supplier_type = models.CharField(max_length=20, choices=SUPPLIER_TYPES, default='company')
    
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
    payable_account = models.ForeignKey(ChartOfAccount, on_delete=models.PROTECT, null=True, blank=True)
    purchase_representative = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    
    # Rating and performance
    quality_rating = models.IntegerField(default=5, choices=[(i, i) for i in range(1, 6)])
    delivery_rating = models.IntegerField(default=5, choices=[(i, i) for i in range(1, 6)])
    service_rating = models.IntegerField(default=5, choices=[(i, i) for i in range(1, 6)])
    
    # Status
    is_approved = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    block_reason = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        unique_together = ['company', 'code']
        ordering = ['code']
        
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_outstanding_balance(self):
        """ยอดค้างจ่าย"""
        from django.db.models import Sum
        bills = self.purchase_bills.filter(
            status__in=['confirmed', 'partial_paid']
        )
        return bills.aggregate(
            total=Sum('outstanding_amount')
        )['total'] or 0
    
    def get_average_rating(self):
        """คะแนนเฉลี่ย"""
        return (self.quality_rating + self.delivery_rating + self.service_rating) / 3

class PurchaseOrder(BaseModel):
    """ใบสั่งซื้อ"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent to Supplier'),
        ('confirmed', 'Confirmed'),
        ('received', 'Received'),
        ('billed', 'Billed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    po_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    
    # Dates
    order_date = models.DateField()
    expected_delivery_date = models.DateField(null=True, blank=True)
    
    # Order details
    reference = models.CharField(max_length=100, null=True, blank=True)
    supplier_reference = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Financial
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    purchase_representative = models.ForeignKey(User, on_delete=models.PROTECT)
    
    # Delivery
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    delivery_address = models.TextField(null=True, blank=True)
    
    # Approval workflow
    requires_approval = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='approved_pos')
    approved_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-order_date', '-po_number']
        
    def __str__(self):
        return f"{self.po_number} - {self.supplier.name}"
    
    def calculate_totals(self):
        """คำนวณยอดรวม"""
        lines = self.po_lines.all()
        
        self.subtotal = sum(line.line_total for line in lines)
        self.discount_amount = self.subtotal * (self.supplier.discount_percent / 100)
        
        # Calculate tax
        self.tax_amount = 0
        for line in lines:
            if line.tax:
                tax_calc = line.tax.calculate_tax(line.line_total)
                self.tax_amount += tax_calc['tax_amount']
        
        self.total_amount = self.subtotal - self.discount_amount + self.tax_amount
        self.save(update_fields=['subtotal', 'discount_amount', 'tax_amount', 'total_amount'])
    
    def can_be_received(self):
        """ตรวจสอบว่าสามารถรับสินค้าได้หรือไม่"""
        return self.status in ['confirmed', 'received']

class PurchaseOrderLine(BaseModel):
    """รายการในใบสั่งซื้อ"""
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='po_lines')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    description = models.CharField(max_length=255, null=True, blank=True)
    quantity = models.DecimalField(max_digits=15, decimal_places=4, validators=[MinValueValidator(0)])
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    line_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    tax = models.ForeignKey(Tax, on_delete=models.PROTECT, null=True, blank=True)
    
    # Delivery tracking
    received_quantity = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    billed_quantity = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    
    # Expected delivery
    expected_delivery_date = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['id']
        
    def save(self, *args, **kwargs):
        # Calculate line total
        if self.discount_percent > 0:
            self.discount_amount = self.quantity * self.unit_price * (self.discount_percent / 100)
        
        self.line_total = (self.quantity * self.unit_price) - self.discount_amount
        super().save(*args, **kwargs)
        
        # Update PO totals
        self.po.calculate_totals()
    
    def get_pending_quantity(self):
        """จำนวนที่ยังไม่ได้รับ"""
        return self.quantity - self.received_quantity
    
    def __str__(self):
        return f"{self.product.code} x {self.quantity}"

class PurchaseReceipt(BaseModel):
    """ใบรับสินค้า"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('billed', 'Billed'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    receipt_number = models.CharField(max_length=50, unique=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='receipts')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    
    # Dates
    receipt_date = models.DateField()
    delivery_date = models.DateField(null=True, blank=True)
    
    # Receipt details
    supplier_delivery_note = models.CharField(max_length=100, null=True, blank=True)
    supplier_invoice_number = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    # Transportation
    vehicle_number = models.CharField(max_length=50, null=True, blank=True)
    driver_name = models.CharField(max_length=255, null=True, blank=True)
    driver_phone = models.CharField(max_length=20, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Quality control
    qc_required = models.BooleanField(default=False)
    qc_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('partial', 'Partial'),
    ], null=True, blank=True)
    qc_notes = models.TextField(null=True, blank=True)
    qc_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='qc_receipts')
    qc_date = models.DateTimeField(null=True, blank=True)
    
    # Approval
    received_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='received_orders')
    
    class Meta:
        ordering = ['-receipt_date', '-receipt_number']
        
    def __str__(self):
        return f"{self.receipt_number} - {self.supplier.name}"

class PurchaseReceiptLine(BaseModel):
    """รายการในใบรับสินค้า"""
    receipt = models.ForeignKey(PurchaseReceipt, on_delete=models.CASCADE, related_name='receipt_lines')
    po_line = models.ForeignKey(PurchaseOrderLine, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    quantity_ordered = models.DecimalField(max_digits=15, decimal_places=4)
    quantity_received = models.DecimalField(max_digits=15, decimal_places=4)
    quantity_rejected = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    
    # Location tracking
    destination_location = models.ForeignKey('inventory.Location', on_delete=models.PROTECT)
    
    # Quality control
    qc_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
    ], default='pending')
    rejection_reason = models.CharField(max_length=255, null=True, blank=True)
    
    notes = models.CharField(max_length=255, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update PO line received quantity
        self.po_line.received_quantity = sum(
            line.quantity_received for line in self.po_line.purchasereceiptline_set.all()
        )
        self.po_line.save()
    
    def __str__(self):
        return f"{self.product.code} - Received: {self.quantity_received}"

class PurchaseBill(BaseModel):
    """ใบเสนอซื้อ/บิล"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
        ('partial_paid', 'Partially Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    bill_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_bills')
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='bills', null=True, blank=True)
    
    # Dates
    bill_date = models.DateField()
    due_date = models.DateField()
    
    # Bill details
    supplier_invoice_number = models.CharField(max_length=100)
    reference = models.CharField(max_length=100, null=True, blank=True)
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
        ordering = ['-bill_date', '-bill_number']
        unique_together = ['company', 'supplier_invoice_number', 'supplier']
        
    def __str__(self):
        return f"{self.bill_number} - {self.supplier.name}"
    
    def calculate_totals(self):
        """คำนวณยอดรวมบิล"""
        lines = self.bill_lines.all()
        
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

class PurchaseBillLine(BaseModel):
    """รายการในบิล"""
    bill = models.ForeignKey(PurchaseBill, on_delete=models.CASCADE, related_name='bill_lines')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    po_line = models.ForeignKey(PurchaseOrderLine, on_delete=models.CASCADE, null=True, blank=True)
    
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=15, decimal_places=4, validators=[MinValueValidator(0)])
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    line_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    tax = models.ForeignKey(Tax, on_delete=models.PROTECT, null=True, blank=True)
    
    # Expense account
    expense_account = models.ForeignKey(ChartOfAccount, on_delete=models.PROTECT, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        # Calculate line total
        if self.discount_percent > 0:
            self.discount_amount = self.quantity * self.unit_price * (self.discount_percent / 100)
        
        self.line_total = (self.quantity * self.unit_price) - self.discount_amount
        super().save(*args, **kwargs)
        
        # Update bill totals
        self.bill.calculate_totals()
    
    def __str__(self):
        return f"{self.product.code} x {self.quantity}"

class PurchasePayment(BaseModel):
    """การจ่ายชำระเงิน"""
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
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='payments')
    
    # Payment details
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    reference = models.CharField(max_length=100, null=True, blank=True)
    
    # Bank details
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
        return f"{self.payment_number} - {self.supplier.name} - {self.amount:,.2f}"

class PurchasePaymentAllocation(BaseModel):
    """การจัดสรรเงินจ่าย"""
    payment = models.ForeignKey(PurchasePayment, on_delete=models.CASCADE, related_name='allocations')
    bill = models.ForeignKey(PurchaseBill, on_delete=models.CASCADE, related_name='payment_allocations')
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    
    class Meta:
        unique_together = ['payment', 'bill']
        
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update bill paid amount
        total_allocated = self.bill.payment_allocations.aggregate(
            total=models.Sum('amount'))['total'] or 0
        self.bill.paid_amount = total_allocated
        self.bill.calculate_totals()
    
    def __str__(self):
        return f"{self.payment.payment_number} -> {self.bill.bill_number}: {self.amount:,.2f}"

class SupplierEvaluation(BaseModel):
    """การประเมินผู้จำหน่าย"""
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='evaluations')
    evaluation_period_start = models.DateField()
    evaluation_period_end = models.DateField()
    
    # Rating criteria (1-5 scale)
    quality_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    delivery_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    service_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    pricing_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    communication_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    
    # Performance metrics
    on_time_delivery_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    quality_defect_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    response_time_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Comments
    strengths = models.TextField(null=True, blank=True)
    weaknesses = models.TextField(null=True, blank=True)
    recommendations = models.TextField(null=True, blank=True)
    
    # Overall assessment
    overall_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    continue_partnership = models.BooleanField(default=True)
    
    evaluated_by = models.ForeignKey(User, on_delete=models.PROTECT)
    
    def save(self, *args, **kwargs):
        # Calculate overall rating
        self.overall_rating = (
            self.quality_rating + self.delivery_rating + self.service_rating +
            self.pricing_rating + self.communication_rating
        ) / 5
        super().save(*args, **kwargs)
        
        # Update supplier ratings
        self.supplier.quality_rating = self.quality_rating
        self.supplier.delivery_rating = self.delivery_rating
        self.supplier.service_rating = self.service_rating
        self.supplier.save()
    
    def __str__(self):
        return f"{self.supplier.name} - {self.evaluation_period_start} to {self.evaluation_period_end}"