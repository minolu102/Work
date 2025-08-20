# hr/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from core.models import BaseModel, Company, Address, Contact
from accounting.models import ChartOfAccount

class Department(BaseModel):
    """แผนก"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    parent_department = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_departments')
    manager = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='managed_departments')
    
    # Budget and cost center
    cost_center_code = models.CharField(max_length=20, null=True, blank=True)
    annual_budget = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['company', 'code']
        ordering = ['code']
        
    def __str__(self):
        return f"{self.code} - {self.name}"

class Position(BaseModel):
    """ตำแหน่งงาน"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='positions')
    
    # Job specifications
    level = models.CharField(max_length=50, choices=[
        ('entry', 'Entry Level'),
        ('junior', 'Junior'),
        ('senior', 'Senior'),
        ('supervisor', 'Supervisor'),
        ('manager', 'Manager'),
        ('director', 'Director'),
        ('executive', 'Executive'),
    ], default='entry')
    
    # Salary range
    min_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    max_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Requirements
    education_required = models.CharField(max_length=100, null=True, blank=True)
    experience_years = models.IntegerField(default=0)
    skills_required = models.TextField(null=True, blank=True)
    
    class Meta:
        unique_together = ['company', 'code']
        ordering = ['department', 'level', 'name']
        
    def __str__(self):
        return f"{self.name} - {self.department.name}"

class Employee(BaseModel):
    """พนักงาน"""
    EMPLOYMENT_TYPES = [
        ('permanent', 'Permanent'),
        ('contract', 'Contract'),
        ('probation', 'Probation'),
        ('part_time', 'Part Time'),
        ('consultant', 'Consultant'),
    ]
    
    MARITAL_STATUS = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    employee_id = models.CharField(max_length=50, unique=True)
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    thai_first_name = models.CharField(max_length=100, null=True, blank=True)
    thai_last_name = models.CharField(max_length=100, null=True, blank=True)
    nickname = models.CharField(max_length=50, null=True, blank=True)
    
    # Identity
    national_id = models.CharField(max_length=13, unique=True)
    passport_number = models.CharField(max_length=20, null=True, blank=True)
    
    # Contact Information
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    mobile = models.CharField(max_length=20, null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=255, null=True, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, null=True, blank=True)
    
    # Personal Details
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS, default='single')
    nationality = models.CharField(max_length=100, default='Thai')
    religion = models.CharField(max_length=100, null=True, blank=True)
    
    # Employment Information
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    position = models.ForeignKey(Position, on_delete=models.PROTECT)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPES, default='permanent')
    
    # Employment Dates
    hire_date = models.DateField()
    probation_end_date = models.DateField(null=True, blank=True)
    contract_start_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True)
    termination_date = models.DateField(null=True, blank=True)
    
    # Supervisor
    supervisor = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='subordinates')
    
    # Bank Information
    bank_account_number = models.CharField(max_length=20, null=True, blank=True)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    bank_branch = models.CharField(max_length=100, null=True, blank=True)
    
    # Tax Information
    tax_id = models.CharField(max_length=13, null=True, blank=True)
    social_security_number = models.CharField(max_length=20, null=True, blank=True)
    
    # Photo
    photo = models.ImageField(upload_to='employees/photos/', null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    termination_reason = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['employee_id']
        
    def __str__(self):
        return f"{self.employee_id} - {self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def thai_full_name(self):
        if self.thai_first_name and self.thai_last_name:
            return f"{self.thai_first_name} {self.thai_last_name}"
        return self.full_name

class Salary(BaseModel):
    """เงินเดือน"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salaries')
    effective_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    # Basic Salary
    basic_salary = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Allowances
    position_allowance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    transportation_allowance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    meal_allowance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    housing_allowance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    phone_allowance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Overtime rates (per hour)
    overtime_rate_weekday = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    overtime_rate_weekend = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    overtime_rate_holiday = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Benefits
    provident_fund_employee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    provident_fund_company_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Deductions
    social_security_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    tax_exemption_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    is_current = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-effective_date']
        
    def __str__(self):
        return f"{self.employee.full_name} - {self.basic_salary:,.2f} (from {self.effective_date})"
    
    @property
    def total_allowances(self):
        return (
            self.position_allowance + self.transportation_allowance +
            self.meal_allowance + self.housing_allowance +
            self.phone_allowance + self.other_allowances
        )
    
    @property
    def gross_salary(self):
        return self.basic_salary + self.total_allowances

class Attendance(BaseModel):
    """การเข้าออกงาน"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    
    # Check-in/out times
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    
    # Break times
    break_start = models.TimeField(null=True, blank=True)
    break_end = models.TimeField(null=True, blank=True)
    
    # Working hours
    regular_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('early_leave', 'Early Leave'),
        ('half_day', 'Half Day'),
        ('sick_leave', 'Sick Leave'),
        ('annual_leave', 'Annual Leave'),
        ('business_leave', 'Business Leave'),
        ('maternity_leave', 'Maternity Leave'),
        ('public_holiday', 'Public Holiday'),
    ], default='present')
    
    # Late/Early details
    late_minutes = models.IntegerField(default=0)
    early_leave_minutes = models.IntegerField(default=0)
    
    # Location (if GPS tracking)
    check_in_location = models.CharField(max_length=255, null=True, blank=True)
    check_out_location = models.CharField(max_length=255, null=True, blank=True)
    
    notes = models.TextField(null=True, blank=True)
    
    class Meta:
        unique_together = ['employee', 'date']
        ordering = ['-date', 'employee']
        
    def __str__(self):
        return f"{self.employee.full_name} - {self.date} ({self.status})"

