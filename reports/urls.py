from django.urls import path
from .views import (
    ReportDashboardView,
    ExportEmployeesCSVView, ExportAttendanceCSVView,
    ExportLeavesCSVView, ExportPayrollCSVView,
    ExportEmployeesPDFView
)

app_name = 'reports'

urlpatterns = [
    path('', ReportDashboardView.as_view(), name='report_dashboard'),
    path('employees/csv/', ExportEmployeesCSVView.as_view(), name='export_employees_csv'),
    path('employees/pdf/', ExportEmployeesPDFView.as_view(), name='export_employees_pdf'),
    path('attendance/csv/', ExportAttendanceCSVView.as_view(), name='export_attendance_csv'),
    path('leaves/csv/', ExportLeavesCSVView.as_view(), name='export_leaves_csv'),
    path('payroll/csv/', ExportPayrollCSVView.as_view(), name='export_payroll_csv'),
]
