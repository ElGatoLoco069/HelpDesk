from django.db import migrations, models


def mark_existing_as_notified(apps, schema_editor):
    """Evita exibir todo o historico como notificacao nativa apos o deploy."""
    UserNotification = apps.get_model("notifications", "UserNotification")
    UserNotification.objects.update(browser_notified=True)


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0005_alter_notification_action_kind"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="url",
            field=models.CharField(
                blank=True,
                default="",
                help_text="URL interna aberta ao clicar na notificacao.",
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name="usernotification",
            name="browser_notified",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="usernotification",
            name="browser_notified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(mark_existing_as_notified, migrations.RunPython.noop),
    ]
