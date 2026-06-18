from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from system.models import MaintenanceWindow, SystemSettings
from system.security import generate_totp_secret, generate_totp_token


class MaintenanceCenterTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        self.client = Client(HTTP_HOST="localhost")
        self.client.force_login(self.admin)

    def test_superuser_can_activate_and_finish_maintenance(self):
        page_response = self.client.get(reverse("maintenance_center"))

        self.assertEqual(page_response.status_code, 200)

        blocked_response = self.client.post(
            reverse("maintenance_center"),
            {
                "action": "activate_maintenance",
                "title": "Manutencao de teste",
                "reason": "Validacao automatizada da central.",
                "duration_minutes": "60",
                "block_login": "on",
                "show_maintenance_page": "on",
                "reauth_password": "password",
                "authenticator_code": "000000",
            },
        )

        self.assertEqual(blocked_response.status_code, 302)
        self.assertFalse(SystemSettings.objects.filter(status="maintenance").exists())

        profile = self.admin.profile
        profile.authenticator_secret = generate_totp_secret()
        profile.save(update_fields=["authenticator_secret"])

        setup_response = self.client.post(
            reverse("maintenance_center"),
            {
                "action": "setup_authenticator",
                "setup_authenticator_code": generate_totp_token(profile.authenticator_secret),
            },
        )

        self.assertEqual(setup_response.status_code, 302)
        profile.refresh_from_db()
        self.assertTrue(profile.authenticator_enabled)

        activate_response = self.client.post(
            reverse("maintenance_center"),
            {
                "action": "activate_maintenance",
                "title": "Manutencao de teste",
                "reason": "Validacao automatizada da central.",
                "duration_minutes": "60",
                "block_login": "on",
                "show_maintenance_page": "on",
                "reauth_password": "password",
                "authenticator_code": generate_totp_token(profile.authenticator_secret),
            },
        )

        self.assertEqual(activate_response.status_code, 302)
        settings = SystemSettings.objects.get()
        self.assertEqual(settings.status, "maintenance")
        self.assertTrue(
            MaintenanceWindow.objects.filter(
                title="Manutencao de teste",
                status="active",
            ).exists()
        )

        finish_response = self.client.post(
            reverse("maintenance_center"),
            {
                "action": "finish_maintenance",
            },
        )

        self.assertEqual(finish_response.status_code, 302)
        settings.refresh_from_db()
        self.assertEqual(settings.status, "online")
        self.assertIsNone(settings.active_maintenance)
