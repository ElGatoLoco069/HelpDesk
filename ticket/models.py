from django.db import models
from registers.models import Subcategory, Priority
from django.contrib.auth.models import User

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
    description = models.TextField(max_length=255)

    status = models.ForeignKey(Ticket_Status, on_delete=models.PROTECT)

    priority = models.ForeignKey(Priority, on_delete=models.PROTECT)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    assigned_to = models.ForeignKey(User, related_name="assigned_tickets", null=True, blank=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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

