from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser
from departments.models import Department
from employees.models import Employee

class ReportsModuleTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name='QA', code='QA')
        self.hr_user = CustomUser.objects.create_user(username='hr_reports', password='Password123!', role=CustomUser.Role.HR_ADMIN)
        self.client = Client()
        self.client.login(username='hr_reports', password='Password123!')
        Employee.objects.create(
            employee_id='EMP-REP-01',
            first_name='Barry',
            last_name='Allen',
            email='barry@test.com',
            phone='+1 555-6666',
            department=self.dept,
            designation='SDET'
        )

    def test_export_employees_csv(self):
        response = self.client.get(reverse('reports:export_employees_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertContains(response, 'Barry Allen')

    def test_export_employees_pdf(self):
        response = self.client.get(reverse('reports:export_employees_pdf'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF-'))
