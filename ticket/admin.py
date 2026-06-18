from django.contrib import admin
from ticket.models import (
    Ticket,
    TicketAttachment,
    TicketInteractionAttachment,
    TicketReport,
    Ticket_Status,
)


# Register your models here.

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):

    list_display = [
        "hash",
        "title",
        "status",
        "priority",
        "created_by",
        "assigned_to",
        "created_at",
        "updated_at",
        ]

    search_fields = [
        "hash",
        "title",
        "status",
        "priority",
        "created_by",
        "created_at",
    ]


@admin.register(Ticket_Status)
class TicketStatusAdmin(admin.ModelAdmin):
    
    list_display = [
        "id",
        "name",
    ]

    search_fields = [
        "name",
    ]


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):

    list_display = [
        "ticket",
        "original_name",
        "content_type",
        "size",
        "created_at",
    ]

    search_fields = [
        "ticket__hash",
        "original_name",
    ]


@admin.register(TicketInteractionAttachment)
class TicketInteractionAttachmentAdmin(admin.ModelAdmin):

    list_display = [
        "interaction",
        "original_name",
        "content_type",
        "size",
        "created_at",
    ]

    search_fields = [
        "interaction__ticket__hash",
        "original_name",
    ]


@admin.register(TicketReport)
class TicketReportAdmin(admin.ModelAdmin):

    list_display = [
        "ticket",
        "technician",
        "created_at",
    ]

    search_fields = [
        "ticket__hash",
        "technician__username",
        "summary",
    ]
