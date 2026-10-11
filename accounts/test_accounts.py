from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser

class AuthenticationAndRBACTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superadmin = CustomUser.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='Password123!',
            role=CustomUser.Role.SUPER_ADMIN,
            is_staff=True,
            is_superuser=True
        )
        self.employee_user = CustomUser.objects.create_user(
            username='emp_test',
            email='emp@test.com',
            password='Password123!',
            role=CustomUser.Role.EMPLOYEE
        )

    def test_valid_login(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'admin_test',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))

    def test_invalid_login(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'admin_test',
            'password': 'WrongPassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password")

    def test_unauthenticated_access_redirects(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_user_management_restricted_to_superadmin(self):
        # Employee should be denied
        self.client.login(username='emp_test', password='Password123!')
        response = self.client.get(reverse('accounts:user_list'))
        self.assertEqual(response.status_code, 403)

        # Super admin should be allowed
        self.client.login(username='admin_test', password='Password123!')
        response = self.client.get(reverse('accounts:user_list'))
        self.assertEqual(response.status_code, 200)
