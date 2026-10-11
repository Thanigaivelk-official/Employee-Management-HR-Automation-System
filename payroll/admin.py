from django.contrib import admin
from .models import SalaryStructure, PayrollRecord

@admin.register(SalaryStructure)
class SalaryStructureAdmin(admin.ModelAdmin):
    list_display = ('employee', 'basic_salary', 'hra', 'effective_from')
    search_fields = ('employee__first_name', 'employee__employee_id')

@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = ('payslip_number', 'employee', 'month', 'year', 'gross_salary', 'net_salary', 'status')
    list_filter = ('year', 'month', 'status')
    search_fields = ('payslip_number', 'employee__first_name', 'employee__employee_id')
