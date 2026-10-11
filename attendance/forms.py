from django import forms
from django.utils import timezone
from .models import Attendance
from employees.models import Employee

class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['employee', 'attendance_date', 'check_in', 'check_out', 'status', 'remarks']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'attendance_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'check_in': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional remarks or correction reason...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = Employee.objects.filter(employment_status=Employee.Status.ACTIVE)
        if not self.instance.pk:
            self.fields['attendance_date'].initial = timezone.localdate()

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')
        att_date = cleaned_data.get('attendance_date')

        if att_date and att_date > timezone.localdate():
            self.add_error('attendance_date', "Cannot log attendance for future dates.")

        if check_in and check_out and check_out <= check_in:
            self.add_error('check_out', "Check-out time must be later than check-in time.")

        return cleaned_data
