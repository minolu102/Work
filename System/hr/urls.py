# hr/urls.py
from django.urls import path
from . import views

app_name = 'hr'

urlpatterns = [
    path('', views.employee_list, name='employee_list'),
    
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/<uuid:employee_id>/', views.employee_detail, name='employee_detail'),
    path('employees/create/', views.create_employee, name='create_employee'),
    
    path('departments/', views.department_list, name='department_list'),
    path('departments/<uuid:department_id>/', views.department_detail, name='department_detail'),
    
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/create/', views.create_attendance, name='create_attendance'),
    path('attendance/bulk-import/', views.bulk_import_attendance, name='bulk_import_attendance'),
    
    path('leave/', views.leave_requests, name='leave_requests'),
    path('leave/<uuid:request_id>/', views.leave_request_detail, name='leave_request_detail'),
    path('leave/create/', views.create_leave_request, name='create_leave_request'),
    path('leave/<uuid:request_id>/approve/', views.approve_leave_request, name='approve_leave_request'),
    
    path('payroll/', views.payroll_list, name='payroll_list'),
    path('payroll/<uuid:payroll_id>/', views.payroll_detail, name='payroll_detail'),
    path('payroll/create/', views.create_payroll, name='create_payroll'),
    path('payroll/<uuid:payroll_id>/calculate/', views.calculate_payroll, name='calculate_payroll'),
    path('payroll/<uuid:payroll_id>/approve/', views.approve_payroll, name='approve_payroll'),
    
    path('reports/attendance/', views.attendance_report, name='attendance_report'),
    path('reports/payroll/', views.payroll_report, name='payroll_report'),
    path('reports/employee-summary/', views.employee_summary_report, name='employee_summary_report'),
]