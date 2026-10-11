"""
URL configuration for Employee Management & HR Automation System.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from accounts.views import DashboardView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('dashboard') if request.user.is_authenticated else redirect('accounts:login')),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('departments/', include('departments.urls', namespace='departments')),
    path('employees/', include('employees.urls', namespace='employees')),
    path('attendance/', include('attendance.urls', namespace='attendance')),
    path('leave/', include('leave_management.urls', namespace='leave_management')),
    path('payroll/', include('payroll.urls', namespace='payroll')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('audit/', include('audit.urls', namespace='audit')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler403 = 'accounts.views.handler403'
handler404 = 'accounts.views.handler404'
handler500 = 'accounts.views.handler500'
