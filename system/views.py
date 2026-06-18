from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.generic import View
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from accounts.models import Profile
from system.security import (
    build_totp_uri,
    format_totp_secret,
    generate_totp_secret,
    verify_totp_token,
    verify_user_password,
)
from ticket.models import Ticket
from system.models import MaintenanceLog, MaintenanceWindow, SystemSettings


def is_under_maintenance(request):
    settings = SystemSettings.objects.first()

    if not settings or settings.status != "maintenance":
        return None

    maintenance = settings.active_maintenance

    if maintenance and not maintenance.block_login:
        return None

    if not maintenance or maintenance.show_maintenance_page:
        return render(request, "maintenance.html")

    return None


@method_decorator(login_required(login_url="/"), name="dispatch")
class SystemView(View):

    def get(self, request):
        if not request.user.is_superuser:
            messages.warning(request, "Apenas superadmins podem acessar a central do sistema.")
            return redirect("home")

        profile = request.user.profile

        if not profile.authenticator_secret:
            profile.authenticator_secret = generate_totp_secret()
            profile.save(update_fields=["authenticator_secret"])

        settings, _ = SystemSettings.objects.get_or_create()
        online_users = Profile.objects.filter(
            last_activity__gte=timezone.now() - timedelta(minutes=5)
        )

        total_online = online_users.count()
        total_tickets = Ticket.objects.count()
        active_tickets = Ticket.objects.exclude(
            Q(status__name__iexact="Concluido") |
            Q(status__name__iexact="Concluído")
        ).count()
        online_profiles = (
            online_users
            .select_related("user")
            .order_by("-last_activity")[:6]
        )
        maintenance_windows = MaintenanceWindow.objects.select_related("created_by").all()[:5]
        maintenance_logs = (
            MaintenanceLog.objects
            .select_related("maintenance", "performed_by")
            .all()[:6]
        )

        return render(
            request,
            "maintenance_center.html",
            {
                "active_page": "maintenance_center",
                "online_users": total_online,
                "total_tickets": total_tickets,
                "active_tickets": active_tickets,
                "online_profiles": online_profiles,
                "system_settings": settings,
                "active_maintenance": settings.active_maintenance,
                "maintenance_windows": maintenance_windows,
                "maintenance_logs": maintenance_logs,
                "authenticator_enabled": profile.authenticator_enabled,
                "authenticator_secret": format_totp_secret(profile.authenticator_secret),
                "authenticator_uri": build_totp_uri(request.user, profile.authenticator_secret),
            }
        )


    def post(self, request):
        if not request.user.is_superuser:
            messages.warning(request, "Apenas superadmins podem alterar o estado do sistema.")
            return redirect("home")

        action = request.POST.get("action")
        settings, _ = SystemSettings.objects.get_or_create()
        profile = request.user.profile

        if not profile.authenticator_secret:
            profile.authenticator_secret = generate_totp_secret()
            profile.save(update_fields=["authenticator_secret"])

        if action == "setup_authenticator":
            authenticator_code = request.POST.get("setup_authenticator_code")

            if not verify_totp_token(profile.authenticator_secret, authenticator_code):
                messages.warning(request, "Codigo do autenticador invalido. Confira o horario do aparelho e tente novamente.")
                return redirect("maintenance_center")

            profile.authenticator_enabled = True
            profile.authenticator_confirmed_at = timezone.now()
            profile.save(update_fields=[
                "authenticator_enabled",
                "authenticator_confirmed_at",
            ])

            messages.success(request, "Autenticador configurado com sucesso.")
            return redirect("maintenance_center")

        if action == "activate_maintenance":
            if not profile.authenticator_enabled:
                messages.warning(request, "Configure o autenticador antes de ativar o modo manutencao.")
                return redirect("maintenance_center")

            reauth_password = request.POST.get("reauth_password")
            authenticator_code = request.POST.get("authenticator_code")

            if not verify_user_password(request.user, reauth_password):
                messages.warning(request, "Senha invalida. Reautenticacao obrigatoria para ativar manutencao.")
                return redirect("maintenance_center")

            if not verify_totp_token(profile.authenticator_secret, authenticator_code):
                messages.warning(request, "Codigo do autenticador invalido ou expirado.")
                return redirect("maintenance_center")

            title = (request.POST.get("title") or "Manutencao emergencial").strip()
            reason = (request.POST.get("reason") or "Manutencao ativada pela central do sistema.").strip()
            duration_minutes = request.POST.get("duration_minutes") or "120"

            try:
                duration_minutes = int(duration_minutes)
            except (TypeError, ValueError):
                duration_minutes = 120

            duration_minutes = min(max(duration_minutes, 15), 480)
            disconnect_users = request.POST.get("disconnect_users") == "on"
            block_login = request.POST.get("block_login") == "on"
            show_maintenance_page = request.POST.get("show_maintenance_page") == "on"
            now = timezone.now()

            maintenance = MaintenanceWindow.objects.create(
                title=title,
                reason=reason,
                start_date=now,
                end_date=now + timedelta(minutes=duration_minutes),
                status="active",
                disconnect_users=disconnect_users,
                block_login=block_login,
                show_maintenance_page=show_maintenance_page,
                created_by=request.user,
            )

            settings.status = "maintenance"
            settings.active_maintenance = maintenance
            settings.save(update_fields=["status", "active_maintenance", "updated_at"])

            MaintenanceLog.objects.create(
                maintenance=maintenance,
                action="started",
                performed_by=request.user,
                description="Manutencao ativada apos reautenticacao e codigo de autenticador validos."
            )

            if disconnect_users:
                Session.objects.exclude(session_key=request.session.session_key).delete()

            messages.success(request, "Modo manutencao ativado.")
            return redirect("maintenance_center")

        if action == "finish_maintenance":
            maintenance = settings.active_maintenance

            if maintenance:
                maintenance.status = "finished"
                maintenance.save(update_fields=["status", "updated_at"])

                MaintenanceLog.objects.create(
                    maintenance=maintenance,
                    action="finished",
                    performed_by=request.user,
                    description="Manutencao finalizada pela central do sistema."
                )

            settings.status = "online"
            settings.active_maintenance = None
            settings.save(update_fields=["status", "active_maintenance", "updated_at"])

            messages.success(request, "Modo manutencao finalizado.")
            return redirect("maintenance_center")

        messages.warning(request, "Acao invalida.")
        return redirect("maintenance_center")
