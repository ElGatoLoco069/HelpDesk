from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from accounts.models import Profile, UserPreferences, System

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Perfil'


class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    
    list_display = [
        "user",
        "indicators",
        "service_queue",
    ]

    search_fields = [
        "user"
    ]


@admin.action(description="Colocar sistema em manutenção")
def enable_maintenance(modeladmin, request, queryset):
    queryset.update(under_maintenance=True)


@admin.action(description="Colocar sistema em operação")
def disable_maintenance(modeladmin, request, queryset):
    queryset.update(under_maintenance=False)


@admin.register(System)
class SystemAdmin(admin.ModelAdmin):

    list_display = (
        "status",
    )

    actions = (
        enable_maintenance,
        disable_maintenance,
    )

    def status(self, obj):
        return "🔴 Em manutenção" if obj.under_maintenance else "🟢 Operando"

    status.short_description = "Status"
  
    
# Remove o admin padrão do User
admin.site.unregister(User)

# Registra novamente com o Profile embutido
admin.site.register(User, CustomUserAdmin)

