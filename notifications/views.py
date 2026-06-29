import json
import time

from django.conf import settings
from notifications.models import Notification, NotificationType, UserNotification
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST
# Create your views here.

BROWSER_NOTIFICATION_LIMIT = 10

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
        ticket_id=None,
        url="",
    ):
        if not url and ticket_id:
            url = reverse("ticket_detail", kwargs={"ticket_id": ticket_id})

        notification = Notification.objects.create(
            title=title,
            description=descript,
            type=notification_type,
            send_all=send_to_all,
            action_kind=action_kind,
            ticket_id=ticket_id,
            url=url,
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
        ticket_id=None,
        url="",
    ):
        
        type = SendNotification.get_type("Sucesso", "fas fa-check-circle", "success")
        return SendNotification.send(
            title, descript, type, send_to_all, send_to, action_kind, ticket_id, url
        )


    @staticmethod
    def warning(
        request,
        title,
        descript,
        send_to_all=False,
        send_to=None,
        action_kind="",
        ticket_id=None,
        url="",
    ):

        type = SendNotification.get_type("Aviso", "fas fa-circle-exclamation", "warning")
        return SendNotification.send(
            title, descript, type, send_to_all, send_to, action_kind, ticket_id, url
        )


def _safe_notification_url(request, notification):
    """Impede que uma URL cadastrada redirecione o usuario para outro dominio."""
    target_url = notification.get_target_url()
    is_safe = url_has_allowed_host_and_scheme(
        target_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )
    return target_url if is_safe else reverse("home")


@login_required
@require_GET
def pending_browser_notifications(request):
    """Lista, em lotes pequenos, avisos nativos ainda nao exibidos ao usuario."""
    pending = (
        UserNotification.objects
        .select_related("notification")
        .filter(
            user=request.user,
            hidden=False,
            browser_notified=False,
        )
        .order_by("created_at")[:BROWSER_NOTIFICATION_LIMIT]
    )

    items = [
        {
            "id": item.id,
            "title": item.notification.title,
            "message": item.notification.description,
            "url": _safe_notification_url(request, item.notification),
            "mark_displayed_url": reverse(
                "mark_browser_notification_displayed",
                kwargs={"notification_id": item.id},
            ),
            "mark_read_url": reverse(
                "mark_browser_notification_read",
                kwargs={"notification_id": item.id},
            ),
        }
        for item in pending
    ]

    return JsonResponse({
        "success": True,
        "app_name": getattr(settings, "HELPDESK_NAME", "HelpDesk"),
        "notifications": items,
    })


@login_required
@require_POST
def mark_browser_notification_displayed(request, notification_id):
    """Confirma que o navegador conseguiu criar a notificacao nativa."""
    user_notification = get_object_or_404(
        UserNotification,
        id=notification_id,
        user=request.user,
    )

    if not user_notification.browser_notified:
        user_notification.browser_notified = True
        user_notification.browser_notified_at = timezone.now()
        user_notification.save(update_fields=["browser_notified", "browser_notified_at"])

    return JsonResponse({"success": True})


@login_required
@require_POST
def mark_browser_notification_read(request, notification_id):
    """Marca apenas a notificacao clicada, sempre validando o seu proprietario."""
    user_notification = get_object_or_404(
        UserNotification,
        id=notification_id,
        user=request.user,
    )
    UserNotification.objects.filter(id=user_notification.id, read=False).update(read=True)
    return JsonResponse({"success": True})


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
