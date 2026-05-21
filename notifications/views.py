import json
import time

from django.shortcuts import render
from notifications.models import Notification, NotificationType, UserNotification
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.http import JsonResponse, StreamingHttpResponse
from django.template.loader import render_to_string
# Create your views here.

class SendNotification():
    
    @staticmethod
    def get_type(name, icon, color):
        notification_type, _ = NotificationType.objects.get_or_create(
            name=name,
            defaults={
                "icon": icon,
                "color": color,
            }
        )

        return notification_type


    @staticmethod
    def send(
        title,
        descript,
        notification_type,
        send_to_all=False,
        send_to=None,
        action_kind="",
        ticket_id=None
    ):
        notification = Notification.objects.create(
            title=title,
            description=descript,
            type=notification_type,
            send_all=send_to_all,
            action_kind=action_kind,
            ticket_id=ticket_id
        )

        if send_to_all:
            User = get_user_model()
            user_notifications = [
                UserNotification(
                    notification=notification,
                    user=user,
                    read=False,
                    hidden=False
                )
                for user in User.objects.filter(is_active=True)
            ]

            UserNotification.objects.bulk_create(user_notifications, ignore_conflicts=True)
            return notification

        if send_to:
            UserNotification.objects.create(
                notification=notification,
                user=send_to,
                read=False,
                hidden=False
            )

        return notification


    @staticmethod
    def success(
        request,
        title,
        descript,
        send_to_all=False,
        send_to=None,
        action_kind="",
        ticket_id=None
    ):
        
        type = SendNotification.get_type("Sucesso", "fas fa-check-circle", "success")
        return SendNotification.send(title, descript, type, send_to_all, send_to, action_kind, ticket_id)


    @staticmethod
    def warning(
        request,
        title,
        descript,
        send_to_all=False,
        send_to=None,
        action_kind="",
        ticket_id=None
    ):

        type = SendNotification.get_type("Aviso", "fas fa-circle-exclamation", "warning")
        return SendNotification.send(title, descript, type, send_to_all, send_to, action_kind, ticket_id)


@login_required
def mark_notifications_read(request):

    if request.method == "POST":

        UserNotification.objects.filter(
            user=request.user,
            read=False
        ).update(read=True)

        return JsonResponse({
            "success": True
        })

    return JsonResponse({
        "success": False
    }, status=400)


@login_required
def notifications_snapshot(request):

    return JsonResponse(build_notifications_payload(request))


def build_notifications_payload(request):

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

    html = render_to_string(
        "notification_items.html",
        {
            "notifications": notifications[:10],
        },
        request=request
    )

    latest_notification_id = notifications.values_list("id", flat=True).first() or 0

    return {
        "success": True,
        "html": html,
        "unread_notifications": unread_notifications,
        "latest_notification_id": latest_notification_id,
    }


@login_required
def notifications_events(request):

    def event_stream():
        last_seen = request.GET.get("last_seen") or "0"

        try:
            last_seen = int(last_seen)
        except ValueError:
            last_seen = 0

        for _ in range(30):
            close_old_connections()
            payload = build_notifications_payload(request)

            if payload["latest_notification_id"] > last_seen:
                yield f"data: {json.dumps(payload)}\n\n"
                return

            time.sleep(2)

        yield "event: heartbeat\ndata: {}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream"
    )
    response["Cache-Control"] = "no-cache"
    return response
