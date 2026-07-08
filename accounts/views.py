from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.views.generic import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from ldap3 import Server, Connection, NONE, SUBTREE
from ldap3.utils.conv import escape_filter_chars
from django.contrib import messages
from notifications.views import SendNotification
from accounts.models import UserPreferences


class AccountsView(View):
    
    def get(self, request):
        try:
            
            return render(request, "account.html")
        
        except Exception as e:
            print(e)
            messages.error(request, "Erro ao efetuar login")
            return redirect("account")
        
        
    def post(self, request):
        try: 
            username = (request.POST.get("username") or "").strip()
            password = request.POST.get("password") or ""

            if not username or not password:
                messages.warning(request, "Informe usuario e senha.")
                return redirect("account")

            ad_user = self.authenticate_ad(username, password)

            if ad_user:
                user, created = User.objects.get_or_create(username=username)
                user.first_name = ad_user["first_name"]
                user.last_name = ad_user["last_name"]
                user.email = ad_user["email"]
                user.save()

                login(request, user)
                messages.success(request, "Usuário logado com sucesso!")
                return redirect("home")
            else:
                messages.warning(request, "Usuario ou senha invalidos")
                return redirect("account")
        except Exception as e:
            print(e)
            messages.error(request, "Erro ao efetuar login")
            return redirect("account")    


    def authenticate_ad(self, username, password):
        server = Server(
            "ldap://cafelandia.pr.gov.br",
            get_info=NONE,
            connect_timeout=3
        )

        user = f"{username}@cafelandia.pr.gov.br"

        try:
            conn = Connection(
                server,
                user=user,
                password=password,
                receive_timeout=5
            )

            if conn.bind():
                try:
                    return self.get_ad_user_data(conn, username)
                finally:
                    conn.unbind()
            else:
                return False
        except Exception as e:
            print(e)
            return False


    def get_ad_user_data(self, conn, username):
        search_base = "dc=cafelandia,dc=pr,dc=gov,dc=br"
        safe_username = escape_filter_chars(username)
        search_filter = f"(|(sAMAccountName={safe_username})(userPrincipalName={safe_username}@cafelandia.pr.gov.br))"

        conn.search(
            search_base=search_base,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=["displayName", "givenName", "sn", "mail"],
        )

        if not conn.entries:
            return {
                "first_name": username,
                "last_name": "",
                "email": "",
            }

        entry = conn.entries[0]
        display_name = self.get_ad_attr(entry, "displayName")
        first_name = self.get_ad_attr(entry, "givenName")
        last_name = self.get_ad_attr(entry, "sn")
        email = self.get_ad_attr(entry, "mail")

        if display_name and not first_name:
            name_parts = display_name.split(" ", 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

        return {
            "first_name": first_name or display_name or username,
            "last_name": last_name or "",
            "email": email or "",
        }


    def get_ad_attr(self, entry, attr_name):
        value = getattr(entry, attr_name, None)
        return str(value) if value else ""
        

def logout_view(request):
    messages.success(request, """Logout efetuado com sucesso!
                     Até logo 👋""")
    logout(request)
    return redirect("account")


@method_decorator(login_required(login_url="/"), name="dispatch")
class SettingsView(View):

    def get(self, request):
        
        preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
        
        return render(
            request,
            "settings.html",
            {
                "active_page": "config",
                "preferences": preferences,
            }
        )


    def post(self, request):
        action = request.POST.get("action")

        if action == "update_profile":
            return self.update_profile(request)

        if action == "send_global_notification":
            return self.send_global_notification(request)

        if action == "update_dashboard":
            return self.update_dashboard(request)

        messages.warning(request, "Acao invalida.")
        return redirect("settings")


    def update_profile(self, request):
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        email = (request.POST.get("email") or "").strip()
        telefone = (request.POST.get("telefone") or "").strip()
        cargo = (request.POST.get("cargo") or "").strip()
        departamento = (request.POST.get("departamento") or "").strip()
        refresh_seconds = request.POST.get("ticket_auto_refresh_seconds")

        if not first_name:
            messages.warning(request, "Informe seu nome.")
            return redirect("settings")

        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.email = email
        request.user.save(update_fields=["first_name", "last_name", "email"])

        profile = request.user.profile
        profile.telefone = telefone
        profile.departamento = departamento
        profile.cargo = cargo

        update_fields = ["telefone", "departamento", "cargo"]

        if profile.is_support:
            try:
                refresh_seconds = int(refresh_seconds)
            except (TypeError, ValueError):
                refresh_seconds = profile.ticket_auto_refresh_seconds

            profile.ticket_auto_refresh_seconds = min(max(refresh_seconds, 10), 300)
            update_fields.append("ticket_auto_refresh_seconds")

        profile.save(update_fields=update_fields)

        messages.success(request, "Perfil atualizado com sucesso!")
        return redirect("settings")


    def update_dashboard(self, request):
        
        user = request.user
        indicators = request.POST.get("indicators")
        indicators_events = request.POST.get("indicators_events")
        service_queue = request.POST.get("service_queue")
        
        preference, _ = UserPreferences.objects.get_or_create(user=user)
        
        if indicators == "on":
            preference.indicators = True
        else:
            preference.indicators = False
            
        if service_queue == "on":
            preference.service_queue = True
        else:
            preference.service_queue = False
        
        if indicators_events == "on":
            preference.indicators_events = True
        else: 
            preference.indicators_events = False
        
        preference.save()
        
        messages.success(request, "Dashboard atualizado com sucesso!")
        
        return redirect("settings")
        

    def send_global_notification(self, request):
        if not request.user.is_superuser:
            messages.warning(request, "Apenas superadmins podem enviar notificacoes globais.")
            return redirect("settings")

        title = (request.POST.get("title") or "").strip()
        description = (request.POST.get("description") or "").strip()

        if len(title) < 4 or len(description) < 10:
            messages.warning(request, "Informe um titulo e uma mensagem validos.")
            return redirect("settings")

        SendNotification.warning(
            request,
            title,
            description,
            True,
            None
        )

        messages.success(request, "Notificacao enviada para todos os usuarios.")
        return redirect("settings")
