from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from accounts.models import Profile

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Perfil'


class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)


# Remove o admin padrão do User
admin.site.unregister(User)

# Registra novamente com o Profile embutido
admin.site.register(User, CustomUserAdmin)

