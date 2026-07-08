from django.db import models
from registers.models import Subcategory, Priority
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone

from datetime import timedelta
import unicodedata

# Create your models here.


DONE_STATUS_NAMES = {
    "concluido",
    "concluida",
    "resolvido",
    "resolvida",
    "fechado",
    "fechada",
    "finalizado",
    "finalizada",
}
CANCELLED_STATUS_NAMES = {"cancelado", "cancelada"}
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


def is_resolution_paused_status(name):
    return normalize_status_name(name) in PAUSED_RESOLUTION_STATUS_NAMES


class Ticket_Status(models.Model):

    name = models.CharField(max_length=150)
    color = models.CharField(max_length=150, default="progress")
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Ticket(models.Model):

    hash = models.CharField(max_length=150, unique=True)
    title = models.ForeignKey(Subcategory, on_delete=models.PROTECT)
    description = models.TextField(max_length=550)

    status = models.ForeignKey(Ticket_Status, on_delete=models.PROTECT)

    priority = models.ForeignKey(Priority, on_delete=models.PROTECT)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    assigned_to = models.ForeignKey(User, related_name="assigned_tickets", null=True, blank=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    first_response_at = models.DateTimeField(null=True, blank=True, db_index=True)
    assigned_at = models.DateTimeField(null=True, blank=True, db_index=True)
    cancelled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    reopened_at = models.DateTimeField(null=True, blank=True, db_index=True)
    resolution_paused_at = models.DateTimeField(null=True, blank=True, db_index=True)
    resolution_paused_seconds = models.PositiveBigIntegerField(default=0)
    solution_proposed_at = models.DateTimeField(null=True, blank=True)
    solution_responded_at = models.DateTimeField(null=True, blank=True)
    requester_solution_accepted = models.BooleanField(null=True, blank=True)
    evaluation_requested_at = models.DateTimeField(null=True, blank=True)
    satisfaction_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    satisfaction_comment = models.TextField(blank=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.hash

    def _status_name_for_lifecycle(self):
        if not self.status_id:
            return ""

        cached_status = self._state.fields_cache.get("status")
        if cached_status and cached_status.pk == self.status_id:
            return cached_status.name

        return (
            Ticket_Status.objects
            .filter(pk=self.status_id)
            .values_list("name", flat=True)
            .first()
            or ""
        )

    def save(self, *args, **kwargs):
        """Mantem marcos do ciclo de vida sem depender de uma view especifica."""
        previous = None
        if self.pk:
            previous = (
                type(self).objects
                .filter(pk=self.pk)
                .values(
                    "assigned_to_id",
                    "status__name",
                    "resolution_paused_at",
                    "resolution_paused_seconds",
                )
                .first()
            )

        now = timezone.now()
        lifecycle_fields = set()

        was_assigned = previous and previous["assigned_to_id"] is not None
        if self.assigned_to_id and not was_assigned and self.assigned_at is None:
            self.assigned_at = now
            lifecycle_fields.add("assigned_at")

        current_status = normalize_status_name(self._status_name_for_lifecycle())
        previous_status = normalize_status_name(previous["status__name"]) if previous else ""
        is_done = current_status in DONE_STATUS_NAMES
        was_done = previous_status in DONE_STATUS_NAMES
        is_cancelled = current_status in CANCELLED_STATUS_NAMES
        was_cancelled = previous_status in CANCELLED_STATUS_NAMES
        is_paused = current_status in PAUSED_RESOLUTION_STATUS_NAMES
        was_paused = previous_status in PAUSED_RESOLUTION_STATUS_NAMES
        had_open_pause = bool(previous and previous["resolution_paused_at"])

        if is_done and not was_done and self.closed_at is None:
            self.closed_at = now
            lifecycle_fields.add("closed_at")

        if is_cancelled and not was_cancelled and self.cancelled_at is None:
            self.cancelled_at = now
            lifecycle_fields.add("cancelled_at")

        if (
            previous
            and (was_done or was_cancelled)
            and not (is_done or is_cancelled)
            and self.reopened_at is None
        ):
            self.reopened_at = now
            lifecycle_fields.add("reopened_at")

        if is_paused and not was_paused and self.resolution_paused_at is None:
            self.resolution_paused_at = now
            lifecycle_fields.add("resolution_paused_at")

        if previous and (was_paused or had_open_pause) and not is_paused:
            pause_started_at = previous["resolution_paused_at"] or self.resolution_paused_at

            if pause_started_at:
                paused_seconds = max(
                    0,
                    int((now - pause_started_at).total_seconds()),
                )
                self.resolution_paused_seconds = (
                    self.resolution_paused_seconds
                    or previous["resolution_paused_seconds"]
                    or 0
                ) + paused_seconds
                lifecycle_fields.add("resolution_paused_seconds")

            self.resolution_paused_at = None
            lifecycle_fields.add("resolution_paused_at")

        update_fields = kwargs.get("update_fields")
        if update_fields is not None and lifecycle_fields:
            kwargs["update_fields"] = set(update_fields) | lifecycle_fields

        super().save(*args, **kwargs)

    @property
    def resolution_paused_duration(self):
        seconds = self.resolution_paused_seconds or 0

        if self.resolution_paused_at:
            pause_end_at = self.closed_at or self.cancelled_at or timezone.now()
            seconds += max(
                0,
                int((pause_end_at - self.resolution_paused_at).total_seconds()),
            )

        return timedelta(seconds=seconds)

    @property
    def active_resolution_duration(self):
        end_at = self.closed_at or self.cancelled_at or timezone.now()
        elapsed_seconds = max(0, int((end_at - self.created_at).total_seconds()))
        active_seconds = max(
            0,
            elapsed_seconds - int(self.resolution_paused_duration.total_seconds()),
        )

        return timedelta(seconds=active_seconds)

    @property
    def resolution_is_paused(self):
        return bool(self.resolution_paused_at)

    @property
    def resolution_paused_hours(self):
        return round(self.resolution_paused_duration.total_seconds() / 3600, 2)

    @property
    def active_resolution_hours(self):
        return round(self.active_resolution_duration.total_seconds() / 3600, 2)

    @property
    def resolution_hours(self):
        if not self.closed_at:
            return None

        return self.active_resolution_hours


class TicketAttachment(models.Model):

    ticket = models.ForeignKey(Ticket, related_name="attachments", on_delete=models.CASCADE)
    file = models.FileField(upload_to="ticket_attachments/%Y/%m/")
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.original_name


class TicketReport(models.Model):

    ticket = models.ForeignKey(Ticket, related_name="reports", on_delete=models.CASCADE)
    technician = models.ForeignKey(User, related_name="ticket_reports", on_delete=models.PROTECT)
    summary = models.TextField(max_length=500)
    actions = models.TextField()
    materials = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ticket.hash} - {self.technician}"

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)
        if creating:
            Ticket.objects.filter(
                pk=self.ticket_id,
                first_response_at__isnull=True,
            ).update(first_response_at=self.created_at)

    @property
    def action_items(self):
        return [item.strip() for item in self.actions.splitlines() if item.strip()]

    @property
    def material_items(self):
        return [item.strip() for item in self.materials.splitlines() if item.strip()]


class TicketInteraction(models.Model):
    ticket = models.ForeignKey(Ticket, related_name="interactions", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    message = models.TextField()

    interaction_type = models.CharField(
        max_length=20,
        choices=[
            ("requester", "Solicitante"),
            ("technician", "Tecnico"),
            ("system", "Sistema"),
        ]
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.ticket.hash} - {self.user}"

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)
        if creating and self.interaction_type == "technician":
            Ticket.objects.filter(
                pk=self.ticket_id,
                first_response_at__isnull=True,
            ).update(first_response_at=self.created_at)


class TicketInteractionAttachment(models.Model):

    interaction = models.ForeignKey(
        TicketInteraction,
        related_name="attachments",
        on_delete=models.CASCADE
    )
    file = models.FileField(upload_to="ticket_interactions/%Y/%m/")
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.original_name
