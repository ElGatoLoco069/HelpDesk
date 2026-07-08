# Generated manually for the Events module.

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ticket", "0006_ticket_assigned_at_ticket_cancelled_at_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Event",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=180, verbose_name="titulo")),
                ("description", models.TextField(blank=True, verbose_name="descricao")),
                ("event_date", models.DateField(db_index=True, verbose_name="data do evento")),
                ("start_time", models.TimeField(verbose_name="horario de inicio")),
                ("end_time", models.TimeField(verbose_name="horario de termino")),
                ("location", models.CharField(max_length=180, verbose_name="local")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pendente", "Pendente"),
                            ("planejado", "Planejado"),
                            ("em_preparacao", "Em preparacao"),
                            ("em_andamento", "Em andamento"),
                            ("concluido", "Concluido"),
                            ("cancelado", "Cancelado"),
                        ],
                        db_index=True,
                        default="pendente",
                        max_length=20,
                        verbose_name="status",
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[
                            ("baixa", "Baixa"),
                            ("media", "Media"),
                            ("alta", "Alta"),
                            ("critica", "Critica"),
                        ],
                        db_index=True,
                        default="media",
                        max_length=20,
                        verbose_name="prioridade",
                    ),
                ),
                (
                    "estimated_people",
                    models.PositiveIntegerField(
                        blank=True,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="quantidade estimada de pessoas",
                    ),
                ),
                ("required_resources", models.TextField(blank=True, verbose_name="recursos necessarios")),
                (
                    "needs_onsite_support",
                    models.BooleanField(default=False, verbose_name="precisa de suporte presencial"),
                ),
                (
                    "needs_live_stream",
                    models.BooleanField(default=False, verbose_name="precisa de transmissao ao vivo"),
                ),
                ("technical_notes", models.TextField(blank=True, verbose_name="observacoes tecnicas")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="criado em")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="atualizado em")),
                (
                    "cancelled_at",
                    models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="cancelado em"),
                ),
                (
                    "completed_at",
                    models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="concluido em"),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_events",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="criado por",
                    ),
                ),
                (
                    "related_ticket",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="events",
                        to="ticket.ticket",
                        verbose_name="chamado vinculado",
                    ),
                ),
                (
                    "requester",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="requested_events",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="solicitante",
                    ),
                ),
                (
                    "responsible_technician",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="responsible_events",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="tecnico responsavel",
                    ),
                ),
            ],
            options={
                "verbose_name": "evento",
                "verbose_name_plural": "eventos",
                "ordering": ["event_date", "start_time", "title"],
                "permissions": [("manage_events", "Pode gerenciar eventos")],
            },
        ),
    ]
