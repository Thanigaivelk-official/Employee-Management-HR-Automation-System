from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView
from django.views import View
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Q
import datetime

from .models import Attendance
from .forms import AttendanceRecordForm
from employees.models import Employee
from accounts.models import CustomUser
from accounts.decorators import RoleRequiredMixin
from audit.services import log_action

class ClockInOutView(View):
    """Allows authenticated employees to clock in and clock out for today."""
    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        employee = getattr(request.user, 'employee_profile', None)
        if not employee:
            messages.error(request, "No employee record is linked to your user account.")
            return redirect('dashboard')

        today = timezone.localdate()
        now_time = timezone.localtime().time().replace(microsecond=0)

        record, created = Attendance.objects.get_or_create(
            employee=employee,
            attendance_date=today,
            defaults={
                'check_in': now_time,
                'status': Attendance.Status.PRESENT,
                'created_by': request.user
            }
        )

        if created:
            messages.success(request, f"Successfully clocked in at {now_time.strftime('%I:%M %p')}.")
        elif record.check_out is None:
            record.check_out = now_time
            record.save()
            messages.success(request, f"Successfully clocked out at {now_time.strftime('%I:%M %p')}. Working hours: {record.working_hours} hrs.")
        else:
            messages.info(request, f"You have already clocked out for today at {record.check_out.strftime('%I:%M %p')}.")

        return redirect('dashboard')

class AttendanceListView(RoleRequiredMixin, ListView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'MANAGER', 'EMPLOYEE']
    model = Attendance
    template_name = 'attendance/attendance_list.html'
    context_object_name = 'attendances'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = Attendance.objects.select_related('employee', 'employee__department').all()

        # Scoping based on role
        if user.is_only_employee_role:
            emp = getattr(user, 'employee_profile', None)
            if emp:
                qs = qs.filter(employee=emp)
            else:
                qs = qs.none()
        elif user.role == CustomUser.Role.MANAGER and not user.is_superuser:
            qs = qs.filter(
                Q(employee__department__manager__user=user) |
                Q(employee__reporting_manager__user=user) |
                Q(employee__user=user)
            ).distinct()

        # Date filtering
        date_str = self.request.GET.get('date')
        if date_str:
            try:
                filter_date = datetime.date.fromisoformat(date_str)
                qs = qs.filter(attendance_date=filter_date)
            except ValueError:
                pass
        else:
            # Default to current month or today if not filtered
            month_str = self.request.GET.get('month')
            year_str = self.request.GET.get('year')
            if month_str and year_str:
                try:
                    qs = qs.filter(attendance_date__year=int(year_str), attendance_date__month=int(month_str))
                except ValueError:
                    pass

        # Department filter
        dept_id = self.request.GET.get('department')
        if dept_id:
            qs = qs.filter(employee__department_id=dept_id)

        # Status filter
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)

        # Search employee
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(
                Q(employee__first_name__icontains=search) |
                Q(employee__last_name__icontains=search) |
                Q(employee__employee_id__icontains=search)
            )

        return qs.order_by('-attendance_date', 'employee__first_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from departments.models import Department
        context['departments'] = Department.objects.filter(is_active=True)
        context['statuses'] = Attendance.Status.choices
        context['today'] = timezone.localdate()
        return context

class AttendanceCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN']
    model = Attendance
    form_class = AttendanceRecordForm
    template_name = 'attendance/attendance_form.html'
    success_url = reverse_lazy('attendance:attendance_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        log_action(
            actor=self.request.user,
            action='CREATE',
            object_type='Attendance',
            object_id=str(self.object.pk),
            change_summary=f"Logged attendance for {self.object.employee.full_name} on {self.object.attendance_date} ({self.object.status})",
            request=self.request
        )
        messages.success(self.request, "Attendance record created successfully.")
        return response

class AttendanceUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN']
    model = Attendance
    form_class = AttendanceRecordForm
    template_name = 'attendance/attendance_form.html'
    success_url = reverse_lazy('attendance:attendance_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(
            actor=self.request.user,
            action='UPDATE',
            object_type='Attendance',
            object_id=str(self.object.pk),
            change_summary=f"Corrected attendance record for {self.object.employee.full_name} on {self.object.attendance_date}: Status={self.object.status}, Hours={self.object.working_hours}",
            request=self.request
        )
        messages.success(self.request, "Attendance record corrected successfully with audit log entry.")
        return response
