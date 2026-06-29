from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class NotificationType(models.Model):

    COLORS = [
        ("primary", "Primary"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("danger", "Danger"),
    ]

    name = models.CharField(max_length=150)
    icon = models.CharField(max_length=150)

    color = models.CharField(
        max_length=20,
        choices=COLORS,
        default="primary"
    )

    status = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Notification(models.Model):

    ACTION_KINDS = [
        ("", "Nenhuma"),
        ("solution_validation", "Validacao de solucao"),
        ("service_evaluation", "Avaliacao de atendimento"),
        ("approval_request", "Solicitacao de autorizacao"),
    ]

    title = models.CharField(max_length=150)
    description = models.TextField()

    type = models.ForeignKey(
        NotificationType,
        on_delete=models.PROTECT
    )

    send_all = models.BooleanField(default=False)
    action_kind = models.CharField(max_length=40, choices=ACTION_KINDS, blank=True, default="")
    ticket_id = models.PositiveIntegerField(null=True, blank=True)
    url = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="URL interna aberta ao clicar na notificacao.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_target_url(self):
        """Retorna um destino interno util mesmo para notificacoes antigas."""
        if self.url:
            return self.url

        if self.ticket_id:
            return reverse("ticket_detail", kwargs={"ticket_id": self.ticket_id})

        return reverse("home")


class UserNotification(models.Model):

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    read = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    browser_notified = models.BooleanField(default=False, db_index=True)
    browser_notified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("notification", "user")

    def __str__(self):
        return f"{self.user} - {self.notification}"
