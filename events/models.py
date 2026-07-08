from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Event(models.Model):
    class Status(models.TextChoices):
        PENDING = "pendente", "Pendente"
        PLANNED = "planejado", "Planejado"
        PREPARING = "em_preparacao", "Em preparacao"
        IN_PROGRESS = "em_andamento", "Em andamento"
        COMPLETED = "concluido", "Concluido"
        CANCELLED = "cancelado", "Cancelado"

    class Priority(models.TextChoices):
        LOW = "baixa", "Baixa"
        MEDIUM = "media", "Media"
        HIGH = "alta", "Alta"
        CRITICAL = "critica", "Critica"

    title = models.CharField("titulo", max_length=180)
    description = models.TextField("descricao", blank=True)
    event_date = models.DateField("data do evento", db_index=True)
    start_time = models.TimeField("horario de inicio")
    end_time = models.TimeField("horario de termino")
    location = models.CharField("local", max_length=180)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="requested_events",
        verbose_name="solicitante",
        on_delete=models.PROTECT,
    )
    responsible_technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="responsible_events",
        verbose_name="tecnico responsavel",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    status = models.CharField(
        "status",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    priority = models.CharField(
        "prioridade",
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True,
    )
    estimated_people = models.PositiveIntegerField(
        "quantidade estimada de pessoas",
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )
    required_resources = models.TextField("recursos necessarios", blank=True)
    needs_onsite_support = models.BooleanField("precisa de suporte presencial", default=False)
    needs_live_stream = models.BooleanField("precisa de transmissao ao vivo", default=False)
    technical_notes = models.TextField("observacoes tecnicas", blank=True)
    related_ticket = models.ForeignKey(
        "ticket.Ticket",
        related_name="events",
        verbose_name="chamado vinculado",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="created_events",
        verbose_name="criado por",
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)
    cancelled_at = models.DateTimeField("cancelado em", null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField("concluido em", null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["event_date", "start_time", "title"]
        permissions = [
            ("manage_events", "Pode gerenciar eventos"),
        ]
        verbose_name = "evento"
        verbose_name_plural = "eventos"

    def __str__(self):
        return f"{self.title} - {self.event_date:%d/%m/%Y}"

    @property
    def status_slug(self):
        return self.status

    @property
    def status_color_class(self):
        return f"event-status-{self.status_slug}"

    @property
    def priority_slug(self):
        return self.priority

    def clean(self):
        errors = {}

        if self.end_time and self.start_time and self.end_time <= self.start_time:
            errors["end_time"] = "O horario de termino deve ser maior que o horario de inicio."

        if self.estimated_people is not None and self.estimated_people <= 0:
            errors["estimated_people"] = "A quantidade estimada de pessoas deve ser positiva."

        if self.location is not None and not self.location.strip():
            errors["location"] = "Informe o local do evento."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        previous_status = None

        if self.pk:
            previous_status = (
                type(self).objects
                .filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )

        lifecycle_fields = set()
        now = timezone.now()

        if self.status == self.Status.CANCELLED and previous_status != self.Status.CANCELLED:
            if self.cancelled_at is None:
                self.cancelled_at = now
                lifecycle_fields.add("cancelled_at")

        if self.status == self.Status.COMPLETED and previous_status != self.Status.COMPLETED:
            if self.completed_at is None:
                self.completed_at = now
                lifecycle_fields.add("completed_at")

        update_fields = kwargs.get("update_fields")

        if update_fields is not None and lifecycle_fields:
            kwargs["update_fields"] = set(update_fields) | lifecycle_fields

        self.full_clean()
        super().save(*args, **kwargs)
