from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
import datetime

from accounts.models import CustomUser
from departments.models import Department
from employees.models import Employee
from leave_management.models import LeaveType, LeaveBalance, LeaveRequest
from leave_management.forms import calculate_working_days

class LeaveModuleTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name='Marketing', code='MKT')
        self.user = CustomUser.objects.create_user(username='leave_tester', password='Password123!', role=CustomUser.Role.EMPLOYEE)
        self.emp = Employee.objects.create(
            employee_id='EMP-LV-01',
            user=self.user,
            first_name='Clara',
            last_name='Oswald',
            email='clara@test.com',
            phone='+1 555-8888',
            department=self.dept,
            designation='Content Lead'
        )
        self.lt_cl = LeaveType.objects.create(name='Casual Leave', code='CL', default_days_per_year=12, is_paid=True)
        self.balance = LeaveBalance.objects.create(
            employee=self.emp,
            leave_type=self.lt_cl,
            year=2026,
            total_allocated=Decimal('12.0'),
            used=Decimal('0.0'),
            remaining=Decimal('12.0')
        )

    def test_calculate_working_days_excludes_weekends(self):
        # 2026-04-10 is Friday, 2026-04-13 is Monday (span contains Sat & Sun)
        start = datetime.date(2026, 4, 10) # Friday
        end = datetime.date(2026, 4, 13)   # Monday
        # Friday + Monday = 2 working days
        days = calculate_working_days(start, end)
        self.assertEqual(days, Decimal('2.0'))

    def test_leave_approval_workflow_deducts_balance(self):
        req = LeaveRequest.objects.create(
            employee=self.emp,
            leave_type=self.lt_cl,
            start_date=datetime.date(2026, 5, 4), # Monday
            end_date=datetime.date(2026, 5, 5),   # Tuesday
            days_count=Decimal('2.0'),
            reason='Personal commitment',
            status=LeaveRequest.Status.PENDING
        )

        hr_admin = CustomUser.objects.create_user(username='hr_approver', password='Password123!', role=CustomUser.Role.HR_ADMIN)
        client = Client()
        client.login(username='hr_approver', password='Password123!')

        response = client.post(reverse('leave_management:leave_review', kwargs={'pk': req.pk}), {
            'action': 'APPROVE',
            'comments': 'Approved by HR'
        })
        self.assertEqual(response.status_code, 302)

        req.refresh_from_db()
        self.assertEqual(req.status, LeaveRequest.Status.APPROVED)
        self.assertEqual(req.reviewed_by, hr_admin)

        self.balance.refresh_from_db()
        self.assertEqual(self.balance.used, Decimal('2.0'))
        self.assertEqual(self.balance.remaining, Decimal('10.0'))

    def test_employee_cannot_approve_own_leave(self):
        req = LeaveRequest.objects.create(
            employee=self.emp,
            leave_type=self.lt_cl,
            start_date=datetime.date(2026, 6, 1),
            end_date=datetime.date(2026, 6, 2),
            days_count=Decimal('2.0'),
            status=LeaveRequest.Status.PENDING
        )
        client = Client()
        client.login(username='leave_tester', password='Password123!')
        response = client.post(reverse('leave_management:leave_review', kwargs={'pk': req.pk}), {
            'action': 'APPROVE',
            'comments': 'Self approval attempt'
        })
        self.assertEqual(response.status_code, 403) # Role check prevents employee
