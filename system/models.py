from django.db import models
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class MaintenanceWindow(models.Model):

    STATUS_CHOICES = [
        ("scheduled", "Agendada"),
        ("active", "Em andamento"),
        ("finished", "Finalizada"),
        ("cancelled", "Cancelada"),
    ]

    title = models.CharField(
        max_length=150,
        verbose_name="Título"
    )

    reason = models.TextField(
        verbose_name="Motivo"
    )

    start_date = models.DateTimeField(
        verbose_name="Início"
    )

    end_date = models.DateTimeField(
        verbose_name="Previsão de término"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="scheduled"
    )

    disconnect_users = models.BooleanField(
        default=False,
        verbose_name="Deslogar usuários conectados"
    )

    block_login = models.BooleanField(
        default=True,
        verbose_name="Bloquear novos logins"
    )

    show_maintenance_page = models.BooleanField(
        default=True,
        verbose_name="Exibir página de manutenção"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
    

class SystemSettings(models.Model):

    STATUS_CHOICES = [
        ("online", "Operando"),
        ("maintenance", "Manutenção"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="online"
    )

    active_maintenance = models.ForeignKey(
        MaintenanceWindow,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return "Configurações do Sistema"
    
    
class MaintenanceLog(models.Model):

    ACTIONS = [
        ("created", "Criada"),
        ("started", "Iniciada"),
        ("finished", "Finalizada"),
        ("cancelled", "Cancelada"),
    ]

    maintenance = models.ForeignKey(
        MaintenanceWindow,
        on_delete=models.CASCADE,
        related_name="logs"
    )

    action = models.CharField(
        max_length=20,
        choices=ACTIONS
    )

    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    description = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]