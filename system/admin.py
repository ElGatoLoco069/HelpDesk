# admin.py

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    MaintenanceWindow,
    SystemSettings,
    MaintenanceLog
)


@admin.register(MaintenanceWindow)
class MaintenanceWindowAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "status_badge",
        "start_date",
        "end_date",
        "disconnect_users",
        "block_login",
        "show_maintenance_page",
        "created_by",
    )

    list_filter = (
        "status",
        "disconnect_users",
        "block_login",
        "show_maintenance_page",
    )

    search_fields = (
        "title",
        "reason",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    date_hierarchy = "start_date"

    actions = [
        "start_maintenance",
        "finish_maintenance",
        "cancel_maintenance",
    ]

    fieldsets = (
        (
            "Informações Gerais",
            {
                "fields": (
                    "title",
                    "reason",
                    "status",
                )
            }
        ),
        (
            "Agendamento",
            {
                "fields": (
                    "start_date",
                    "end_date",
                )
            }
        ),
        (
            "Comportamento do Sistema",
            {
                "fields": (
                    "disconnect_users",
                    "block_login",
                    "show_maintenance_page",
                )
            }
        ),
        (
            "Auditoria",
            {
                "fields": (
                    "created_by",
                    "created_at",
                    "updated_at",
                )
            }
        ),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)

    @admin.display(description="Status")
    def status_badge(self, obj):

        colors = {
            "scheduled": "#f39c12",
            "active": "#e74c3c",
            "finished": "#27ae60",
            "cancelled": "#7f8c8d",
        }

        labels = {
            "scheduled": "Agendada",
            "active": "Ativa",
            "finished": "Finalizada",
            "cancelled": "Cancelada",
        }

        return format_html(
            '<strong style="color:{};">● {}</strong>',
            colors.get(obj.status),
            labels.get(obj.status),
        )

    def start_maintenance(self, request, queryset):

        settings = SystemSettings.objects.first()

        for maintenance in queryset:

            maintenance.status = "active"
            maintenance.save()

            MaintenanceLog.objects.create(
                maintenance=maintenance,
                action="started",
                performed_by=request.user,
                description="Manutenção iniciada pelo admin."
            )

            if settings:
                settings.status = "maintenance"
                settings.active_maintenance = maintenance
                settings.save()

        self.message_user(
            request,
            f"{queryset.count()} manutenção(ões) iniciada(s)."
        )

    start_maintenance.short_description = "▶ Iniciar manutenção"

    def finish_maintenance(self, request, queryset):

        settings = SystemSettings.objects.first()

        for maintenance in queryset:

            maintenance.status = "finished"
            maintenance.save()

            MaintenanceLog.objects.create(
                maintenance=maintenance,
                action="finished",
                performed_by=request.user,
                description="Manutenção finalizada pelo admin."
            )

        if settings:
            settings.status = "online"
            settings.active_maintenance = None
            settings.save()

        self.message_user(
            request,
            f"{queryset.count()} manutenção(ões) finalizada(s)."
        )

    finish_maintenance.short_description = "✅ Finalizar manutenção"

    def cancel_maintenance(self, request, queryset):

        for maintenance in queryset:

            maintenance.status = "cancelled"
            maintenance.save()

            MaintenanceLog.objects.create(
                maintenance=maintenance,
                action="cancelled",
                performed_by=request.user,
                description="Manutenção cancelada pelo admin."
            )

        self.message_user(
            request,
            f"{queryset.count()} manutenção(ões) cancelada(s)."
        )

    cancel_maintenance.short_description = "❌ Cancelar manutenção"
    
    
@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):

    list_display = (
        "status",
        "active_maintenance",
        "updated_at",
    )

    readonly_fields = (
        "updated_at",
    )

    def has_add_permission(self, request):
        return not SystemSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
    
    
@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):

    list_display = (
        "maintenance",
        "action",
        "performed_by",
        "created_at",
    )

    list_filter = (
        "action",
        "created_at",
    )

    search_fields = (
        "maintenance__title",
        "description",
    )

    readonly_fields = (
        "maintenance",
        "action",
        "performed_by",
        "description",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False