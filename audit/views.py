from django.shortcuts import render
from django.views.generic import ListView
from django.db.models import Q
from .models import AuditLog
from accounts.decorators import RoleRequiredMixin

class AuditLogListView(RoleRequiredMixin, ListView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN']
    model = AuditLog
    template_name = 'audit/audit_list.html'
    context_object_name = 'audit_logs'
    paginate_by = 25

    def get_queryset(self):
        qs = AuditLog.objects.select_related('actor').all()
        action = self.request.GET.get('action')
        object_type = self.request.GET.get('object_type')
        search = self.request.GET.get('search')

        if action:
            qs = qs.filter(action=action)
        if object_type:
            qs = qs.filter(object_type=object_type)
        if search:
            qs = qs.filter(
                Q(actor__username__icontains=search) |
                Q(change_summary__icontains=search) |
                Q(object_id__icontains=search)
            )

        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['actions'] = AuditLog.ActionType.choices
        context['object_types'] = ['Employee', 'Department', 'Attendance', 'LeaveRequest', 'Payroll', 'User']
        return context
