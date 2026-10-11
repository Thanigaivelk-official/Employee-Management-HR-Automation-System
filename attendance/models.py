from django.db import models
from django.conf import settings
from decimal import Decimal
import datetime

class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'
        HALF_DAY = 'HALF_DAY', 'Half Day'
        LEAVE = 'LEAVE', 'On Leave'
        HOLIDAY = 'HOLIDAY', 'Holiday'
        WEEKLY_OFF = 'WEEKLY_OFF', 'Weekly Off'

    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    attendance_date = models.DateField(db_index=True)
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PRESENT
    )
    working_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Calculated work duration in hours."
    )
    is_late = models.BooleanField(
        default=False,
        help_text="Flagged when check-in is past the grace period (e.g. 09:30 AM)."
    )
    remarks = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_attendance_records'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendance Records'
        unique_together = ('employee', 'attendance_date')
        ordering = ['-attendance_date', 'employee']
        indexes = [
            models.Index(fields=['attendance_date', 'status']),
        ]

    def __str__(self):
        return f"{self.employee.employee_id} - {self.attendance_date} ({self.get_status_display()})"

    def calculate_hours(self):
        """Calculates working duration and late arrival flag."""
        if self.check_in and self.check_out:
            t1 = datetime.datetime.combine(self.attendance_date, self.check_in)
            t2 = datetime.datetime.combine(self.attendance_date, self.check_out)
            if t2 > t1:
                duration_seconds = (t2 - t1).total_seconds()
                hours = round(Decimal(duration_seconds / 3600.0), 2)
                self.working_hours = hours
                if hours >= Decimal('7.0'):
                    self.status = self.Status.PRESENT
                elif hours >= Decimal('4.0'):
                    self.status = self.Status.HALF_DAY
                else:
                    self.status = self.Status.ABSENT

        # Grace period for late check-in: 09:30:00
        if self.check_in:
            if self.check_in > datetime.time(9, 30, 0):
                self.is_late = True
            else:
                self.is_late = False

    def save(self, *args, **kwargs):
        self.calculate_hours()
        super().save(*args, **kwargs)
