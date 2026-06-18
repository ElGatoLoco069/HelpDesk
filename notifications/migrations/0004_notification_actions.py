# Generated manually on 2026-05-21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0003_rename_hidden_notification_send_all_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="action_kind",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Nenhuma"),
                    ("solution_validation", "Validacao de solucao"),
                    ("service_evaluation", "Avaliacao de atendimento"),
                ],
                default="",
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="ticket_id",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
