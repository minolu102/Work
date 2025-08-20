# hr/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q, Count, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from .models import Employee, Department, Attendance, LeaveRequest, Payroll
from .forms import EmployeeForm, AttendanceForm, LeaveRequestForm

@login_required
def employee_list(request):
    """รายการพนักงาน"""
    employees = Employee.objects.filter(
        company=request.user.profile.company,
        is_active=True
    ).select_related('department', 'position').order_by('employee_id')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        employees = employees.filter(
            Q(employee_id__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    
    # Filter by department
    department_id = request.GET.get('department', '')
    if department_id:
        employees = employees.filter(department_id=department_id)
    
    # Pagination
    paginator = Paginator(employees, 20)
    page = request.GET.get('page')
    employees = paginator.get_page(page)
    
    departments = Department.objects.filter(
        company=request.user.profile.company,
        is_active=True
    )
    
    context = {
        'employees': employees,
        'departments': departments,
        'search': search,
        'department_id': department_id,
        'title': 'Employee List - รายการพนักงาน'
    }
    return render(request, 'hr/employee_list.html', context)

@login_required
def attendance_report(request):
    """รายงานการเข้าออกงาน"""
    company = request.user.profile.company
    
    # Date range filter
    from datetime import date, timedelta
    date_from = request.GET.get('date_from', date.today().replace(day=1))
    date_to = request.GET.get('date_to', date.today())
    
    # Get attendance data
    attendances = Attendance.objects.filter(
        employee__company=company,
        date__range=[date_from, date_to]
    ).select_related('employee')
    
    # Summary statistics
    total_present = attendances.filter(status='present').count()
    total_absent = attendances.filter(status='absent').count()
    total_late = attendances.filter(status='late').count()
    
    # Department wise attendance
    dept_attendance = attendances.values(
        'employee__department__name'
    ).annotate(
        present_count=Count('id', filter=Q(status='present')),
        absent_count=Count('id', filter=Q(status='absent')),
        late_count=Count('id', filter=Q(status='late'))
    ).order_by('employee__department__name')
    
    context = {
        'date_from': date_from,
        'date_to': date_to,
        'total_present': total_present,
        'total_absent': total_absent,
        'total_late': total_late,
        'dept_attendance': dept_attendance,
        'title': 'Attendance Report - รายงานการเข้าออกงาน'
    }
    return render(request, 'hr/attendance_report.html', context)

@login_required
def leave_requests(request):
    """คำขอลา"""
    requests = LeaveRequest.objects.filter(
        employee__company=request.user.profile.company
    ).select_related('employee', 'leave_type').order_by('-start_date')
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        requests = requests.filter(status=status)
    
    # Filter pending approval
    pending_approval = request.GET.get('pending_approval', '')
    if pending_approval:
        requests = requests.filter(status='submitted')
    
    # Pagination
    paginator = Paginator(requests, 20)
    page = request.GET.get('page')
    requests = paginator.get_page(page)
    
    context = {
        'requests': requests,
        'status': status,
        'pending_approval': pending_approval,
        'title': 'Leave Requests - คำขอลา'
    }
    return render(request, 'hr/leave_requests.html', context)

@login_required
def payroll_list(request):
    """รายการการจ่ายเงินเดือน"""
    payrolls = Payroll.objects.filter(
        company=request.user.profile.company
    ).order_by('-payroll_period_start')
    
    # Pagination
    paginator = Paginator(payrolls, 10)
    page = request.GET.get('page')
    payrolls = paginator.get_page(page)
    
    context = {
        'payrolls': payrolls,
        'title': 'Payroll List - รายการเงินเดือน'
    }
    return render(request, 'hr/payroll_list.html', context)

@login_required
def employee_detail(request, employee_id):
    """รายละเอียดพนักงาน"""
    employee = get_object_or_404(Employee, id=employee_id, company=request.user.profile.company)
    
    # Attendance records
    attendances = Attendance.objects.filter(employee=employee).order_by('-date')
    
    # Leave requests
    leave_requests = LeaveRequest.objects.filter(employee=employee).order_by('-start_date')
    
    context = {
        'employee': employee,
        'attendances': attendances,
        'leave_requests': leave_requests,
        'title': f'Employee Detail - {employee.full_name}'
    }
    return render(request, 'hr/employee_detail.html', context)

@login_required
def create_employee(request):
    """เพิ่มพนักงานใหม่"""
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            employee = form.save(commit=False)
            employee.company = request.user.profile.company
            employee.save()
            messages.success(request, 'Employee added successfully.')
            return redirect('hr:employee_list')
    else:
        form = EmployeeForm()
    
    context = {
        'form': form,
        'title': 'Add Employee - เพิ่มพนักงาน'
    }
    return render(request, 'hr/add_employee.html', context)

@login_required
def edit_employee(request, employee_id):
    """แก้ไขข้อมูลพนักงาน"""
    employee = get_object_or_404(Employee, id=employee_id, company=request.user.profile.company)
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, 'Employee updated successfully.')
            return redirect('hr:employee_detail', employee_id=employee.id)
    else:
        form = EmployeeForm(instance=employee)
    
    context = {
        'form': form,
        'employee': employee,
        'title': f'Edit Employee - {employee.full_name}'
    }
    return render(request, 'hr/edit_employee.html', context)

@login_required
def delete_employee(request, employee_id):
    """ลบพนักงาน"""
    employee = get_object_or_404(Employee, id=employee_id, company=request.user.profile.company)
    
    if request.method == 'POST':
        employee.is_active = False
        employee.save()
        messages.success(request, 'Employee deleted successfully.')
        return redirect('hr:employee_list')
    
    context = {
        'employee': employee,
        'title': f'Delete Employee - {employee.full_name}'
    }
    return render(request, 'hr/delete_employee.html', context)

@login_required
def create_attendance(request, employee_id):
    """บันทึกการเข้าออกงานของพนักงาน"""
    employee = get_object_or_404(Employee, id=employee_id, company=request.user.profile.company)
    
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            attendance = form.save(commit=False)
            attendance.employee = employee
            attendance.date = timezone.now().date()
            attendance.save()
            messages.success(request, 'Attendance create successfully.')
            return redirect('hr:employee_detail', employee_id=employee.id)
    else:
        form = AttendanceForm()
    
    context = {
        'form': form,
        'employee': employee,
        'title': f'Mark Attendance - {employee.full_name}'
    }
    return render(request, 'hr/mark_attendance.html', context)

@login_required
def department_list(request):
    """รายการแผนก"""
    departments = Department.objects.filter(
        company=request.user.profile.company,
        is_active=True
    ).order_by('name')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        departments = departments.filter(name__icontains=search)
    
    context = {
        'departments': departments,
        'search': search,
        'title': 'Department List - รายการแผนก'
    }
    return render(request, 'hr/department_list.html', context)

@login_required
def department_detail(request, department_id):
    """รายละเอียดแผนก"""
    department = get_object_or_404(Department, id=department_id, company=request.user.profile.company)
    
    # Employees in department
    employees = Employee.objects.filter(department=department, is_active=True).order_by('employee_id')
    
    context = {
        'department': department,
        'employees': employees,
        'title': f'Department Detail - {department.name}'
    }
    return render(request, 'hr/department_detail.html', context)

@login_required
def attendance_list(request):
    """รายการการเข้าออกงาน"""
    attendances = Attendance.objects.filter(
        employee__company=request.user.profile.company
    ).select_related('employee').order_by('-date')
    
    # Pagination
    paginator = Paginator(attendances, 20)
    page = request.GET.get('page')
    attendances = paginator.get_page(page)
    
    context = {
        'attendances': attendances,
        'title': 'Attendance List - รายการการเข้าออกงาน'
    }
    return render(request, 'hr/attendance_list.html', context)

@login_required
def bulk_import_attendance(request):
    """อัปโหลดพนักงานแบบกลุ่ม"""
    if request.method == 'POST':
        file = request.FILES.get('file')
        if file:
            # Process the uploaded file (CSV, Excel, etc.)
            # This is a placeholder for actual file processing logic
            messages.success(request, 'attendance import successfully.')
            return redirect('hr:attendance_list')
        else:
            messages.error(request, 'Please import a valid file.')
    
    context = {
        'title': 'Bulk import attendance - อัปโหลดพนักงานแบบกลุ่ม'
    }
    return render(request, 'hr/bulk_import_attendance.html', context)

@login_required
def leave_request_detail(request):
    """รายละเอียดคำขอลา"""
    leave_request_id = request.GET.get('id')
    leave_request = get_object_or_404(LeaveRequest, id=leave_request_id, employee__company=request.user.profile.company)
    
    context = {
        'leave_request': leave_request,
        'title': f'Leave Request Detail - {leave_request.employee.full_name}'
    }
    return render(request, 'hr/leave_request_detail.html', context)

@login_required
def create_leave_request(request):
    """สร้างคำขอลาใหม่"""
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.employee = request.user.profile.employee
            leave_request.save()
            messages.success(request, 'Leave request submitted successfully.')
            return redirect('hr:leave_requests')
    else:
        form = LeaveRequestForm()
    
    context = {
        'form': form,
        'title': 'Create Leave Request - สร้างคำขอลา'
    }
    return render(request, 'hr/create_leave_request.html', context)

@login_required
def approve_leave_request(request, request_id):
    """อนุมัติคำขอลา"""
    leave_request = get_object_or_404(LeaveRequest, id=request_id, employee__company=request.user.profile.company)
    
    if request.method == 'POST':
        leave_request.status = 'approved'
        leave_request.approved_by = request.user
        leave_request.approved_at = timezone.now()
        leave_request.save()
        messages.success(request, 'Leave request approved successfully.')
        return redirect('hr:leave_requests')
    
    context = {
        'leave_request': leave_request,
        'title': f'Approve Leave Request - {leave_request.employee.full_name}'
    }
    return render(request, 'hr/approve_leave_request.html', context)

@login_required
def payroll_detail(request, payroll_id):
    """รายละเอียดการจ่ายเงินเดือน"""
    payroll = get_object_or_404(Payroll, id=payroll_id, company=request.user.profile.company)
    
    # Employee payroll details
    employee_payrolls = payroll.employee_payrolls.all().select_related('employee')
    
    context = {
        'payroll': payroll,
        'employee_payrolls': employee_payrolls,
        'title': f'Payroll Detail - {payroll.payroll_period_start} to {payroll.payroll_period_end}'
    }
    return render(request, 'hr/payroll_detail.html', context)

@login_required
def create_payroll(request):
    """สร้างการจ่ายเงินเดือนใหม่"""
    if request.method == 'POST':
        # Logic to create payroll based on the form data
        # This is a placeholder for actual payroll creation logic
        messages.success(request, 'Payroll created successfully.')
        return redirect('hr:payroll_list')
    
    context = {
        'title': 'Create Payroll - สร้างการจ่ายเงินเดือน'
    }
    return render(request, 'hr/create_payroll.html', context)

@login_required
def calculate_payroll(request):
    """คำนวณเงินเดือน"""
    if request.method == 'POST':
        # Logic to calculate payroll based on the form data
        # This is a placeholder for actual payroll calculation logic
        messages.success(request, 'Payroll calculated successfully.')
        return redirect('hr:payroll_list')
    
    context = {
        'title': 'Calculate Payroll - คำนวณเงินเดือน'
    }
    return render(request, 'hr/calculate_payroll.html', context)

@login_required
def approve_payroll(request, payroll_id):
    """อนุมัติการจ่ายเงินเดือน"""
    payroll = get_object_or_404(Payroll, id=payroll_id, company=request.user.profile.company)
    
    if request.method == 'POST':
        payroll.status = 'approved'
        payroll.approved_by = request.user
        payroll.approved_at = timezone.now()
        payroll.save()
        messages.success(request, 'Payroll approved successfully.')
        return redirect('hr:payroll_list')
    
    context = {
        'payroll': payroll,
        'title': f'Approve Payroll - {payroll.payroll_period_start} to {payroll.payroll_period_end}'
    }
    return render(request, 'hr/approve_payroll.html', context)

@login_required
def payroll_report(request):
    """รายงานการจ่ายเงินเดือน"""
    company = request.user.profile.company
    
    # Date range filter
    from datetime import date, timedelta
    date_from = request.GET.get('date_from', date.today().replace(day=1))
    date_to = request.GET.get('date_to', date.today())
    
    payrolls = Payroll.objects.filter(
        company=company,
        payroll_period_start__gte=date_from,
        payroll_period_end__lte=date_to
    ).order_by('-payroll_period_start')
    
    context = {
        'payrolls': payrolls,
        'date_from': date_from,
        'date_to': date_to,
        'title': 'Payroll Report - รายงานการจ่ายเงินเดือน'
    }
    return render(request, 'hr/payroll_report.html', context)

@login_required
def employee_summary_report(request):
    """รายงานสรุปพนักงาน"""
    company = request.user.profile.company
    
    # Summary statistics
    total_employees = Employee.objects.filter(company=company, is_active=True).count()
    total_departments = Department.objects.filter(company=company, is_active=True).count()
    
    # Average salary
    average_salary = Employee.objects.filter(company=company, is_active=True).aggregate(Avg('salary'))['salary__avg'] or 0
    
    context = {
        'total_employees': total_employees,
        'total_departments': total_departments,
        'average_salary': average_salary,
        'title': 'Employee Summary Report - รายงานสรุปพนักงาน'
    }
    return render(request, 'hr/employee_summary_report.html', context)



