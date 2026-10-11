from django import forms
from django.utils import timezone
from .models import Employee
from departments.models import Department
from accounts.models import CustomUser

class EmployeeForm(forms.ModelForm):
    create_user_account = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Automatically create a login account for this employee if none exists."
    )
    user_role = forms.ChoiceField(
        choices=CustomUser.Role.choices,
        initial=CustomUser.Role.EMPLOYEE,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Employee
        fields = [
            'employee_id', 'first_name', 'last_name', 'email', 'phone',
            'date_of_birth', 'gender', 'address', 'profile_picture',
            'date_of_joining', 'department', 'designation', 'reporting_manager',
            'employment_type', 'employment_status', 'basic_salary', 'emergency_contact'
        ]
        widgets = {
            'employee_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank to auto-generate'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@company.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 555-0123'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Residential address...'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'date_of_joining': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'designation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Senior Software Engineer'}),
            'reporting_manager': forms.Select(attrs={'class': 'form-select'}),
            'employment_type': forms.Select(attrs={'class': 'form-select'}),
            'employment_status': forms.Select(attrs={'class': 'form-select'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency contact phone or name'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.filter(is_active=True)
        self.fields['reporting_manager'].queryset = Employee.objects.filter(employment_status=Employee.Status.ACTIVE)
        if self.instance.pk:
            self.fields['employee_id'].widget.attrs['readonly'] = True
            # Exclude self from reporting managers to prevent cyclical hierarchy
            self.fields['reporting_manager'].queryset = self.fields['reporting_manager'].queryset.exclude(pk=self.instance.pk)

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        qs = Employee.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("An employee with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        dob = cleaned_data.get('date_of_birth')
        doj = cleaned_data.get('date_of_joining')

        if dob and doj and dob >= doj:
            self.add_error('date_of_birth', "Date of birth must be before date of joining.")
        if dob and dob > timezone.localdate():
            self.add_error('date_of_birth', "Date of birth cannot be in the future.")

        return cleaned_data
