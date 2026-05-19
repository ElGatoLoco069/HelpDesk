from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.views.generic import View
from ldap3 import Server, Connection, ALL, SUBTREE
from django.contrib import messages

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
            username = request.POST.get("username")
            password = request.POST.get("password")

            ad_user = self.authenticate_ad(username, password)

            if ad_user:
                user, created = User.objects.get_or_create(username=username)
                user.first_name = ad_user["first_name"]
                user.last_name = ad_user["last_name"]
                user.email = ad_user["email"]
                user.save()

                login(request, user)
                messages.success(request, "Usuario logado com sucesso!")
                return redirect("home")
            else:
                messages.warning(request, "Usuario ou senha invalidos")
                return redirect("account")
        except Exception as e:
            print(e)
            messages.error(request, "Erro ao efetuar login")
            return redirect("account")    

    def authenticate_ad(self, username, password):
        server = Server('ldap://cafelandia.pr.gov.br', get_info=ALL)

        user = f"{username}@cafelandia.pr.gov.br"

        try:
            conn = Connection(server, user=user, password=password)
            if conn.bind():
                return self.get_ad_user_data(conn, username)
            else:
                return False
        except Exception as e:
            print(e)
            return False

    def get_ad_user_data(self, conn, username):
        search_base = "dc=cafelandia,dc=pr,dc=gov,dc=br"
        search_filter = f"(|(sAMAccountName={username})(userPrincipalName={username}@cafelandia.pr.gov.br))"

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
    logout(request)
    return redirect("account")
