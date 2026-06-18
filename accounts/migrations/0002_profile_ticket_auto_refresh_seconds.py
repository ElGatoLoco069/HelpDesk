# Generated manually on 2026-05-21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="ticket_auto_refresh_seconds",
            field=models.PositiveSmallIntegerField(default=30),
        ),
    ]
