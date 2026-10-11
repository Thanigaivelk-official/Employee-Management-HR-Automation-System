from django.contrib import admin
from .models import LeaveType, LeaveBalance, LeaveRequest

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'default_days_per_year', 'is_paid', 'requires_attachment')

@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'year', 'total_allocated', 'used', 'remaining')
    list_filter = ('year', 'leave_type')
    search_fields = ('employee__first_name', 'employee__employee_id')

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('request_id', 'employee', 'leave_type', 'start_date', 'end_date', 'days_count', 'status')
    list_filter = ('status', 'leave_type', 'start_date')
    search_fields = ('request_id', 'employee__first_name', 'employee__employee_id')
