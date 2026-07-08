# Generated manually on 2026-07-08

import unicodedata

from django.db import migrations, models
from django.utils import timezone


PAUSED_RESOLUTION_STATUS_NAMES = {
    "acao do cliente",
    "aguardando cliente",
    "aguardando fornecedor",
    "aguardando solicitante",
    "proposta de solucao",
}


def normalize_status_name(name):
    normalized = unicodedata.normalize("NFKD", name or "")
    return normalized.encode("ascii", "ignore").decode("ascii").strip().lower()


def initialize_current_resolution_pauses(apps, schema_editor):
    Ticket = apps.get_model("ticket", "Ticket")
    TicketStatus = apps.get_model("ticket", "Ticket_Status")

    paused_status_ids = [
        status.id
        for status in TicketStatus.objects.all()
        if normalize_status_name(status.name) in PAUSED_RESOLUTION_STATUS_NAMES
    ]

    if not paused_status_ids:
        return

    Ticket.objects.filter(
        status_id__in=paused_status_ids,
        resolution_paused_at__isnull=True,
        closed_at__isnull=True,
        cancelled_at__isnull=True,
    ).update(resolution_paused_at=timezone.now())


class Migration(migrations.Migration):

    dependencies = [
        ("ticket", "0006_ticket_assigned_at_ticket_cancelled_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="ticket",
            name="resolution_paused_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="ticket",
            name="resolution_paused_seconds",
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.RunPython(
            initialize_current_resolution_pauses,
            migrations.RunPython.noop,
        ),
    ]
