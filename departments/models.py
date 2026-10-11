from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Full department name, e.g. Human Resources")
    code = models.CharField(max_length=10, unique=True, help_text="Short unique uppercase code, e.g. HR, ENG, FIN")
    description = models.TextField(blank=True, null=True)
    manager = models.ForeignKey(
        'employees.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments',
        help_text="Designated manager responsible for this department."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Soft status. Deactivated departments preserve employee history."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        if self.code:
            self.code = self.code.upper().strip()

    @property
    def active_employee_count(self):
        return self.employees.filter(employment_status='ACTIVE').count()
