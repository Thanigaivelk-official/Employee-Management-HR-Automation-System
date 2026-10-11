from django.urls import path
from .views import (
    EmployeeListView, EmployeeDetailView,
    EmployeeCreateView, EmployeeUpdateView, EmployeeDeactivateView
)

app_name = 'employees'

urlpatterns = [
    path('', EmployeeListView.as_view(), name='employee_list'),
    path('add/', EmployeeCreateView.as_view(), name='employee_add'),
    path('<int:pk>/', EmployeeDetailView.as_view(), name='employee_detail'),
    path('<int:pk>/edit/', EmployeeUpdateView.as_view(), name='employee_edit'),
    path('<int:pk>/deactivate/', EmployeeDeactivateView.as_view(), name='employee_deactivate'),
]
