from django.contrib import admin
from .models import Attendance

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'attendance_date', 'check_in', 'check_out', 'status', 'working_hours', 'is_late')
    list_filter = ('status', 'is_late', 'attendance_date')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_id')
