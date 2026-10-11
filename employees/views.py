from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.views import View
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal

from .models import Employee
from .forms import EmployeeForm
from accounts.models import CustomUser
from accounts.decorators import RoleRequiredMixin
from audit.services import log_action

class EmployeeListView(RoleRequiredMixin, ListView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'MANAGER', 'EMPLOYEE']
    model = Employee
    template_name = 'employees/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 15

    def get_queryset(self):
        user = self.request.user
        qs = Employee.objects.select_related('department', 'reporting_manager', 'user').all()

        # Role-based visibility
        if user.role == CustomUser.Role.MANAGER and not user.is_superuser:
            qs = qs.filter(
                Q(department__manager__user=user) | Q(reporting_manager__user=user)
            ).distinct()

        # Search parameter
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(
                Q(employee_id__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(department__name__icontains=search)
            )

        # Filters
        dept_id = self.request.GET.get('department')
        emp_type = self.request.GET.get('employment_type')
        status = self.request.GET.get('status')

        if dept_id:
            qs = qs.filter(department_id=dept_id)
        if emp_type:
            qs = qs.filter(employment_type=emp_type)
        if status:
            qs = qs.filter(employment_status=status)
        else:
            # By default show active employees unless specific status filter is chosen
            if not self.request.GET.get('all_status'):
                qs = qs.filter(employment_status=Employee.Status.ACTIVE)

        # Sorting
        sort_by = self.request.GET.get('sort', 'employee_id')
        if sort_by in ['employee_id', '-employee_id', 'first_name', '-first_name', 'date_of_joining', '-date_of_joining']:
            qs = qs.order_by(sort_by)
        else:
            qs = qs.order_by('employee_id')

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from departments.models import Department
        context['departments'] = Department.objects.filter(is_active=True)
        context['employment_types'] = Employee.EmploymentType.choices
        context['statuses'] = Employee.Status.choices
        return context

class EmployeeDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'MANAGER', 'EMPLOYEE']
    model = Employee
    template_name = 'employees/employee_detail.html'
    context_object_name = 'employee'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        emp = self.object
        today = timezone.localdate()
        current_year = today.year
        current_month = today.month

        # Lazy imports to avoid circular dependencies
        from attendance.models import Attendance
        from leave_management.models import LeaveRequest, LeaveBalance
        from payroll.models import PayrollRecord, SalaryStructure

        # Attendance summary for current month
        month_attendance = Attendance.objects.filter(employee=emp, attendance_date__year=current_year, attendance_date__month=current_month)
        context['present_days'] = month_attendance.filter(status=Attendance.Status.PRESENT).count()
        context['absent_days'] = month_attendance.filter(status=Attendance.Status.ABSENT).count()
        context['leave_days'] = month_attendance.filter(status=Attendance.Status.LEAVE).count()

        # Leave balances and recent requests
        context['leave_balances'] = LeaveBalance.objects.filter(employee=emp, year=current_year).select_related('leave_type')
        context['recent_leaves'] = LeaveRequest.objects.filter(employee=emp).order_by('-created_at')[:5]

        # Check permission to view confidential payroll details
        can_view_payroll = (
            self.request.user.is_hr_admin_role or
            (emp.user and emp.user == self.request.user)
        )
        context['can_view_payroll'] = can_view_payroll

        if can_view_payroll:
            context['salary_structure'] = SalaryStructure.objects.filter(employee=emp).first()
            context['recent_payslips'] = PayrollRecord.objects.filter(employee=emp).order_by('-year', '-month')[:6]

        return context

class EmployeeCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN']
    model = Employee
    form_class = EmployeeForm
    template_name = 'employees/employee_form.html'

    def form_valid(self, form):
        with transaction.atomic():
            employee = form.save(commit=False)
            create_user = form.cleaned_data.get('create_user_account')
            user_role = form.cleaned_data.get('user_role') or CustomUser.Role.EMPLOYEE

            # Create User Account if requested
            if create_user:
                username = employee.email.split('@')[0]
                # Ensure username uniqueness
                base_username = username
                counter = 1
                while CustomUser.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1

                user = CustomUser.objects.create_user(
                    username=username,
                    email=employee.email,
                    first_name=employee.first_name,
                    last_name=employee.last_name,
                    role=user_role,
                    phone_number=employee.phone
                )
                user.set_password('Password@123')  # Default initial password
                user.save()
                employee.user = user

            employee.save()

            # Initialize Leave Balances for all active leave types
            from leave_management.models import LeaveType, LeaveBalance
            current_year = timezone.localdate().year
            for lt in LeaveType.objects.all():
                LeaveBalance.objects.get_or_create(
                    employee=employee,
                    leave_type=lt,
                    year=current_year,
                    defaults={
                        'total_allocated': Decimal(lt.default_days_per_year),
                        'used': Decimal('0.00'),
                        'remaining': Decimal(lt.default_days_per_year)
                    }
                )

            # Initialize standard Salary Structure
            from payroll.models import SalaryStructure
            SalaryStructure.objects.get_or_create(
                employee=employee,
                defaults={
                    'basic_salary': employee.basic_salary,
                    'hra': employee.basic_salary * Decimal('0.40'),
                    'transport_allowance': Decimal('2000.00'),
                    'medical_allowance': Decimal('1500.00'),
                    'special_allowance': Decimal('1000.00'),
                    'pf_rate_percent': Decimal('12.00'),
                    'professional_tax': Decimal('200.00'),
                }
            )

            log_action(
                actor=self.request.user,
                action='CREATE',
                object_type='Employee',
                object_id=str(employee.pk),
                change_summary=f"Created employee profile {employee.full_name} ({employee.employee_id})",
                request=self.request
            )

        messages.success(self.request, f"Employee '{employee.full_name}' created successfully (ID: {employee.employee_id}).")
        return redirect('employees:employee_detail', pk=employee.pk)

class EmployeeUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN']
    model = Employee
    form_class = EmployeeForm
    template_name = 'employees/employee_form.html'

    def form_valid(self, form):
        with transaction.atomic():
            employee = form.save()
            # If basic salary updated, sync with salary structure
            from payroll.models import SalaryStructure
            structure = SalaryStructure.objects.filter(employee=employee).first()
            if structure:
                structure.basic_salary = employee.basic_salary
                structure.hra = employee.basic_salary * Decimal('0.40')
                structure.save()

            log_action(
                actor=self.request.user,
                action='UPDATE',
                object_type='Employee',
                object_id=str(employee.pk),
                change_summary=f"Updated details for employee {employee.full_name} ({employee.employee_id})",
                request=self.request
            )

        messages.success(self.request, f"Employee '{employee.full_name}' updated successfully.")
        return redirect('employees:employee_detail', pk=employee.pk)

class EmployeeDeactivateView(RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN']

    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        status_to_set = request.POST.get('status', Employee.Status.RESIGNED)
        
        employee.employment_status = status_to_set
        employee.save()

        # Deactivate login account as well
        if employee.user:
            employee.user.is_active = False
            employee.user.save()

        log_action(
            actor=request.user,
            action='UPDATE',
            object_type='Employee',
            object_id=str(employee.pk),
            change_summary=f"Marked employee {employee.full_name} as {status_to_set} and deactivated user login.",
            request=request
        )

        messages.warning(request, f"Employee {employee.full_name} has been marked as {status_to_set}.")
        return redirect('employees:employee_detail', pk=employee.pk)
