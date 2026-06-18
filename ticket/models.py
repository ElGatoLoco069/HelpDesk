from django.db import models
from registers.models import Subcategory, Priority
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator

# Create your models here.

class Ticket_Status(models.Model):

    name = models.CharField(max_length=150)
    color = models.CharField(max_length=150, default="progress")
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Ticket(models.Model):

    hash = models.CharField(max_length=150, unique=True)
    title = models.ForeignKey(Subcategory, on_delete=models.PROTECT)
    description = models.TextField(max_length=550)

    status = models.ForeignKey(Ticket_Status, on_delete=models.PROTECT)

    priority = models.ForeignKey(Priority, on_delete=models.PROTECT)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    assigned_to = models.ForeignKey(User, related_name="assigned_tickets", null=True, blank=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    solution_proposed_at = models.DateTimeField(null=True, blank=True)
    solution_responded_at = models.DateTimeField(null=True, blank=True)
    requester_solution_accepted = models.BooleanField(null=True, blank=True)
    evaluation_requested_at = models.DateTimeField(null=True, blank=True)
    satisfaction_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    satisfaction_comment = models.TextField(blank=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.hash


class TicketAttachment(models.Model):

    ticket = models.ForeignKey(Ticket, related_name="attachments", on_delete=models.CASCADE)
    file = models.FileField(upload_to="ticket_attachments/%Y/%m/")
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.original_name


class TicketReport(models.Model):

    ticket = models.ForeignKey(Ticket, related_name="reports", on_delete=models.CASCADE)
    technician = models.ForeignKey(User, related_name="ticket_reports", on_delete=models.PROTECT)
    summary = models.TextField(max_length=500)
    actions = models.TextField()
    materials = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ticket.hash} - {self.technician}"

    @property
    def action_items(self):
        return [item.strip() for item in self.actions.splitlines() if item.strip()]

    @property
    def material_items(self):
        return [item.strip() for item in self.materials.splitlines() if item.strip()]


class TicketInteraction(models.Model):
    ticket = models.ForeignKey(Ticket, related_name="interactions", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    message = models.TextField()

    interaction_type = models.CharField(
        max_length=20,
        choices=[
            ("requester", "Solicitante"),
            ("technician", "Tecnico"),
            ("system", "Sistema"),
        ]
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.ticket.hash} - {self.user}"


class TicketInteractionAttachment(models.Model):

    interaction = models.ForeignKey(
        TicketInteraction,
        related_name="attachments",
        on_delete=models.CASCADE
    )
    file = models.FileField(upload_to="ticket_interactions/%Y/%m/")
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.original_name
