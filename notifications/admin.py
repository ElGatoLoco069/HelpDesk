from django.contrib import admin
from notifications.models import Notification, NotificationType, UserNotification


@admin.register(NotificationType)
class NotificationTypeAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "icon",
        "color",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "color",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "-created_at",
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "title",
        "type",
        "send_all",
        "created_at",
    )

    list_filter = (
        "send_all",
        "type",
    )

    search_fields = (
        "title",
        "description",
    )

    ordering = (
        "-created_at",
    )


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "notification",
        "user",
        "read",
        "hidden",
        "browser_notified",
        "browser_notified_at",
        "created_at",
    )

    list_filter = (
        "read",
        "hidden",
        "browser_notified",
    )

    search_fields = (
        "user__username",
        "notification__title",
    )

    autocomplete_fields = (
        "user",
        "notification",
    )

    ordering = (
        "-created_at",
    )
