from notifications.models import UserNotification


def notifications(request):

    if not request.user.is_authenticated:
        return {}

    notifications = (
        UserNotification.objects
        .select_related(
            "notification",
            "notification__type"
        )
        .filter(
            user=request.user,
            hidden=False
        )
        .order_by("-created_at")
    )

    unread_notifications = notifications.filter(read=False).count()

    return {
        "notifications": notifications[:10],
        "unread_notifications": unread_notifications,
    }