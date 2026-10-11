from django.test import TestCase, Client
from django.urls import reverse
from departments.models import Department
from accounts.models import CustomUser

class DepartmentModuleTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.hr_user = CustomUser.objects.create_user(
            username='hr_tester',
            email='hr@test.com',
            password='Password123!',
            role=CustomUser.Role.HR_ADMIN
        )
        self.client.login(username='hr_tester', password='Password123!')
        self.dept = Department.objects.create(name='Operations', code='OPS', description='Operations division')

    def test_department_creation_and_uppercase_code(self):
        dept = Department(name='Legal', code='leg')
        dept.full_clean()
        dept.save()
        self.assertEqual(dept.code, 'LEG')

    def test_duplicate_code_prevention(self):
        response = self.client.post(reverse('departments:department_add'), {
            'name': 'Operations Duplicate',
            'code': 'OPS',
            'description': 'Duplicate test',
            'is_active': True
        })
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIn('code', form.errors)
        self.assertIn('A department with this code already exists.', form.errors['code'])

    def test_department_soft_deactivation(self):
        self.assertTrue(self.dept.is_active)
        response = self.client.post(reverse('departments:department_toggle_active', kwargs={'pk': self.dept.pk}))
        self.dept.refresh_from_db()
        self.assertFalse(self.dept.is_active)
