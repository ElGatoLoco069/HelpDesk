# Generated manually on 2026-05-21

from django.db import migrations, models
import django.core.validators


def create_solution_status(apps, schema_editor):
    TicketStatus = apps.get_model("ticket", "Ticket_Status")

    TicketStatus.objects.get_or_create(
        name="Proposta de Solucao",
        defaults={
            "color": "warning",
            "status": True,
        }
    )


class Migration(migrations.Migration):

    dependencies = [
        ("ticket", "0002_ticketinteraction"),
    ]

    operations = [
        migrations.AddField(
            model_name="ticket",
            name="evaluated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="ticket",
            name="evaluation_requested_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="ticket",
            name="requester_solution_accepted",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="ticket",
            name="satisfaction_comment",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="ticket",
            name="satisfaction_rating",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5),
                ],
            ),
        ),
        migrations.AddField(
            model_name="ticket",
            name="solution_proposed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="ticket",
            name="solution_responded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(create_solution_status, migrations.RunPython.noop),
    ]
