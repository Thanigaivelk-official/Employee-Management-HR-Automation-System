from django import forms
from django.utils import timezone
from .models import SalaryStructure, PayrollRecord
from employees.models import Employee
from departments.models import Department

class SalaryStructureForm(forms.ModelForm):
    class Meta:
        model = SalaryStructure
        fields = [
            'basic_salary', 'hra', 'transport_allowance',
            'medical_allowance', 'special_allowance',
            'pf_rate_percent', 'professional_tax', 'effective_from'
        ]
        widgets = {
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'hra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'transport_allowance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'medical_allowance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'special_allowance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'pf_rate_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'professional_tax': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'effective_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class PayrollRunForm(forms.Form):
    MONTH_CHOICES = [(i, timezone.datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)]
    
    current_year = timezone.localdate().year
    current_month = timezone.localdate().month

    month = forms.ChoiceField(
        choices=MONTH_CHOICES,
        initial=current_month,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    year = forms.IntegerField(
        initial=current_year,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
        empty_label="All Departments",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
