from django.conf import settings
from django.db import models

from ticket.models import Ticket


class ApprovalRequest(models.Model):

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pendente"),
        (STATUS_APPROVED, "Aprovada"),
        (STATUS_REJECTED, "Rejeitada"),
        (STATUS_CANCELLED, "Cancelada"),
    ]

    ticket = models.ForeignKey(
        Ticket,
        related_name="approval_requests",
        on_delete=models.CASCADE
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="approval_requests_created",
        on_delete=models.PROTECT
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="approval_requests_to_review",
        on_delete=models.PROTECT
    )
    reason = models.TextField(max_length=800)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    response_comment = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ticket.hash} - {self.get_status_display()}"
