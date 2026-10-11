from django.urls import path
from .views import (
    DepartmentListView, DepartmentDetailView,
    DepartmentCreateView, DepartmentUpdateView, DepartmentToggleActiveView
)

app_name = 'departments'

urlpatterns = [
    path('', DepartmentListView.as_view(), name='department_list'),
    path('add/', DepartmentCreateView.as_view(), name='department_add'),
    path('<int:pk>/', DepartmentDetailView.as_view(), name='department_detail'),
    path('<int:pk>/edit/', DepartmentUpdateView.as_view(), name='department_edit'),
    path('<int:pk>/toggle-active/', DepartmentToggleActiveView.as_view(), name='department_toggle_active'),
]
