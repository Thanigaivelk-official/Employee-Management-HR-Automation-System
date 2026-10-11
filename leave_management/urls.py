from django.urls import path
from .views import (
    LeaveRequestListView, LeaveApplyView,
    LeaveDetailView, LeaveReviewView,
    LeaveCancelView, LeaveBalanceListView
)

app_name = 'leave_management'

urlpatterns = [
    path('', LeaveRequestListView.as_view(), name='leave_list'),
    path('apply/', LeaveApplyView.as_view(), name='leave_apply'),
    path('balances/', LeaveBalanceListView.as_view(), name='leave_balances'),
    path('<int:pk>/', LeaveDetailView.as_view(), name='leave_detail'),
    path('<int:pk>/review/', LeaveReviewView.as_view(), name='leave_review'),
    path('<int:pk>/cancel/', LeaveCancelView.as_view(), name='leave_cancel'),
]
