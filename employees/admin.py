from django.contrib import admin
from .models import Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'first_name', 'last_name', 'email', 'department', 'designation', 'employment_status')
    list_filter = ('employment_status', 'employment_type', 'department')
    search_fields = ('employee_id', 'first_name', 'last_name', 'email')
    ordering = ('employee_id',)
