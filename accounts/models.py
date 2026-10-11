from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        HR_ADMIN = 'HR_ADMIN', 'HR Administrator'
        MANAGER = 'MANAGER', 'Department Manager'
        EMPLOYEE = 'EMPLOYEE', 'Employee'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
        help_text="Role determining application-level permissions and access hierarchy."
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_super_admin_role(self):
        return self.role == self.Role.SUPER_ADMIN or self.is_superuser

    @property
    def is_hr_admin_role(self):
        return self.role in [self.Role.SUPER_ADMIN, self.Role.HR_ADMIN] or self.is_superuser

    @property
    def is_manager_role(self):
        return self.role in [self.Role.SUPER_ADMIN, self.Role.HR_ADMIN, self.Role.MANAGER] or self.is_superuser

    @property
    def is_only_employee_role(self):
        return self.role == self.Role.EMPLOYEE and not self.is_superuser
