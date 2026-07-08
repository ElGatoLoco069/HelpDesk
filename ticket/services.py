from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from notifications.models import Notification, NotificationType, UserNotification
from ticket.models import (
    DONE_STATUS_NAMES as MODEL_DONE_STATUS_NAMES,
    Ticket,
    Ticket_Status,
    normalize_status_name,
)


SOLUTION_STATUS_NAMES = {
    "proposta de solucao",
    "proposta de solução",
}

DONE_STATUS_NAMES = MODEL_DONE_STATUS_NAMES | {"concluído", "concluída"}

AUTO_CLOSE_SOLUTION_DAYS = 7
AUTO_CLOSE_SOLUTION_RATING = 5
AUTO_CLOSE_NOTIFICATION_TITLE = "Chamado concluido automaticamente"


def get_status_by_name(*names):
    normalized_names = {normalize_status_name(name) for name in names}

    for status in Ticket_Status.objects.filter(status=True):
        if normalize_status_name(status.name) in normalized_names:
            return status

    return None


def get_status_ids_by_name(*names):
    normalized_names = {normalize_status_name(name) for name in names}

    return [
        status.id
        for status in Ticket_Status.objects.filter(status=True)
        if normalize_status_name(status.name) in normalized_names
    ]


def get_solution_status():
    status = get_status_by_name(*SOLUTION_STATUS_NAMES)

    if status:
        return status

    return Ticket_Status.objects.create(
        name="Proposta de Solucao",
        color="warning",
        status=True,
    )


def get_done_status():
    status = get_status_by_name(*DONE_STATUS_NAMES)

    if status:
        return status

    return Ticket_Status.objects.create(
        name="Concluido",
        color="open",
        status=True,
    )


def _notification_type():
    notification_type, _ = NotificationType.objects.get_or_create(
        name="Sucesso",
        defaults={
            "icon": "fas fa-check-circle",
            "color": "success",
        },
    )

    return notification_type


def _notify_auto_closed_ticket(ticket, days, rating):
    recipients = []

    for user in [ticket.created_by, ticket.assigned_to]:
        if user and user.is_active and user.id not in {recipient.id for recipient in recipients}:
            recipients.append(user)

    if not recipients:
        return

    notification = Notification.objects.create(
        title=AUTO_CLOSE_NOTIFICATION_TITLE,
        description=(
            f"O chamado {ticket.hash} ficou mais de {days} dias em proposta de solucao "
            f"e foi concluido automaticamente com nota {rating}/5 "
            "para o tecnico responsavel."
        ),
        type=_notification_type(),
        send_all=False,
        action_kind="",
        ticket_id=ticket.id,
    )

    UserNotification.objects.bulk_create(
        [
            UserNotification(
                notification=notification,
                user=user,
                read=False,
                hidden=False,
            )
            for user in recipients
        ],
        ignore_conflicts=True,
    )


def auto_close_expired_solution_proposals(now=None, days=None, rating=None):
    """
    Conclui propostas de solucao pendentes ha mais de ``days`` dias.

    A nota fica gravada no proprio chamado em ``satisfaction_rating``, que e o
    campo usado pelo sistema para avaliar o atendimento do tecnico atribuido.
    """
    now = now or timezone.now()
    days = days if days is not None else getattr(
        settings,
        "TICKET_SOLUTION_AUTO_CLOSE_DAYS",
        AUTO_CLOSE_SOLUTION_DAYS,
    )
    rating = rating if rating is not None else getattr(
        settings,
        "TICKET_SOLUTION_AUTO_CLOSE_RATING",
        AUTO_CLOSE_SOLUTION_RATING,
    )
    deadline = now - timedelta(days=days)

    solution_status_ids = get_status_ids_by_name(*SOLUTION_STATUS_NAMES)

    if not solution_status_ids:
        solution_status_ids = [get_solution_status().id]

    done_status = get_done_status()

    expired_tickets = (
        Ticket.objects
        .select_related("created_by", "assigned_to", "status")
        .filter(
            status_id__in=solution_status_ids,
            requester_solution_accepted__isnull=True,
        )
        .filter(
            solution_proposed_at__lt=deadline,
        )
        .order_by("id")
    )

    closed_count = 0

    with transaction.atomic():
        for ticket in expired_tickets.select_for_update():
            ticket.status = done_status
            ticket.requester_solution_accepted = True
            ticket.solution_responded_at = now
            ticket.evaluation_requested_at = now
            ticket.satisfaction_rating = rating
            ticket.satisfaction_comment = (
                "Avaliacao automatica: proposta de solucao sem retorno do "
                f"solicitante por mais de {days} dias."
            )
            ticket.evaluated_at = now
            ticket.save(update_fields=[
                "status",
                "requester_solution_accepted",
                "solution_responded_at",
                "evaluation_requested_at",
                "satisfaction_rating",
                "satisfaction_comment",
                "evaluated_at",
                "updated_at",
            ])

            UserNotification.objects.filter(
                user=ticket.created_by,
                notification__ticket_id=ticket.id,
                notification__action_kind="solution_validation",
            ).update(read=True, hidden=True)

            _notify_auto_closed_ticket(ticket, days, rating)
            closed_count += 1

    return closed_count
