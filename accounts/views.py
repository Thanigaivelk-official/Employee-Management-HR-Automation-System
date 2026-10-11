from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib.auth import login, logout
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Count, Sum, Q
import json
from decimal import Decimal

from .models import CustomUser
from .forms import (
    LoginForm, UserCreateForm, UserUpdateForm,
    ProfileUpdateForm, BootstrapPasswordChangeForm
)
from .decorators import RoleRequiredMixin, role_required

class UserLoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        form = LoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_active:
                messages.error(request, "This account is currently deactivated. Contact HR or Administrator.")
                return render(request, self.template_name, {'form': form})
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            next_url = request.GET.get('next') or 'dashboard'
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password. Please try again.")
            return render(request, self.template_name, {'form': form})

class UserLogoutView(View):
    def get(self, request):
        logout(request)
        messages.info(request, "You have been securely logged out.")
        return redirect('accounts:login')
    
    def post(self, request):
        return self.get(request)

class DashboardView(LoginRequiredMixin, View):
    template_name = 'dashboard/index.html'

    def get(self, request):
        user = request.user
        today = timezone.localdate()
        current_year = today.year
        current_month = today.month

        context = {
            'today': today,
            'role': user.role,
        }

        # Lazy imports of related models to prevent circular imports
        from employees.models import Employee
        from departments.models import Department
        from attendance.models import Attendance
        from leave_management.models import LeaveRequest, LeaveBalance
        from payroll.models import PayrollRecord
        from audit.models import AuditLog

        # Check if user has an associated Employee record
        employee_profile = getattr(user, 'employee_profile', None)
        context['employee_profile'] = employee_profile

        if user.is_hr_admin_role:
            # HR Admin & Super Admin Metrics
            active_employees = Employee.objects.filter(employment_status=Employee.Status.ACTIVE)
            total_active_count = active_employees.count()
            total_departments = Department.objects.filter(is_active=True).count()

            # Today's Attendance breakdown
            today_attendance = Attendance.objects.filter(attendance_date=today)
            present_today = today_attendance.filter(status=Attendance.Status.PRESENT).count()
            half_day_today = today_attendance.filter(status=Attendance.Status.HALF_DAY).count()
            leave_today = today_attendance.filter(status=Attendance.Status.LEAVE).count()
            absent_today = today_attendance.filter(status=Attendance.Status.ABSENT).count()

            # Pending Leave Requests across company
            pending_leaves = LeaveRequest.objects.filter(status=LeaveRequest.Status.PENDING).count()

            # Current Month Payroll Total
            current_month_payroll = PayrollRecord.objects.filter(
                month=current_month, year=current_year, status__in=[PayrollRecord.Status.PROCESSED, PayrollRecord.Status.PAID]
            ).aggregate(total_net=Sum('net_salary'))['total_net'] or Decimal('0.00')

            # Department breakdown chart data
            dept_counts = Department.objects.filter(is_active=True).annotate(
                emp_count=Count('employees', filter=Q(employees__employment_status=Employee.Status.ACTIVE))
            ).values('name', 'emp_count')

            dept_labels = [d['name'] for d in dept_counts]
            dept_values = [d['emp_count'] for d in dept_counts]

            # Recent 5 activities
            recent_audit_logs = AuditLog.objects.select_related('actor').all()[:6]
            recent_employees = Employee.objects.select_related('department').order_by('-created_at')[:5]
            recent_leaves = LeaveRequest.objects.select_related('employee', 'leave_type').filter(status=LeaveRequest.Status.PENDING)[:5]

            context.update({
                'total_employees': total_active_count,
                'total_departments': total_departments,
                'present_today': present_today + half_day_today,
                'absent_today': absent_today,
                'on_leave_today': leave_today,
                'pending_leaves_count': pending_leaves,
                'current_month_payroll': current_month_payroll,
                'dept_labels_json': json.dumps(dept_labels),
                'dept_values_json': json.dumps(dept_values),
                'recent_audit_logs': recent_audit_logs,
                'recent_employees': recent_employees,
                'recent_leaves': recent_leaves,
            })

        elif user.role == CustomUser.Role.MANAGER:
            # Department Manager Metrics
            managed_depts = Department.objects.filter(manager__user=user, is_active=True)
            team_members = Employee.objects.filter(
                Q(department__in=managed_depts) | Q(reporting_manager__user=user),
                employment_status=Employee.Status.ACTIVE
            ).distinct()
            
            team_ids = team_members.values_list('id', flat=True)
            team_count = team_members.count()

            team_today_att = Attendance.objects.filter(employee_id__in=team_ids, attendance_date=today)
            team_present = team_today_att.filter(status__in=[Attendance.Status.PRESENT, Attendance.Status.HALF_DAY]).count()
            team_leave = team_today_att.filter(status=Attendance.Status.LEAVE).count()

            team_pending_leaves = LeaveRequest.objects.filter(
                employee_id__in=team_ids,
                status=LeaveRequest.Status.PENDING
            ).select_related('employee', 'leave_type')

            context.update({
                'team_count': team_count,
                'team_present': team_present,
                'team_leave': team_leave,
                'team_pending_leaves_count': team_pending_leaves.count(),
                'recent_leaves': team_pending_leaves[:5],
                'team_members': team_members[:5],
            })

        # For Employees (or all users who have an Employee profile)
        if employee_profile:
            my_today_att = Attendance.objects.filter(employee=employee_profile, attendance_date=today).first()
            my_leave_balances = LeaveBalance.objects.filter(employee=employee_profile, year=current_year).select_related('leave_type')
            my_recent_leaves = LeaveRequest.objects.filter(employee=employee_profile).order_by('-created_at')[:4]
            my_latest_payslip = PayrollRecord.objects.filter(employee=employee_profile).order_by('-year', '-month').first()

            context.update({
                'my_today_att': my_today_att,
                'my_leave_balances': my_leave_balances,
                'my_recent_leaves': my_recent_leaves,
                'my_latest_payslip': my_latest_payslip,
            })

        return render(request, self.template_name, context)

