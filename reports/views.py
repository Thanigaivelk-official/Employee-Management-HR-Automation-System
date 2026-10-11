import csv
import io
import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponse, StreamingHttpResponse
from django.views import View
from django.views.generic import TemplateView
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q

from accounts.decorators import RoleRequiredMixin
from employees.models import Employee
from departments.models import Department
from attendance.models import Attendance
from leave_management.models import LeaveRequest
from payroll.models import PayrollRecord

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class Echo:
    """An object that implements just the write method of the file-like interface for streaming CSV."""
    def write(self, value):
        return value

class ReportDashboardView(RoleRequiredMixin, TemplateView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'MANAGER']
    template_name = 'reports/report_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.filter(is_active=True)
        context['today'] = timezone.localdate()
        context['current_year'] = timezone.localdate().year
        return context

class ExportEmployeesCSVView(RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'MANAGER']

    def get(self, request):
        dept_id = request.GET.get('department')
        status = request.GET.get('status', 'ACTIVE')

        qs = Employee.objects.select_related('department', 'reporting_manager').all()
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        if status:
            qs = qs.filter(employment_status=status)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="employee_directory_{timezone.localdate()}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Employee ID', 'Full Name', 'Email', 'Phone', 'Department',
            'Designation', 'Employment Type', 'Status', 'Date of Joining'
        ])

        for emp in qs:
            writer.writerow([
                emp.employee_id,
                emp.full_name,
                emp.email,
                emp.phone,
                emp.department.name if emp.department else '',
                emp.designation,
                emp.get_employment_type_display(),
                emp.get_employment_status_display(),
                emp.date_of_joining
            ])

        return response

class ExportAttendanceCSVView(RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'MANAGER']

    def get(self, request):
        month = request.GET.get('month', timezone.localdate().month)
        year = request.GET.get('year', timezone.localdate().year)
        dept_id = request.GET.get('department')

        qs = Attendance.objects.select_related('employee', 'employee__department').filter(
            attendance_date__year=year, attendance_date__month=month
        )
        if dept_id:
            qs = qs.filter(employee__department_id=dept_id)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="attendance_report_{year}_{month}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Employee ID', 'Employee Name', 'Department',
            'Check In', 'Check Out', 'Working Hours', 'Status', 'Is Late', 'Remarks'
        ])

        for att in qs.order_by('attendance_date', 'employee__employee_id'):
            writer.writerow([
                att.attendance_date,
                att.employee.employee_id,
                att.employee.full_name,
                att.employee.department.name if att.employee.department else '',
                att.check_in.strftime('%H:%M:%S') if att.check_in else '',
                att.check_out.strftime('%H:%M:%S') if att.check_out else '',
                att.working_hours,
                att.get_status_display(),
                'Yes' if att.is_late else 'No',
                att.remarks or ''
            ])

        return response

class ExportLeavesCSVView(RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'MANAGER']

    def get(self, request):
        qs = LeaveRequest.objects.select_related('employee', 'leave_type', 'reviewed_by').all().order_by('-created_at')

        dept_id = request.GET.get('department')
        if dept_id:
            qs = qs.filter(employee__department_id=dept_id)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="leave_report_{timezone.localdate()}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Request ID', 'Employee ID', 'Employee Name', 'Leave Type',
            'Start Date', 'End Date', 'Days Count', 'Status', 'Reason',
            'Reviewed By', 'Reviewed At'
        ])

        for req in qs:
            writer.writerow([
                req.request_id,
                req.employee.employee_id,
                req.employee.full_name,
                req.leave_type.name,
                req.start_date,
                req.end_date,
                req.days_count,
                req.get_status_display(),
                req.reason,
                req.reviewed_by.get_full_name() if req.reviewed_by else '',
                req.reviewed_at.strftime('%Y-%m-%d %H:%M') if req.reviewed_at else ''
            ])

        return response

class ExportPayrollCSVView(RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN']

    def get(self, request):
        month = request.GET.get('month', timezone.localdate().month)
        year = request.GET.get('year', timezone.localdate().year)

        qs = PayrollRecord.objects.select_related('employee', 'employee__department').filter(
            month=month, year=year
        ).order_by('employee__employee_id')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="payroll_summary_{year}_{month}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Payslip No', 'Employee ID', 'Employee Name', 'Department',
            'Basic Salary', 'HRA', 'Allowances', 'Gross Salary',
            'PF Deduction', 'Tax Deduction', 'Unpaid Leave Deduction',
            'Total Deductions', 'Net Salary', 'Status'
        ])

        for p in qs:
            writer.writerow([
                p.payslip_number,
                p.employee.employee_id,
                p.employee.full_name,
                p.employee.department.name if p.employee.department else '',
                p.basic_salary,
                p.hra,
                p.allowances_total,
                p.gross_salary,
                p.pf_deduction,
                p.tax_deduction,
                p.unpaid_leave_deduction,
                p.total_deductions,
                p.net_salary,
                p.get_status_display()
            ])

        return response

class ExportEmployeesPDFView(RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'MANAGER']

    def get(self, request):
        dept_id = request.GET.get('department')
        qs = Employee.objects.select_related('department').filter(employment_status='ACTIVE').order_by('department__name', 'first_name')
        if dept_id:
            qs = qs.filter(department_id=dept_id)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('Title', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=colors.HexColor('#0f172a'))
        meta_style = ParagraphStyle('Meta', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#64748b'))
        cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10)
        head_style = ParagraphStyle('Head', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor('#1e293b'))

        story.append(Paragraph("EMPLOYEE DIRECTORY REPORT", title_style))
        story.append(Paragraph(f"Generated on {timezone.now().strftime('%Y-%m-%d %H:%M')} | Total Active: {qs.count()}", meta_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#3b82f6'), spaceAfter=12))

        table_data = [[
            Paragraph("<b>Emp ID</b>", head_style),
            Paragraph("<b>Full Name</b>", head_style),
            Paragraph("<b>Department</b>", head_style),
            Paragraph("<b>Designation</b>", head_style),
            Paragraph("<b>Email</b>", head_style),
            Paragraph("<b>Phone</b>", head_style),
            Paragraph("<b>Joining Date</b>", head_style),
        ]]

        for emp in qs:
            table_data.append([
                Paragraph(emp.employee_id, cell_style),
                Paragraph(emp.full_name, cell_style),
                Paragraph(emp.department.name if emp.department else '-', cell_style),
                Paragraph(emp.designation, cell_style),
                Paragraph(emp.email, cell_style),
                Paragraph(emp.phone, cell_style),
                Paragraph(str(emp.date_of_joining), cell_style),
            ])

        table = Table(table_data, colWidths=[70, 120, 110, 120, 150, 90, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(table)

        doc.build(story)
        buffer.seek(0)
        return HttpResponse(buffer.getvalue(), content_type='application/pdf')
