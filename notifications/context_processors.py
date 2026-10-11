from .models import Notification

def unread_notifications(request):
    """Context processor making unread notification counts and latest alerts globally accessible in templates."""
    if request.user.is_authenticated:
        qs = Notification.objects.filter(user=request.user, is_read=False)
        return {
            'unread_notifications_count': qs.count(),
            'navbar_notifications': qs[:5]
        }
    return {
        'unread_notifications_count': 0,
        'navbar_notifications': []
    }
