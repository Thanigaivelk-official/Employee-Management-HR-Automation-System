from .models import Notification

def notify_user(user, title, message, notification_type=Notification.NotificationType.SYSTEM, link=None):
    """Creates a persistent in-app notification for a given user."""
    if not user:
        return None
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link
    )