class ProfileView(LoginRequiredMixin, View):
    template_name = 'accounts/profile.html'

    def get(self, request):
        user_form = ProfileUpdateForm(instance=request.user)
        employee_profile = getattr(request.user, 'employee_profile', None)
        return render(request, self.template_name, {
            'user_form': user_form,
            'employee_profile': employee_profile,
        })

    def post(self, request):
        user_form = ProfileUpdateForm(request.POST, instance=request.user)
        if user_form.is_valid():
            user_form.save()
            messages.success(request, "Your profile details have been updated successfully.")
            return redirect('accounts:profile')
        employee_profile = getattr(request.user, 'employee_profile', None)
        return render(request, self.template_name, {
            'user_form': user_form,
            'employee_profile': employee_profile,
        })

class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = BootstrapPasswordChangeForm
    template_name = 'accounts/change_password.html'
    success_url = reverse_lazy('accounts:profile')

    def form_valid(self, form):
        messages.success(self.request, "Your password has been changed successfully.")
        return super().form_valid(form)

class UserListView(RoleRequiredMixin, ListView):
    allowed_roles = ['SUPER_ADMIN']
    model = CustomUser
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 15

    def get_queryset(self):
        qs = CustomUser.objects.all().order_by('-date_joined')
        role = self.request.GET.get('role')
        search = self.request.GET.get('search')
        if role:
            qs = qs.filter(role=role)
        if search:
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        return qs

class UserCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['SUPER_ADMIN']
    model = CustomUser
    form_class = UserCreateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def form_valid(self, form):
        messages.success(self.request, f"User account '{form.instance.username}' created successfully.")
        return super().form_valid(form)

class UserUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = ['SUPER_ADMIN']
    model = CustomUser
    form_class = UserUpdateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def form_valid(self, form):
        messages.success(self.request, f"User account '{form.instance.username}' updated successfully.")
        return super().form_valid(form)

class UserToggleActiveView(RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN']

    def post(self, request, pk):
        user_to_toggle = get_object_or_404(CustomUser, pk=pk)
        if user_to_toggle == request.user:
            messages.error(request, "You cannot deactivate your own administrative account.")
            return redirect('accounts:user_list')
        user_to_toggle.is_active = not user_to_toggle.is_active
        user_to_toggle.save()
        status_str = "activated" if user_to_toggle.is_active else "deactivated"
        messages.success(request, f"User {user_to_toggle.username} has been {status_str}.")
        return redirect('accounts:user_list')

def handler403(request, exception=None):
    return render(request, 'errors/403.html', status=403)

def handler404(request, exception=None):
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    return render(request, 'errors/500.html', status=500)
