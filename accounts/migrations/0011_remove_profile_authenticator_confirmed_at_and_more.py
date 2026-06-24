from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_profile_authenticator_confirmed_at_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="profile",
            name="authenticator_confirmed_at",
        ),
        migrations.RemoveField(
            model_name="profile",
            name="authenticator_enabled",
        ),
        migrations.RemoveField(
            model_name="profile",
            name="authenticator_secret",
        ),
    ]
