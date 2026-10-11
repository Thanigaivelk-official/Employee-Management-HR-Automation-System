from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP

class SalaryStructure(models.Model):
    employee = models.OneToOneField(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='salary_structure'
    )
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('30000.00'))
    hra = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('12000.00'), help_text="House Rent Allowance")
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('2000.00'))
    medical_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1500.00'))
    special_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1000.00'))
    pf_rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('12.00'), help_text="Provident Fund Rate %")
    professional_tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('200.00'))
    effective_from = models.DateField(default=timezone.localdate)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Salary Structure'
        verbose_name_plural = 'Salary Structures'

    def __str__(self):
        return f"Salary Structure - {self.employee.full_name} ({self.employee.employee_id})"

    @property
    def total_monthly_allowances(self):
        return self.hra + self.transport_allowance + self.medical_allowance + self.special_allowance

    @property
    def standard_gross_monthly(self):
        return self.basic_salary + self.total_monthly_allowances

class PayrollRecord(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PROCESSED = 'PROCESSED', 'Processed'
        PAID = 'PAID', 'Paid'

    payslip_number = models.CharField(max_length=30, unique=True, blank=True)
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.PROTECT,
        related_name='payroll_records'
    )
    month = models.PositiveSmallIntegerField(help_text="Month number 1-12")
    year = models.PositiveIntegerField(help_text="Year, e.g. 2026")

    # Earnings snapshot
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    hra = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    allowances_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2)

    # Deductions snapshot
    pf_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tax_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    unpaid_leave_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2)

    # Net Output
    net_salary = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROCESSED)
    payment_date = models.DateField(null=True, blank=True)
    processed_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_payrolls'
    )

    class Meta:
        verbose_name = 'Payroll Record'
        verbose_name_plural = 'Payroll Records'
        unique_together = ('employee', 'month', 'year')
        ordering = ['-year', '-month', 'employee__employee_id']

    def __str__(self):
        return f"{self.payslip_number} - {self.employee.full_name} ({self.month}/{self.year})"

    def save(self, *args, **kwargs):
        if not self.payslip_number:
            self.payslip_number = f"PAY-{self.year}{self.month:02d}-{self.employee.pk:04d}"
        super().save(*args, **kwargs)
