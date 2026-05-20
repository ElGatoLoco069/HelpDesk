from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from django.contrib import messages

from registers.models import Category, Priority, Subcategory
from ticket.models import Ticket, TicketAttachment, TicketReport, Ticket_Status
from accounts.models import Profile

import random
import string
from datetime import datetime

from notifications.views import SendNotification

MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
ACCEPTED_ATTACHMENT_TYPES = {"image/png", "image/jpeg", "application/pdf"}

@method_decorator(login_required(login_url="/"), name="dispatch")
class TicketView(View):
    
    
    def get(self, request):
        
        try:
            
            categories = Category.objects.filter(status=True)
            
            return render(
                request, 
                "new_ticket.html",
                {
                    "active_page":"new_ticket",
                    "categories":categories,
                })
        
        except Exception as e:
            print(e)
            messages.error(request, "Erro ao carregar formulario de registro de chamados")
            return redirect("home")


    def post(self, request):

        try:

            action = request.POST.get("action")

            if action == "create":
                ticket = self.create(request)
                if not ticket:
                    return redirect("new_ticket")
                return redirect("home")

            return redirect("new_ticket")

        except Exception as e:
            messages.error(request, f"Erro: {e}")
            return redirect("home")


    def hash_generate(self):

        while True:
            today = datetime.today().strftime("%Y%m%d")
            letters = "".join(random.choices(string.ascii_uppercase, k=4))
            numbers = random.randint(1000, 9999)
            ticket_hash = f"{letters}-{today}-{numbers}"

            if not Ticket.objects.filter(hash=ticket_hash).exists():
                return ticket_hash


    def create(self, request):

        try:
            subcategory = request.POST.get("subcategory")
            description = (request.POST.get("description") or "").strip()

            if not subcategory:
                messages.warning(request, "Selecione uma subcategoria para criar o chamado.")
                return None

            if len(description) < 15:
                messages.warning(request, "Informe uma descricao com pelo menos 15 caracteres.")
                return None

            attachments = request.FILES.getlist("attachments")

            for attachment in attachments:
                if attachment.content_type not in ACCEPTED_ATTACHMENT_TYPES:
                    messages.warning(request, f"{attachment.name} nao e um arquivo PNG, JPG ou PDF.")
                    return None

                if attachment.size > MAX_ATTACHMENT_SIZE:
                    messages.warning(request, f"{attachment.name} excede o limite de 10MB.")
                    return None

            ticket_hash = self.hash_generate()
            title = Subcategory.objects.get(id=subcategory)
            status = Ticket_Status.objects.filter(name__iexact="Novo").first()

            phone = request.POST.get("phone")

            if not status:
                status = Ticket_Status.objects.order_by("id").first()

            if not status:
                messages.error(request, "Nenhum status inicial encontrado para criar chamado.")
                return None

            ticket = Ticket.objects.create(
                hash=ticket_hash,
                title=title,
                description=description,
                status=status,
                priority=title.priority,
                created_by=request.user
            )

            for attachment in attachments:
                TicketAttachment.objects.create(
                    ticket=ticket,
                    file=attachment,
                    original_name=attachment.name,
                    content_type=attachment.content_type,
                    size=attachment.size,
                )
            
            messages.success(request, f"Chamado criado com sucesso!")
            
            request.user.profile.telefone = phone
            request.user.profile.save()
            
            SendNotification.success(
                request, 
                "Chamado Criado", f"Chamado {ticket_hash} criado com sucesso!",
                False,
                ticket.created_by
            )
            
            return ticket
        
        except Exception as e:
            print(e)
            messages.error(request, "Erro ao criar chamado!")
            return redirect("home")


@method_decorator(login_required(login_url="/"), name="dispatch")
class TicketDetailView(View):

    def get(self, request, ticket_id):

        try:
            ticket = get_object_or_404(
                Ticket.objects.select_related(
                    "title__category",
                    "title__priority",
                    "title__assignment_method",
                    "priority",
                    "status",
                    "created_by",
                    "assigned_to",
                ).prefetch_related("attachments", "reports__technician"),
                id=ticket_id,
            )

            return render(
                request,
                "ticket_detail.html",
                {
                    "active_page": "home",
                    "ticket": ticket,
                },
            )

        except Exception as e:
            print(e)
            messages.error(request, "Erro ao carregar detalhes do chamado")
            return redirect("home")


