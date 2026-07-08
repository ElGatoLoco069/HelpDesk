from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "event_date",
        "start_time",
        "end_time",
        "location",
        "requester",
        "responsible_technician",
        "status",
        "priority",
    ]
    list_filter = [
        "status",
        "priority",
        "event_date",
        "needs_onsite_support",
        "needs_live_stream",
    ]
    search_fields = [
        "title",
        "description",
        "location",
        "requester__username",
        "requester__first_name",
        "requester__last_name",
        "responsible_technician__username",
        "related_ticket__hash",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "cancelled_at",
        "completed_at",
    ]
    fieldsets = (
        (
            "Dados do evento",
            {
                "fields": (
                    "title",
                    "description",
                    "event_date",
                    "start_time",
                    "end_time",
                    "location",
                )
            },
        ),
        (
            "Responsaveis",
            {
                "fields": (
                    "requester",
                    "responsible_technician",
                    "created_by",
                    "related_ticket",
                )
            },
        ),
        (
            "Planejamento",
            {
                "fields": (
                    "status",
                    "priority",
                    "estimated_people",
                    "required_resources",
                    "needs_onsite_support",
                    "needs_live_stream",
                    "technical_notes",
                )
            },
        ),
        (
            "Historico",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "cancelled_at",
                    "completed_at",
                )
            },
        ),
    )
