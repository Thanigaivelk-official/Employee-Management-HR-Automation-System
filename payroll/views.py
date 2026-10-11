from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, FormView, UpdateView
from django.views import View
from django.http import HttpResponse, FileResponse, Http404
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db import transaction
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
import calendar

from .models import PayrollRecord, SalaryStructure
from .forms import SalaryStructureForm, PayrollRunForm
from .services import generate_payslip_pdf
from employees.models import Employee
from accounts.models import CustomUser
from accounts.decorators import RoleRequiredMixin
from audit.services import log_action
from notifications.services import notify_user

class PayrollListView(RoleRequiredMixin, ListView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'EMPLOYEE']
    model = PayrollRecord
    template_name = 'payroll/payroll_list.html'
    context_object_name = 'payrolls'
    paginate_by = 15

    def get_queryset(self):
        user = self.request.user
        qs = PayrollRecord.objects.select_related('employee', 'employee__department').all()

        if user.is_only_employee_role:
            emp = getattr(user, 'employee_profile', None)
            if emp:
                qs = qs.filter(employee=emp)
            else:
                qs = qs.none()

        month = self.request.GET.get('month')
        year = self.request.GET.get('year')
        dept_id = self.request.GET.get('department')
        search = self.request.GET.get('search')

        if month:
            qs = qs.filter(month=month)
        if year:
            qs = qs.filter(year=year)
        if dept_id:
            qs = qs.filter(employee__department_id=dept_id)
        if search:
            qs = qs.filter(
                employee__first_name__icontains=search) | qs.filter(employee__last_name__icontains=search) | qs.filter(payslip_number__icontains=search
            )

        return qs.order_by('-year', '-month', 'employee__first_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from departments.models import Department
        context['departments'] = Department.objects.filter(is_active=True)
        context['months'] = [(i, calendar.month_name[i]) for i in range(1, 13)]
        context['current_year'] = timezone.localdate().year
        return context

class PayrollDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'EMPLOYEE']
    model = PayrollRecord
    template_name = 'payroll/payroll_detail.html'
    context_object_name = 'payroll'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        # Prevent employees from viewing other employees' payslips
        if user.is_only_employee_role:
            if not obj.employee.user or obj.employee.user != user:
                raise Http404("Payslip not found or access restricted.")
        return obj

class DownloadPayslipPDFView(RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'EMPLOYEE']

    def get(self, request, pk):
        payroll = get_object_or_404(PayrollRecord, pk=pk)
        user = request.user

        # Security check: employee can only download their own payslip
        if user.is_only_employee_role:
            if not payroll.employee.user or payroll.employee.user != user:
                messages.error(request, "Access restricted: You cannot download payslips belonging to other personnel.")
                return redirect('dashboard')

        pdf_buffer = generate_payslip_pdf(payroll)
        filename = f"Payslip_{payroll.employee.employee_id}_{payroll.year}_{payroll.month:02d}.pdf"

        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

class PayrollGenerateView(RoleRequiredMixin, FormView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN']
    template_name = 'payroll/payroll_generate.html'
    form_class = PayrollRunForm
    success_url = reverse_lazy('payroll:payroll_list')

    def form_valid(self, form):
        month = int(form.cleaned_data['month'])
        year = int(form.cleaned_data['year'])
        department = form.cleaned_data.get('department')

        employees_qs = Employee.objects.filter(employment_status=Employee.Status.ACTIVE)
        if department:
            employees_qs = employees_qs.filter(department=department)

        processed_count = 0
        skipped_count = 0

        with transaction.atomic():
            for emp in employees_qs:
                # Check for existing record to prevent duplicates
                if PayrollRecord.objects.filter(employee=emp, month=month, year=year).exists():
                    skipped_count += 1
                    continue

                # Fetch or create salary structure
                structure, _ = SalaryStructure.objects.get_or_create(
                    employee=emp,
                    defaults={
                        'basic_salary': emp.basic_salary,
                        'hra': (emp.basic_salary * Decimal('0.40')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                        'transport_allowance': Decimal('2000.00'),
                        'medical_allowance': Decimal('1500.00'),
                        'special_allowance': Decimal('1000.00'),
                        'pf_rate_percent': Decimal('12.00'),
                        'professional_tax': Decimal('200.00'),
                    }
                )

                # Compute components
                basic = structure.basic_salary
                hra = structure.hra
                allowances = structure.transport_allowance + structure.medical_allowance + structure.special_allowance
                bonus = Decimal('0.00')
                gross = basic + hra + allowances + bonus

                # Deductions
                pf_rate = structure.pf_rate_percent / Decimal('100.00')
                pf_deduction = (basic * pf_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                tax_deduction = structure.professional_tax

                # Calculate unpaid leave deductions (from Attendance records if marked ABSENT)
                from attendance.models import Attendance
                unpaid_days = Attendance.objects.filter(
                    employee=emp,
                    attendance_date__year=year,
                    attendance_date__month=month,
                    status=Attendance.Status.ABSENT
                ).count()

                per_day_salary = (basic / Decimal('30.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                unpaid_deduction = (per_day_salary * Decimal(unpaid_days)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                total_deductions = pf_deduction + tax_deduction + unpaid_deduction
                net_salary = max(Decimal('0.00'), gross - total_deductions)

                record = PayrollRecord.objects.create(
                    employee=emp,
                    month=month,
                    year=year,
                    basic_salary=basic,
                    hra=hra,
                    allowances_total=allowances,
                    bonus=bonus,
                    gross_salary=gross,
                    pf_deduction=pf_deduction,
                    tax_deduction=tax_deduction,
                    unpaid_leave_deduction=unpaid_deduction,
                    total_deductions=total_deductions,
                    net_salary=net_salary,
                    status=PayrollRecord.Status.PROCESSED,
                    processed_by=self.request.user
                )
                processed_count += 1

                # Send notification to employee
                if emp.user:
                    notify_user(
                        user=emp.user,
                        title="Payslip Generated",
                        message=f"Your payslip for {calendar.month_name[month]} {year} has been processed. Net pay: ${net_salary:,.2f}.",
                        notification_type="PAYROLL",
                        link=reverse('payroll:payroll_detail', kwargs={'pk': record.pk})
                    )

            log_action(
                actor=self.request.user,
                action='PROCESS',
                object_type='Payroll',
                object_id=f"{year}-{month:02d}",
                change_summary=f"Processed payroll for {month}/{year}. Generated: {processed_count}, Skipped (Already existed): {skipped_count}.",
                request=self.request
            )

        messages.success(
            self.request,
            f"Payroll processing complete for {calendar.month_name[month]} {year}. "
            f"Successfully created {processed_count} payslips. (Skipped {skipped_count} existing records)."
        )
        return redirect('payroll:payroll_list')

class SalaryStructureUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN']
    model = SalaryStructure
    form_class = SalaryStructureForm
    template_name = 'payroll/salary_structure_form.html'

    def get_success_url(self):
        messages.success(self.request, f"Salary structure for {self.object.employee.full_name} updated successfully.")
        return reverse('employees:employee_detail', kwargs={'pk': self.object.employee.pk})
