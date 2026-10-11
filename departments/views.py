from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.views import View
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Count, Q

from .models import Department
from .forms import DepartmentForm
from accounts.decorators import RoleRequiredMixin
from audit.services import log_action

class DepartmentListView(RoleRequiredMixin, ListView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'MANAGER', 'EMPLOYEE']
    model = Department
    template_name = 'departments/department_list.html'
    context_object_name = 'departments'
    paginate_by = 12

    def get_queryset(self):
        qs = Department.objects.select_related('manager').annotate(
            total_active_staff=Count('employees', filter=Q(employees__employment_status='ACTIVE'))
        ).order_by('name')

        search = self.request.GET.get('search')
        status = self.request.GET.get('status')

        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(code__icontains=search))
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)

        return qs

class DepartmentDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN', 'MANAGER', 'EMPLOYEE']
    model = Department
    template_name = 'departments/department_detail.html'
    context_object_name = 'department'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch employees in this department
        context['employees'] = self.object.employees.select_related('user').order_by('first_name', 'last_name')
        return context

class DepartmentCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN']
    model = Department
    form_class = DepartmentForm
    template_name = 'departments/department_form.html'
    success_url = reverse_lazy('departments:department_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(
            actor=self.request.user,
            action='CREATE',
            object_type='Department',
            object_id=str(self.object.pk),
            change_summary=f"Created department '{self.object.name}' ({self.object.code})",
            request=self.request
        )
        messages.success(self.request, f"Department '{self.object.name}' has been created successfully.")
        return response

class DepartmentUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN']
    model = Department
    form_class = DepartmentForm
    template_name = 'departments/department_form.html'
    success_url = reverse_lazy('departments:department_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(
            actor=self.request.user,
            action='UPDATE',
            object_type='Department',
            object_id=str(self.object.pk),
            change_summary=f"Updated department '{self.object.name}' details",
            request=self.request
        )
        messages.success(self.request, f"Department '{self.object.name}' updated successfully.")
        return response

class DepartmentToggleActiveView(RoleRequiredMixin, View):
    allowed_roles = ['SUPER_ADMIN', 'HR_ADMIN']

    def post(self, request, pk):
        department = get_object_or_404(Department, pk=pk)
        department.is_active = not department.is_active
        department.save()
        status_text = "activated" if department.is_active else "deactivated"
        log_action(
            actor=request.user,
            action='UPDATE',
            object_type='Department',
            object_id=str(department.pk),
            change_summary=f"Soft {status_text} department '{department.name}'",
            request=request
        )
        messages.success(request, f"Department '{department.name}' has been {status_text}.")
        return redirect('departments:department_list')
