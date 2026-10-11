from django.test import TestCase, Client
from django.urls import reverse
from django.db import IntegrityError
from decimal import Decimal
import datetime

from accounts.models import CustomUser
from departments.models import Department
from employees.models import Employee
from attendance.models import Attendance

class AttendanceModuleTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name='Design', code='DSG')
        self.user = CustomUser.objects.create_user(username='att_tester', role=CustomUser.Role.EMPLOYEE)
        self.emp = Employee.objects.create(
            employee_id='EMP-ATT-01',
            user=self.user,
            first_name='Tom',
            last_name='Hardy',
            email='tom@test.com',
            phone='+1 555-9999',
            department=self.dept,
            designation='UI Designer'
        )

    def test_working_hours_calculation_and_late_arrival(self):
        att = Attendance.objects.create(
            employee=self.emp,
            attendance_date=datetime.date(2026, 4, 10),
            check_in=datetime.time(9, 45, 0),   # Late (after 09:30)
            check_out=datetime.time(18, 45, 0), # 9 hours
        )
        self.assertTrue(att.is_late)
        self.assertEqual(att.working_hours, Decimal('9.00'))
        self.assertEqual(att.status, Attendance.Status.PRESENT)

    def test_half_day_calculation(self):
        att = Attendance.objects.create(
            employee=self.emp,
            attendance_date=datetime.date(2026, 4, 11),
            check_in=datetime.time(9, 0, 0),
            check_out=datetime.time(14, 0, 0), # 5 hours
        )
        self.assertFalse(att.is_late)
        self.assertEqual(att.working_hours, Decimal('5.00'))
        self.assertEqual(att.status, Attendance.Status.HALF_DAY)

    def test_duplicate_attendance_same_day_prevention(self):
        Attendance.objects.create(
            employee=self.emp,
            attendance_date=datetime.date(2026, 4, 12),
            status=Attendance.Status.PRESENT
        )
        with self.assertRaises(IntegrityError):
            Attendance.objects.create(
                employee=self.emp,
                attendance_date=datetime.date(2026, 4, 12),
                status=Attendance.Status.PRESENT
            )
