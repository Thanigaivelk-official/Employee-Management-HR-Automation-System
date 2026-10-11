from .models import AuditLog

def get_client_ip(request):
    """Safely extracts client IP address from HTTP headers."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log_action(actor, action, object_type, object_id, change_summary, request=None):
    """Central logging service to append audit entries."""
    ip_address = get_client_ip(request)
    return AuditLog.objects.create(
        actor=actor if (actor and actor.is_authenticated) else None,
        action=action,
        object_type=object_type,
        object_id=str(object_id),
        change_summary=change_summary,
        ip_address=ip_address
    )
