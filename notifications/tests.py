from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from notifications.models import Notification, NotificationType, UserNotification
from notifications.views import SendNotification


User = get_user_model()


class BrowserNotificationAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="requester", password="test-pass")
        self.other_user = User.objects.create_user(username="other", password="test-pass")
        self.notification_type = NotificationType.objects.create(
            name="Sucesso",
            icon="fas fa-check-circle",
            color="success",
        )

    def create_user_notification(self, user=None, **notification_fields):
        browser_notified = notification_fields.pop("browser_notified", False)
        defaults = {
            "title": "Chamado respondido",
            "description": "Seu chamado foi respondido.",
            "type": self.notification_type,
            "url": "/tickets/123/",
        }
        defaults.update(notification_fields)
        notification = Notification.objects.create(**defaults)
        return UserNotification.objects.create(
            notification=notification,
            user=user or self.user,
            browser_notified=browser_notified,
        )

    def test_pending_endpoint_requires_authentication(self):
        response = self.client.get(reverse("pending_browser_notifications"))

        self.assertEqual(response.status_code, 302)

    def test_pending_endpoint_returns_only_current_users_unnotified_items(self):
        pending = self.create_user_notification()
        self.create_user_notification(user=self.other_user)
        self.create_user_notification(browser_notified=True)
        hidden = self.create_user_notification()
        hidden.hidden = True
        hidden.save(update_fields=["hidden"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("pending_browser_notifications"))

        self.assertEqual(response.status_code, 200)
        items = response.json()["notifications"]
        self.assertEqual([item["id"] for item in items], [pending.id])
        self.assertEqual(items[0]["url"], "/tickets/123/")

    def test_pending_endpoint_limits_the_batch(self):
        for index in range(12):
            self.create_user_notification(title=f"Notificacao {index}")
        self.client.force_login(self.user)

        response = self.client.get(reverse("pending_browser_notifications"))

        self.assertEqual(len(response.json()["notifications"]), 10)

    def test_displayed_endpoint_updates_only_the_current_users_item(self):
        own_item = self.create_user_notification()
        other_item = self.create_user_notification(user=self.other_user)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "mark_browser_notification_displayed",
                kwargs={"notification_id": own_item.id},
            )
        )
        forbidden_response = self.client.post(
            reverse(
                "mark_browser_notification_displayed",
                kwargs={"notification_id": other_item.id},
            )
        )

        own_item.refresh_from_db()
        other_item.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(own_item.browser_notified)
        self.assertIsNotNone(own_item.browser_notified_at)
        self.assertEqual(forbidden_response.status_code, 404)
        self.assertFalse(other_item.browser_notified)

    def test_read_endpoint_marks_the_clicked_item_as_read(self):
        item = self.create_user_notification()
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "mark_browser_notification_read",
                kwargs={"notification_id": item.id},
            )
        )

        item.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(item.read)

    def test_external_notification_url_falls_back_to_home(self):
        self.create_user_notification(url="https://example.com/phishing")
        self.client.force_login(self.user)

        response = self.client.get(reverse("pending_browser_notifications"))

        self.assertEqual(response.json()["notifications"][0]["url"], reverse("home"))

    def test_send_notification_builds_ticket_url(self):
        notification = SendNotification.send(
            title="Seu chamado foi respondido",
            descript="Ha uma nova resposta no chamado.",
            notification_type=self.notification_type,
            send_to=self.user,
            ticket_id=123,
        )

        self.assertEqual(notification.url, reverse("ticket_detail", kwargs={"ticket_id": 123}))
        self.assertTrue(
            UserNotification.objects.filter(
                notification=notification,
                user=self.user,
                browser_notified=False,
            ).exists()
        )

# Create your tests here.
