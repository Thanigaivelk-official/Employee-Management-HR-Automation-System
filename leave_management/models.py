from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import datetime

class LeaveType(models.Model):
    name = models.CharField(max_length=50, unique=True, help_text="e.g. Casual Leave, Sick Leave")
    code = models.CharField(max_length=10, unique=True, help_text="e.g. CL, SL, EL, UL")
    default_days_per_year = models.PositiveIntegerField(default=12)
    is_paid = models.BooleanField(default=True)
    requires_attachment = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Leave Type'
        verbose_name_plural = 'Leave Types'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

class LeaveBalance(models.Model):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='leave_balances'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name='balances'
    )
    year = models.PositiveIntegerField(default=2026)
    total_allocated = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    used = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    remaining = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = 'Leave Balance'
        verbose_name_plural = 'Leave Balances'
        unique_together = ('employee', 'leave_type', 'year')
        ordering = ['employee', 'leave_type']

    def __str__(self):
        return f"{self.employee.employee_id} - {self.leave_type.code}: {self.remaining} left ({self.year})"

    def save(self, *args, **kwargs):
        self.remaining = self.total_allocated - self.used
        super().save(*args, **kwargs)

class LeaveRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    request_id = models.CharField(max_length=20, unique=True, blank=True)
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name='requests'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    days_count = models.DecimalField(max_digits=4, decimal_places=1, default=Decimal('1.0'))
    reason = models.TextField()
    document = models.FileField(upload_to='leave_attachments/', null=True, blank=True)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_leaves'
    )
    review_comments = models.TextField(blank=True, null=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Leave Request'
        verbose_name_plural = 'Leave Requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.request_id} - {self.employee.full_name} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.request_id:
            year = timezone.localdate().year
            last_lr = LeaveRequest.objects.filter(request_id__startswith=f"LR-{year}-").order_by('-id').first()
            if last_lr and last_lr.request_id:
                try:
                    last_num = int(last_lr.request_id.split('-')[-1])
                    new_num = last_num + 1
                except ValueError:
                    new_num = 1
            else:
                new_num = LeaveRequest.objects.count() + 1
            self.request_id = f"LR-{year}-{new_num:04d}"
        super().save(*args, **kwargs)
