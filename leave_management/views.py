from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, View
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
import datetime

from .models import LeaveRequest, LeaveType, LeaveBalance
from .forms import LeaveApplicationForm, LeaveReviewForm, calculate_working_days
from employees.models import Employee
from accounts.models import CustomUser
from accounts.decorators import RoleRequiredMixin
from attendance.models import Attendance
from audit.services import log_action
from notifications.services import notify_user

class LeaveRequestListView(RoleRequiredMixin, ListView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'MANAGER', 'EMPLOYEE']
    model = LeaveRequest
    template_name = 'leave_management/leave_list.html'
    context_object_name = 'leaves'
    paginate_by = 15

    def get_queryset(self):
        user = self.request.user
        qs = LeaveRequest.objects.select_related('employee', 'leave_type', 'reviewed_by').all()

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

        # Filters
        status = self.request.GET.get('status')
        leave_type_id = self.request.GET.get('leave_type')
        dept_id = self.request.GET.get('department')

        if status:
            qs = qs.filter(status=status)
        if leave_type_id:
            qs = qs.filter(leave_type_id=leave_type_id)
        if dept_id:
            qs = qs.filter(employee__department_id=dept_id)

        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from departments.models import Department
        context['leave_types'] = LeaveType.objects.all()
        context['departments'] = Department.objects.filter(is_active=True)
        context['statuses'] = LeaveRequest.Status.choices
        return context

class LeaveApplyView(RoleRequiredMixin, CreateView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'MANAGER', 'EMPLOYEE']
    model = LeaveRequest
    form_class = LeaveApplicationForm
    template_name = 'leave_management/leave_form.html'
    success_url = reverse_lazy('leave_management:leave_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['employee'] = getattr(self.request.user, 'employee_profile', None)
        return kwargs

    def form_valid(self, form):
        employee = getattr(self.request.user, 'employee_profile', None)
        if not employee:
            messages.error(self.request, "Your account does not have an associated Employee profile.")
            return redirect('leave_management:leave_list')

        form.instance.employee = employee
        form.instance.days_count = calculate_working_days(form.cleaned_data['start_date'], form.cleaned_data['end_date'])
        response = super().form_valid(form)

        log_action(
            actor=self.request.user,
            action='CREATE',
            object_type='LeaveRequest',
            object_id=str(self.object.pk),
            change_summary=f"Submitted leave request {self.object.request_id} for {self.object.days_count} days ({self.object.leave_type.name})",
            request=self.request
        )

        # Notify HR Admins or Reporting Manager
        if employee.reporting_manager and employee.reporting_manager.user:
            notify_user(
                user=employee.reporting_manager.user,
                title="New Leave Request",
                message=f"{employee.full_name} submitted a leave request ({self.object.leave_type.name}) from {self.object.start_date} to {self.object.end_date}.",
                notification_type="LEAVE",
                link=reverse('leave_management:leave_detail', kwargs={'pk': self.object.pk})
            )

        messages.success(self.request, f"Leave application {self.object.request_id} submitted successfully.")
        return response

class LeaveDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'MANAGER', 'EMPLOYEE']
    model = LeaveRequest
    template_name = 'leave_management/leave_detail.html'
    context_object_name = 'leave'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        req = self.object
        user = self.request.user

        # Determine if current user can review this request
        can_review = False
        if req.status == LeaveRequest.Status.PENDING:
            if user.is_hr_admin_role:
                can_review = True
            elif user.role == CustomUser.Role.MANAGER:
                # Manager of the employee's department or direct reporting manager
                if req.employee.department.manager and req.employee.department.manager.user == user:
                    can_review = True
                elif req.employee.reporting_manager and req.employee.reporting_manager.user == user:
                    can_review = True

            # An employee cannot approve their own leave
            if req.employee.user == user and not user.is_superuser:
                can_review = False

        context['can_review'] = can_review
        context['review_form'] = LeaveReviewForm()
        return context