class LeaveType(BaseModel):
    """ประเภทการลา"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    description = models.TextField(null=True, blank=True)
    
    # Allocation settings
    days_per_year = models.IntegerField(default=0)
    max_consecutive_days = models.IntegerField(default=0)
    advance_notice_days = models.IntegerField(default=1)
    
    # Rules
    requires_approval = models.BooleanField(default=True)
    requires_medical_certificate = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=True)
    
    # Carry forward
    allow_carry_forward = models.BooleanField(default=False)
    max_carry_forward_days = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['company', 'code']
        ordering = ['name']
        
    def __str__(self):
        return self.name

class LeaveRequest(BaseModel):
    """คำขอลา"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    
    # Leave period
    start_date = models.DateField()
    end_date = models.DateField()
    days_requested = models.IntegerField()
    
    # Details
    reason = models.TextField()
    emergency_contact = models.CharField(max_length=255, null=True, blank=True)
    medical_certificate = models.FileField(upload_to='leave/medical/', null=True, blank=True)
    
    # Approval workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    submitted_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='approved_leaves')
    approved_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    
    # Coverage
    covering_employee = models.ForeignKey(Employee, on_delete=models.PROTECT, null=True, blank=True, related_name='covering_leaves')
    handover_notes = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-start_date', '-created_at']
        
    def __str__(self):
        return f"{self.employee.full_name} - {self.leave_type.name} ({self.start_date} to {self.end_date})"
    
    def save(self, *args, **kwargs):
        # Calculate days requested
        if self.start_date and self.end_date:
            self.days_requested = (self.end_date - self.start_date).days + 1
        super().save(*args, **kwargs)

class Payroll(BaseModel):
    """การจ่ายเงินเดือน"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    payroll_period_start = models.DateField()
    payroll_period_end = models.DateField()
    payment_date = models.DateField()
    
    description = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Totals
    total_employees = models.IntegerField(default=0)
    total_gross_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_net_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Processing
    calculated_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='calculated_payrolls')
    calculated_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='approved_payrolls')
    approved_date = models.DateTimeField(null=True, blank=True)
    
    # Journal entry for accounting
    journal_entry = models.ForeignKey('accounting.JournalEntry', on_delete=models.PROTECT, null=True, blank=True)
    
    class Meta:
        unique_together = ['company', 'payroll_period_start', 'payroll_period_end']
        ordering = ['-payroll_period_start']
        
    def __str__(self):
        return f"Payroll {self.payroll_period_start} to {self.payroll_period_end}"
    
    def calculate_payroll(self):
        """คำนวณเงินเดือน"""
        employees = Employee.objects.filter(
            company=self.company,
            is_active=True,
            hire_date__lte=self.payroll_period_end
        )
        
        # Clear existing payslips
        self.payslips.all().delete()
        
        total_gross = 0
        total_deductions = 0
        total_net = 0
        
        for employee in employees:
            # Get current salary
            salary = employee.salaries.filter(
                effective_date__lte=self.payroll_period_end,
                is_current=True
            ).first()
            
            if not salary:
                continue
            
            # Calculate attendance
            attendances = employee.attendances.filter(
                date__range=[self.payroll_period_start, self.payroll_period_end]
            )
            
            regular_hours = sum(a.regular_hours for a in attendances)
            overtime_hours = sum(a.overtime_hours for a in attendances)
            
            # Create payslip
            payslip = PayslipLine.objects.create(
                payroll=self,
                employee=employee,
                basic_salary=salary.basic_salary,
                total_allowances=salary.total_allowances,
                overtime_amount=overtime_hours * salary.overtime_rate_weekday,
                regular_hours=regular_hours,
                overtime_hours=overtime_hours
            )
            
            total_gross += payslip.gross_salary
            total_deductions += payslip.total_deductions
            total_net += payslip.net_salary
        
        # Update totals
        self.total_employees = employees.count()
        self.total_gross_salary = total_gross
        self.total_deductions = total_deductions
        self.total_net_salary = total_net
        self.status = 'calculated'
        self.calculated_by = self.updated_by
        self.calculated_date = timezone.now()
        self.save()

class PayslipLine(BaseModel):
    """รายการเงินเดือนพนักงาน"""
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='payslips')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payslips')
    
    # Earnings
    basic_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_allowances = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    overtime_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    other_earnings = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Deductions
    tax_deduction = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    social_security = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    provident_fund = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    loan_deduction = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Hours
    regular_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    # Totals
    gross_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['payroll', 'employee']
        ordering = ['employee__employee_id']
        
    def save(self, *args, **kwargs):
        # Calculate totals
        self.gross_salary = (
            self.basic_salary + self.total_allowances + self.overtime_amount +
            self.bonus + self.commission + self.other_earnings
        )
        
        self.total_deductions = (
            self.tax_deduction + self.social_security + self.provident_fund +
            self.loan_deduction + self.other_deductions
        )
        
        self.net_salary = self.gross_salary - self.total_deductions
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.payroll} - {self.net_salary:,.2f}"
