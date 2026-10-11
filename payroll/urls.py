from django.urls import path
from .views import (
    PayrollListView, PayrollDetailView,
    DownloadPayslipPDFView, PayrollGenerateView,
    SalaryStructureUpdateView
)

app_name = 'payroll'

urlpatterns = [
    path('', PayrollListView.as_view(), name='payroll_list'),
    path('generate/', PayrollGenerateView.as_view(), name='payroll_generate'),
    path('<int:pk>/', PayrollDetailView.as_view(), name='payroll_detail'),
    path('<int:pk>/pdf/', DownloadPayslipPDFView.as_view(), name='payslip_pdf'),
    path('salary-structure/<int:pk>/edit/', SalaryStructureUpdateView.as_view(), name='salary_structure_edit'),
]