class LeaveReviewView(RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'MANAGER']

    def post(self, request, pk):
        leave_req = get_object_or_404(LeaveRequest, pk=pk)
        form = LeaveReviewForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Invalid review submission.")
            return redirect('leave_management:leave_detail', pk=pk)

        action = form.cleaned_data['action']
        comments = form.cleaned_data['comments']

        # Prevent employee from approving own leave
        if leave_req.employee.user == request.user and not request.user.is_superuser:
            messages.error(request, "You cannot review or approve your own leave request.")
            return redirect('leave_management:leave_detail', pk=pk)

        with transaction.atomic():
            if action == 'APPROVE':
                leave_req.status = LeaveRequest.Status.APPROVED
                leave_req.reviewed_by = request.user
                leave_req.reviewed_at = timezone.now()
                leave_req.review_comments = comments
                leave_req.save()

                # Deduct balance if paid leave
                if leave_req.leave_type.is_paid:
                    balance = LeaveBalance.objects.filter(
                        employee=leave_req.employee,
                        leave_type=leave_req.leave_type,
                        year=leave_req.start_date.year
                    ).first()
                    if balance:
                        balance.used += leave_req.days_count
                        balance.save()

                # Create attendance records for working days in range
                curr_date = leave_req.start_date
                while curr_date <= leave_req.end_date:
                    if curr_date.weekday() < 5:  # Monday to Friday
                        att, _ = Attendance.objects.get_or_create(
                            employee=leave_req.employee,
                            attendance_date=curr_date,
                            defaults={
                                'status': Attendance.Status.LEAVE,
                                'remarks': f"Approved Leave ({leave_req.leave_type.code})",
                                'created_by': request.user
                            }
                        )
                        att.status = Attendance.Status.LEAVE
                        att.save()
                    curr_date += datetime.timedelta(days=1)

                log_action(
                    actor=request.user,
                    action='APPROVE',
                    object_type='LeaveRequest',
                    object_id=str(leave_req.pk),
                    change_summary=f"Approved leave {leave_req.request_id} for {leave_req.employee.full_name} ({leave_req.days_count} days)",
                    request=request
                )

                if leave_req.employee.user:
                    notify_user(
                        user=leave_req.employee.user,
                        title="Leave Request Approved",
                        message=f"Your leave request {leave_req.request_id} from {leave_req.start_date} to {leave_req.end_date} has been approved.",
                        notification_type="LEAVE",
                        link=reverse('leave_management:leave_detail', kwargs={'pk': leave_req.pk})
                    )

                messages.success(request, f"Leave request {leave_req.request_id} approved successfully.")

            elif action == 'REJECT':
                leave_req.status = LeaveRequest.Status.REJECTED
                leave_req.reviewed_by = request.user
                leave_req.reviewed_at = timezone.now()
                leave_req.review_comments = comments
                leave_req.save()

                log_action(
                    actor=request.user,
                    action='REJECT',
                    object_type='LeaveRequest',
                    object_id=str(leave_req.pk),
                    change_summary=f"Rejected leave {leave_req.request_id} for {leave_req.employee.full_name}. Reason: {comments}",
                    request=request
                )

                if leave_req.employee.user:
                    notify_user(
                        user=leave_req.employee.user,
                        title="Leave Request Rejected",
                        message=f"Your leave request {leave_req.request_id} was rejected. Note: {comments}",
                        notification_type="LEAVE",
                        link=reverse('leave_management:leave_detail', kwargs={'pk': leave_req.pk})
                    )

                messages.warning(request, f"Leave request {leave_req.request_id} was rejected.")

        return redirect('leave_management:leave_detail', pk=pk)

class LeaveCancelView(RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'MANAGER', 'EMPLOYEE']

    def post(self, request, pk):
        leave_req = get_object_or_404(LeaveRequest, pk=pk)

        # Ensure only the employee who applied (or Super Admin) can cancel
        if not (request.user.is_super_admin_role or (leave_req.employee.user and leave_req.employee.user == request.user)):
            messages.error(request, "You are not authorized to cancel this leave request.")
            return redirect('leave_management:leave_detail', pk=pk)

        if leave_req.status in [LeaveRequest.Status.REJECTED, LeaveRequest.Status.CANCELLED]:
            messages.info(request, "This request is already resolved.")
            return redirect('leave_management:leave_detail', pk=pk)

        with transaction.atomic():
            was_approved = (leave_req.status == LeaveRequest.Status.APPROVED)
            leave_req.status = LeaveRequest.Status.CANCELLED
            leave_req.save()

            if was_approved and leave_req.leave_type.is_paid:
                # Refund balance
                balance = LeaveBalance.objects.filter(
                    employee=leave_req.employee,
                    leave_type=leave_req.leave_type,
                    year=leave_req.start_date.year
                ).first()
                if balance:
                    balance.used = max(Decimal('0.00'), balance.used - leave_req.days_count)
                    balance.save()

                # Clean up attendance records marked as leave
                Attendance.objects.filter(
                    employee=leave_req.employee,
                    attendance_date__gte=leave_req.start_date,
                    attendance_date__lte=leave_req.end_date,
                    status=Attendance.Status.LEAVE
                ).delete()

            log_action(
                actor=request.user,
                action='UPDATE',
                object_type='LeaveRequest',
                object_id=str(leave_req.pk),
                change_summary=f"Cancelled leave request {leave_req.request_id} (Reverted balances: {was_approved})",
                request=request
            )

        messages.success(request, f"Leave request {leave_req.request_id} has been cancelled.")
        return redirect('leave_management:leave_list')

class LeaveBalanceListView(RoleRequiredMixin, ListView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'MANAGER', 'EMPLOYEE']
    model = LeaveBalance
    template_name = 'leave_management/leave_balances.html'
    context_object_name = 'balances'

    def get_queryset(self):
        user = self.request.user
        current_year = timezone.localdate().year
        year = self.request.GET.get('year', current_year)

        qs = LeaveBalance.objects.select_related('employee', 'leave_type').filter(year=year)

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

        return qs.order_by('employee__first_name', 'leave_type__name')
