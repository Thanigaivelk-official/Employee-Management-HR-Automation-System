from django.urls import path
from .views import (
    ClockInOutView, AttendanceListView,
    AttendanceCreateView, AttendanceUpdateView
)

app_name = 'attendance'

urlpatterns = [
    path('', AttendanceListView.as_view(), name='attendance_list'),
    path('clock-in-out/', ClockInOutView.as_view(), name='clock_in_out'),
    path('add/', AttendanceCreateView.as_view(), name='attendance_add'),
    path('<int:pk>/edit/', AttendanceUpdateView.as_view(), name='attendance_edit'),
]
