from django.contrib import admin

from approval_flow.models import ApprovalRequest


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):

    list_display = [
        "ticket",
        "requested_by",
        "approver",
        "status",
        "created_at",
        "decided_at",
    ]

    list_filter = [
        "status",
        "created_at",
        "decided_at",
    ]

    search_fields = [
        "ticket__hash",
        "requested_by__username",
        "approver__username",
        "reason",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
        "decided_at",
    ]