@method_decorator(login_required(login_url="/"), name="dispatch")
class TicketEditView(View):

    def get_ticket(self, ticket_id):
        return get_object_or_404(
            Ticket.objects.select_related(
                "title__category",
                "title__assignment_method",
                "priority",
                "status",
                "created_by",
                "assigned_to",
            ),
            id=ticket_id,
        )


    def is_ticket_technician(self, user, ticket):
        try:
            return (
                user.profile.is_support and
                ticket.assigned_to_id == user.id
            )
        except Profile.DoesNotExist:
            return False


    def get_support_users(self):
        return User.objects.filter(profile__is_support=True)

       
    def get_context(self, request, ticket):
        return {
            "active_page": "home",
            "ticket": ticket,
            "status": Ticket_Status.objects.filter(status=True).order_by("id"),
            "priorities": Priority.objects.filter(status=True).order_by("id"),
            "technicians": self.get_support_users,
            "can_add_report": self.is_ticket_technician(request.user, ticket),
        }


    def get(self, request, ticket_id):

        try:
            ticket = self.get_ticket(ticket_id)
            return render(request, "ticket_edit.html", self.get_context(request, ticket))

        except Exception as e:
            print(e)
            messages.error(request, "Erro ao carregar edicao do chamado")
            return redirect("ticket_detail", ticket_id=ticket_id)


    def post(self, request, ticket_id):

        try:
            ticket = self.get_ticket(ticket_id)
            action = request.POST.get("action")

            if action == "create_report":
                return self.create_report(request, ticket)

            status_id = request.POST.get("status")
            priority_id = request.POST.get("priority")
            assigned_to_id = request.POST.get("assigned_to")

            try:
                status_id = int(status_id)
                priority_id = int(priority_id)
                assigned_to_id = int(assigned_to_id) if assigned_to_id else None

            except (TypeError, ValueError):
                messages.warning(request, "Dados inválidos enviados.")
                return render(
                    request,
                    "ticket_edit.html",
                    self.get_context(request, ticket)
                )

            if not Ticket_Status.objects.filter(
                id=status_id,
                status=True
            ).exists():

                messages.warning(request, "Selecione um status válido.")

                return render(
                    request,
                    "ticket_edit.html",
                    self.get_context(request, ticket)
                )

            if not Priority.objects.filter(
                id=priority_id,
                status=True
            ).exists():

                messages.warning(request, "Selecione uma prioridade válida.")

                return render(
                    request,
                    "ticket_edit.html",
                    self.get_context(request, ticket)
                )

            if assigned_to_id and not User.objects.filter(
                id=assigned_to_id,
                is_active=True
            ).exists():

                messages.warning(request, "Selecione um técnico válido.")

                return render(
                    request,
                    "ticket_edit.html",
                    self.get_context(request, ticket)
                )

            if assigned_to_id != ticket.assigned_to_id:

                assigned_user = User.objects.get(id=assigned_to_id) if assigned_to_id else None

                SendNotification.success(
                    request,
                    "Técnico Atribuído",
                    f"O chamado {ticket.hash} foi atribuído para "
                    f"{assigned_user.get_full_name() if assigned_user else 'nenhum técnico'}.",
                    False,
                    ticket.created_by
                )
                
            if not TicketReport.objects.filter(ticket=ticket).exists() and status_id ==  5:
                
                messages.warning(request, "Para finalizar o chamado é necessario adicionar o relatorio tecnico!.")

                return render(
                    request,
                    "ticket_edit.html",
                    self.get_context(request, ticket)
                )

            if status_id != ticket.status.id:
                SendNotification.success(request,
                "Status do chamado Atualizado",
                f"O chamado {ticket.hash} esta {Ticket_Status.objects.get(id=status_id)}",
                False, ticket.created_by)

            if status_id == 5:
                
                SendNotification.success(request, 
                "Chamado concluido", 
                f"O tecnico {ticket.assigned_to.get_full_name()} acaba de concluir o chamado {ticket.hash}!",
                False, ticket.created_by)
                

            # =========================
            # ATUALIZAÇÃO DO CHAMADO
            # =========================
            ticket.status_id = status_id
            ticket.priority_id = priority_id
            ticket.assigned_to_id = assigned_to_id

            ticket.save()

            # =========================
            # SUCESSO
            # =========================
            messages.success(request, "Chamado atualizado com sucesso!")

            return redirect(
                "ticket_detail",
                ticket_id=ticket.id
            )

        except Exception as e:

            print("ERRO AO ATUALIZAR CHAMADO:", e)

            messages.error(
                request,
                "Erro ao atualizar chamado."
            )

            return redirect(
                "ticket_detail",
                ticket_id=ticket_id
            )


    def create_report(self, request, ticket):

        if not self.is_ticket_technician(request.user, ticket):
            messages.warning(request, "Apenas o tecnico responsavel pode adicionar relatorio.")
            return redirect("ticket_edit", ticket_id=ticket.id)

        summary = (request.POST.get("summary") or "").strip()
        actions = (request.POST.get("actions") or "").strip()
        materials = (request.POST.get("materials") or "").strip()

        if len(summary) < 10:
            messages.warning(request, "Informe um resumo do atendimento com pelo menos 10 caracteres.")
            return render(request, "ticket_edit.html", self.get_context(request, ticket))

        if not actions:
            messages.warning(request, "Informe ao menos uma acao realizada.")
            return render(request, "ticket_edit.html", self.get_context(request, ticket))

        TicketReport.objects.create(
            ticket=ticket,
            technician=request.user,
            summary=summary,
            actions=actions,
            materials=materials,
        )
        
        SendNotification.success(request, 
        "Relatorio tecnico adicionado",
        f"O tecnico adicionou um relatorio ao chamado {ticket.hash}", 
        False, ticket.created_by)

        messages.success(request, "Relatorio tecnico adicionado com sucesso!")
        return redirect("ticket_detail", ticket_id=ticket.id)


