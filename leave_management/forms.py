from django import forms
from django.utils import timezone
from decimal import Decimal
import datetime

from .models import LeaveRequest, LeaveType, LeaveBalance
from employees.models import Employee

def calculate_working_days(start_date, end_date):
    """Calculates weekdays (Monday through Friday) between start and end date inclusive."""
    current = start_date
    days = 0
    while current <= end_date:
        if current.weekday() < 5:  # Monday=0, Friday=4, Saturday=5, Sunday=6
            days += 1
        current += datetime.timedelta(days=1)
    return Decimal(days) if days > 0 else Decimal('1.0')

class LeaveApplicationForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason', 'document']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Provide justification for leave...'}),
            'document': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        leave_type = cleaned_data.get('leave_type')
        document = cleaned_data.get('document')

        if not start_date or not end_date or not leave_type:
            return cleaned_data

        if end_date < start_date:
            self.add_error('end_date', "End date cannot be prior to start date.")
            return cleaned_data

        # Calculate working days
        days = calculate_working_days(start_date, end_date)
        cleaned_data['days_count'] = days

        if self.employee:
            # Check for overlapping leave requests (PENDING or APPROVED)
            overlaps = LeaveRequest.objects.filter(
                employee=self.employee,
                status__in=[LeaveRequest.Status.PENDING, LeaveRequest.Status.APPROVED]
            ).filter(
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            if self.instance.pk:
                overlaps = overlaps.exclude(pk=self.instance.pk)

            if overlaps.exists():
                raise forms.ValidationError("You already have a pending or approved leave request spanning these dates.")

            # Check leave balance if it's a paid leave
            if leave_type.is_paid:
                year = start_date.year
                balance = LeaveBalance.objects.filter(
                    employee=self.employee,
                    leave_type=leave_type,
                    year=year
                ).first()
                if balance and balance.remaining < days:
                    raise forms.ValidationError(
                        f"Insufficient {leave_type.name} balance. Available: {balance.remaining} days, Requested: {days} days."
                    )

        if leave_type.requires_attachment and not document and not (self.instance.pk and self.instance.document):
            self.add_error('document', f"{leave_type.name} requires supporting documentation (e.g. medical certificate).")

        return cleaned_data

class LeaveReviewForm(forms.Form):
    ACTION_CHOICES = [
        ('APPROVE', 'Approve Request'),
        ('REJECT', 'Reject Request'),
    ]
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    comments = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reviewer comments or justification...'})
    )
