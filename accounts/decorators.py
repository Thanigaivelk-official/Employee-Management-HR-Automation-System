from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.contrib import messages

def role_required(allowed_roles):
    """
    Decorator for views that checks whether a user has one of the allowed roles.
    Superusers automatically pass.
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.is_superuser or request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "Access denied: You do not have permission to access this resource.")
            raise PermissionDenied
        return _wrapped_view
    return decorator

def hr_or_admin_required(view_func):
    return role_required(['SUPER_ADMIN', 'HR_ADMIN'])(view_func)

def manager_or_higher_required(view_func):
    return role_required(['SUPER_ADMIN', 'HR_ADMIN', 'MANAGER'])(view_func)

class RoleRequiredMixin(UserPassesTestMixin):
    """
    CBV mixin that checks if current user's role is in allowed_roles.
    """
    allowed_roles = []

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.role in self.allowed_roles

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect('accounts:login')
        messages.error(self.request, "Access denied: You do not have permission to perform this action.")
        raise PermissionDenied
