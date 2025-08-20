# accounting/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from core.models import BaseModel, Company, Sequence
# Create your models here.

class ChartOfAccount(BaseModel):
    """Chart of Accounts - ผังบัญชี"""
    ACCOUNT_TYPES = [
        ('asset', 'Asset - สินทรัพย์'),
        ('liability', 'Liability - หนี้สิน'),
        ('equity', 'Equity - ส่วนของเจ้าของ'),
        ('income', 'Income - รายได้'),
        ('expense', 'Expense - ค่าใช้จ่าย'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    parent_account = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_accounts')
    level = models.IntegerField(default=1)
    is_header = models.BooleanField(default=False)  # บัญชีหัวข้อ
    is_control = models.BooleanField(default=False)  # บัญชีควบคุม
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['company', 'code']
        ordering = ['code']
        
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_balance(self):
        """คำนวณยอดคงเหลือจาก Journal Entries"""
        from django.db.models import Sum
        debit_total = self.journal_entries.filter(entry_type='debit').aggregate(
            total=Sum('amount'))['total'] or 0
        credit_total = self.journal_entries.filter(entry_type='credit').aggregate(
            total=Sum('amount'))['total'] or 0
        
        if self.account_type in ['asset', 'expense']:
            return debit_total - credit_total
        else:  # liability, equity, income
            return credit_total - debit_total

class JournalEntry(BaseModel):
    """รายการบัญชี"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    entry_number = models.CharField(max_length=50)
    entry_date = models.DateField()
    reference = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('reversed', 'Reversed'),
    ], default='draft')
    posted_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    posted_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-entry_date', '-entry_number']
        
    def __str__(self):
        return f"{self.entry_number} - {self.description[:50]}"
    
    def post_entry(self, user):
        """Post journal entry"""
        if self.status == 'posted':
            raise ValueError("Entry already posted")
        
        # Validate debit = credit
        debit_total = self.journal_lines.filter(entry_type='debit').aggregate(
            total=models.Sum('amount'))['total'] or 0
        credit_total = self.journal_lines.filter(entry_type='credit').aggregate(
            total=models.Sum('amount'))['total'] or 0
        
        if debit_total != credit_total:
            raise ValueError(f"Debit ({debit_total}) must equal Credit ({credit_total})")
        
        self.status = 'posted'
        self.posted_by = user
        self.posted_date = timezone.now()
        self.save()
        
        # Update account balances
        for line in self.journal_lines.all():
            line.account.balance = line.account.get_balance()
            line.account.save()

class JournalLine(BaseModel):
    """รายการบัญชีแยกประเภท"""
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='journal_lines')
    account = models.ForeignKey(ChartOfAccount, on_delete=models.CASCADE, related_name='journal_entries')
    entry_type = models.CharField(max_length=10, choices=[
        ('debit', 'Debit'),
        ('credit', 'Credit'),
    ])
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    description = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        ordering = ['entry_type', 'account__code']
        
    def __str__(self):
        return f"{self.account.code} - {self.entry_type}: {self.amount:,.2f}"

class FiscalYear(BaseModel):
    """ปีบัญชี"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    year = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['company', 'year']
        
    def __str__(self):
        return f"FY {self.year} ({self.start_date} - {self.end_date})"

class AccountingPeriod(BaseModel):
    """งวดบัญชี"""
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name='periods')
    period_number = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['fiscal_year', 'period_number']
        ordering = ['fiscal_year', 'period_number']
        
    def __str__(self):
        return f"Period {self.period_number} - {self.fiscal_year.year}"

class Tax(BaseModel):
    """ภาษี"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    rate = models.DecimalField(max_digits=5, decimal_places=4, validators=[MinValueValidator(0), MaxValueValidator(1)])
    tax_account = models.ForeignKey(ChartOfAccount, on_delete=models.PROTECT)
    is_inclusive = models.BooleanField(default=False)  # ภาษีรวมในราคา
    
    class Meta:
        unique_together = ['company', 'code']
        
    def __str__(self):
        return f"{self.name} ({self.rate*100:.2f}%)"
    
    def calculate_tax(self, amount):
        """คำนวณภาษี"""
        if self.is_inclusive:
            # ภาษีรวมในราคา
            tax_amount = amount * self.rate / (1 + self.rate)
            base_amount = amount - tax_amount
        else:
            # ภาษีแยกจากราคา
            base_amount = amount
            tax_amount = amount * self.rate
        
        return {
            'base_amount': round(base_amount, 2),
            'tax_amount': round(tax_amount, 2),
            'total_amount': round(base_amount + tax_amount, 2)
        }