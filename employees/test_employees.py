from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
import datetime

from accounts.models import CustomUser
from departments.models import Department
from employees.models import Employee

class EmployeeModuleTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.hr_user = CustomUser.objects.create_user(
            username='hr_emp_tester',
            email='hr_emp@test.com',
            password='Password123!',
            role=CustomUser.Role.HR_ADMIN
        )
        self.client.login(username='hr_emp_tester', password='Password123!')
        self.dept = Department.objects.create(name='Tech', code='TEC')

    def test_auto_generate_employee_id(self):
        emp = Employee.objects.create(
            first_name='John',
            last_name='Doe',
            email='john.doe@test.com',
            phone='+1 555-1111',
            department=self.dept,
            designation='Engineer',
            basic_salary=Decimal('50000.00'),
            date_of_joining=datetime.date(2026, 1, 1)
        )
        self.assertTrue(emp.employee_id.startswith('EMP-2026-'))
        self.assertEqual(emp.full_name, 'John Doe')

    def test_unique_email_validation(self):
        Employee.objects.create(
            employee_id='EMP-TEST-01',
            first_name='Alice',
            last_name='Smith',
            email='alice@test.com',
            phone='+1 555-2222',
            department=self.dept,
            designation='Analyst'
        )
        # Attempt duplicate email submission via form
        response = self.client.post(reverse('employees:employee_add'), {
            'first_name': 'Alice Two',
            'last_name': 'Smith',
            'email': 'alice@test.com',
            'phone': '+1 555-3333',
            'department': self.dept.pk,
            'designation': 'Senior Analyst',
            'date_of_joining': '2026-02-01',
            'basic_salary': '55000.00',
            'employment_type': 'FULL_TIME',
            'employment_status': 'ACTIVE'
        })
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIn('email', form.errors)
        self.assertIn('An employee with this email already exists.', form.errors['email'])

    def test_search_employees(self):
        Employee.objects.create(
            employee_id='EMP-SEARCH-01',
            first_name='UniqueNameGuy',
            last_name='Bar',
            email='unique@test.com',
            phone='+1 555-4444',
            department=self.dept,
            designation='Dev'
        )
        response = self.client.get(reverse('employees:employee_list') + '?search=UniqueNameGuy')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'UniqueNameGuy')
