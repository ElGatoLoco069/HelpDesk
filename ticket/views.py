from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.contrib import messages

from registers.models import Category, Priority, Subcategory
from ticket.models import Ticket, TicketAttachment, TicketReport, Ticket_Status, TicketInteraction
from accounts.models import Profile
from notifications.models import UserNotification

import random
import string
from datetime import datetime

from notifications.views import SendNotification

MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
ACCEPTED_ATTACHMENT_TYPES = {"image/png", "image/jpeg", "application/pdf"}

STATUS_CONCLUIDO = "concluido"
STATUS_PROPOSTA = "proposta de solucao"


def normalize_status_name(name):
    return (name or "").strip().lower().replace("ç", "c").replace("ã", "a")


def get_status_by_name(*names):
    normalized = [normalize_status_name(name) for name in names]

    for status in Ticket_Status.objects.filter(status=True):
        if normalize_status_name(status.name) in normalized:
            return status

    return None


def get_solution_status():
    status = get_status_by_name(STATUS_PROPOSTA, "proposta de solução")

    if status:
        return status

    return Ticket_Status.objects.create(
        name="Proposta de Solucao",
        color="warning",
        status=True
    )


def get_done_status():
    return get_status_by_name(STATUS_CONCLUIDO, "concluído")

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

            interactions = TicketInteraction.objects.filter(ticket=ticket)
            return render(
                request,
                "ticket_detail.html",
                {
                    "active_page": "home",
                    "ticket": ticket,
                    "interactions":interactions,
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
        interactions = TicketInteraction.objects.filter(ticket=ticket)
        solution_status = get_solution_status()
        done_status = get_done_status()
        status_options = list(Ticket_Status.objects.filter(status=True).order_by("id"))

        if done_status and ticket.status_id != done_status.id:
            status_options = [item for item in status_options if item.id != done_status.id]

        if solution_status.id not in [item.id for item in status_options]:
            status_options.append(solution_status)

        return {
            "active_page": "home",
            "ticket": ticket,
            "status": status_options,
            "priorities": Priority.objects.filter(status=True).order_by("id"),
            "technicians": self.get_support_users,
            "can_add_report": self.is_ticket_technician(request.user, ticket),
            "interactions":interactions,
        }


    def get(self, request, ticket_id):

        try:
            ticket = self.get_ticket(ticket_id)

            return render(request, "ticket_edit.html", self.get_context(request, ticket), )

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

            if action == "respond_solution":
                return self.respond_solution(request, ticket)

            if action == "evaluate_service":
                return self.evaluate_service(request, ticket)

            if not request.user.profile.is_support:
                messages.warning(
                    request,
                    "Apenas usuarios de suporte podem editar o chamado."
                )

                return redirect(
                    "ticket_detail",
                    ticket_id=ticket.id
                )

            status_id = request.POST.get("status")
            priority_id = request.POST.get("priority")
            assigned_to_id = request.POST.get("assigned_to")

            try:
                status_id = int(status_id)
                priority_id = int(priority_id)
                assigned_to_id = int(assigned_to_id) if assigned_to_id else None

            except (TypeError, ValueError):

                messages.warning(
                    request,
                    "Dados inválidos enviados."
                )

                return render(
                    request,
                    "ticket_edit.html",
                    self.get_context(request, ticket)
                )

            # =========================
            # VALIDA STATUS
            # =========================
            if not Ticket_Status.objects.filter(
                id=status_id,
                status=True
            ).exists():

                messages.warning(
                    request,
                    "Selecione um status válido."
                )

                return render(
                    request,
                    "ticket_edit.html",
                    self.get_context(request, ticket)
                )

            # =========================
            # VALIDA PRIORIDADE
            # =========================
            if not Priority.objects.filter(
                id=priority_id,
                status=True
            ).exists():

                messages.warning(
                    request,
                    "Selecione uma prioridade válida."
                )

                return render(
                    request,
                    "ticket_edit.html",
                    self.get_context(request, ticket)
                )

            # =========================
            # VALIDA TÉCNICO
            # =========================
            if assigned_to_id and not User.objects.filter(
                id=assigned_to_id,
                is_active=True
            ).exists():

                messages.warning(
                    request,
                    "Selecione um técnico válido."
                )

                return render(
                    request,
                    "ticket_edit.html",
                    self.get_context(request, ticket)
                )

            # =========================
            # ALTERAÇÃO DE TÉCNICO
            # =========================
            if assigned_to_id != ticket.assigned_to_id:

                assigned_user = (
                    User.objects.get(id=assigned_to_id)
                    if assigned_to_id else None
                )

                SendNotification.success(
                    request,
                    "Técnico Atribuído",
                    f"O chamado {ticket.hash} foi atribuído para "
                    f"{assigned_user.get_full_name() if assigned_user else 'nenhum técnico'}.",
                    False,
                    ticket.created_by
                )

                # força status para EM ATENDIMENTO
                status_id = 2

            selected_status = Ticket_Status.objects.get(id=status_id)

            selected_status_name = normalize_status_name(
                selected_status.name
            )

            done_status = get_done_status()
            solution_status = get_solution_status()

            is_closing_status = (
                selected_status_name in [
                    STATUS_CONCLUIDO,
                    STATUS_PROPOSTA
                ]
                or (
                    done_status and
                    status_id == done_status.id
                )
                or status_id == solution_status.id
            )

            # =========================
            # VALIDA RELATÓRIO TÉCNICO
            # =========================
            if (
                not TicketReport.objects.filter(ticket=ticket).exists()
                and is_closing_status
            ):

                messages.warning(
                    request,
                    "Para propor a solução do chamado é necessário adicionar o relatório técnico!"
                )

                return render(
                    request,
                    "ticket_edit.html",
                    self.get_context(request, ticket)
                )

            # =========================
            # CONCLUÍDO -> PROPOSTA
            # =========================
            if done_status and status_id == done_status.id:

                status_id = solution_status.id
                selected_status = solution_status

                messages.success(
                    request,
                    "O chamado foi movido para proposta de solução para validação do solicitante."
                )

            # =========================
            # NOTIFICA ALTERAÇÃO STATUS
            # =========================
            if status_id != ticket.status.id:

                SendNotification.success(
                    request,
                    "Status do chamado Atualizado",
                    f"O chamado {ticket.hash} está {selected_status}",
                    False,
                    ticket.created_by
                )

            # =========================
            # PROPOSTA DE SOLUÇÃO
            # =========================
            if (
                status_id == solution_status.id
                and ticket.status_id != solution_status.id
            ):

                SendNotification.warning(
                    request,
                    "Proposta de solução",
                    f"O técnico "
                    f"{ticket.assigned_to.get_full_name() if ticket.assigned_to else 'responsável'} "
                    f"enviou uma proposta de solução para o chamado {ticket.hash}. "
                    f"Confirme se foi resolvido.",
                    False,
                    ticket.created_by,
                    "solution_validation",
                    ticket.id
                )

                ticket.solution_proposed_at = timezone.now()
                ticket.solution_responded_at = None
                ticket.requester_solution_accepted = None

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
            messages.success(
                request,
                "Chamado atualizado com sucesso!"
            )

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

        ticket.status = Ticket_Status.objects.get(id=6)
        ticket.save()
        
        SendNotification.warning(request, 
                "Proposta de solucao", 
                f"O tecnico {ticket.assigned_to.get_full_name() if ticket.assigned_to else 'responsavel'} enviou uma proposta de solucao para o chamado {ticket.hash}. Confirme se foi resolvido.",
                False,
                ticket.created_by,
                "solution_validation",
                ticket.id)
        
        ticket.solution_proposed_at = timezone.now()
        ticket.solution_responded_at = None
        ticket.requester_solution_accepted = None


        messages.success(request, "Relatorio tecnico adicionado com sucesso!")
        return redirect("ticket_detail", ticket_id=ticket.id)


    def respond_solution(self, request, ticket):

        if request.user != ticket.created_by:
            messages.warning(request, "Apenas o solicitante pode validar a proposta de solucao.")
            return redirect("ticket_detail", ticket_id=ticket.id)

        solution_status = get_solution_status()

        if ticket.status_id != solution_status.id or ticket.requester_solution_accepted is not None:
            messages.warning(request, "Este chamado nao possui proposta de solucao pendente.")
            return redirect("ticket_detail", ticket_id=ticket.id)

        resolved = request.POST.get("resolved") == "yes"
        comment = (request.POST.get("solution_comment") or "").strip()

        ticket.requester_solution_accepted = resolved
        ticket.solution_responded_at = timezone.now()

        if resolved:
            done_status = get_done_status()

            if not done_status:
                done_status = Ticket_Status.objects.create(
                    name="Concluido",
                    color="open",
                    status=True
                )

            ticket.status = done_status
            ticket.evaluation_requested_at = timezone.now()
            ticket.save(update_fields=[
                "status",
                "requester_solution_accepted",
                "solution_responded_at",
                "evaluation_requested_at",
                "updated_at",
            ])

            TicketInteraction.objects.create(
                ticket=ticket,
                user=request.user,
                message=comment or "Solicitante confirmou que a proposta resolveu o chamado.",
                interaction_type="requester"
            )

            SendNotification.success(
                request,
                "Avalie o atendimento",
                f"O chamado {ticket.hash} foi concluido. Por favor avalie o atendimento recebido.",
                False,
                ticket.created_by,
                "service_evaluation",
                ticket.id
            )

            UserNotification.objects.filter(
                user=request.user,
                notification__ticket_id=ticket.id,
                notification__action_kind="solution_validation"
            ).update(read=True, hidden=True)

            messages.success(request, "Chamado concluido. A avaliacao do atendimento ja esta disponivel.")
            return redirect("ticket_detail", ticket_id=ticket.id)

        in_service_status = get_status_by_name("em andamento", "aguardando", "novo")

        if in_service_status:
            ticket.status = in_service_status

        ticket.save(update_fields=[
            "status",
            "requester_solution_accepted",
            "solution_responded_at",
            "updated_at",
        ])

        TicketInteraction.objects.create(
            ticket=ticket,
            user=request.user,
            message=comment or "Solicitante informou que a proposta nao resolveu o chamado.",
            interaction_type="requester"
        )

        if ticket.assigned_to:
            SendNotification.warning(
                request,
                "Chamado nao resolvido",
                f"O solicitante marcou o chamado {ticket.hash} como nao resolvido. Revise a proposta de solucao.",
                False,
                ticket.assigned_to
            )

        UserNotification.objects.filter(
            user=request.user,
            notification__ticket_id=ticket.id,
            notification__action_kind="solution_validation"
        ).update(read=True, hidden=True)

        messages.warning(request, "O tecnico responsavel foi notificado para revisar o atendimento.")
        return redirect("ticket_detail", ticket_id=ticket.id)


    def evaluate_service(self, request, ticket):

        if request.user != ticket.created_by:
            messages.warning(request, "Apenas o solicitante pode avaliar este atendimento.")
            return redirect("ticket_detail", ticket_id=ticket.id)

        done_status = get_done_status()

        if not done_status or ticket.status_id != done_status.id:
            messages.warning(request, "A avaliacao fica disponivel apenas apos a conclusao do chamado.")
            return redirect("ticket_detail", ticket_id=ticket.id)

        if ticket.satisfaction_rating is not None:
            messages.warning(request, "Este atendimento ja foi avaliado.")
            return redirect("ticket_detail", ticket_id=ticket.id)

        try:
            rating = int(request.POST.get("rating"))
        except (TypeError, ValueError):
            messages.warning(request, "Selecione uma nota valida.")
            return redirect("ticket_detail", ticket_id=ticket.id)

        if rating < 1 or rating > 5:
            messages.warning(request, "A nota deve ficar entre 1 e 5.")
            return redirect("ticket_detail", ticket_id=ticket.id)

        ticket.satisfaction_rating = rating
        ticket.satisfaction_comment = (request.POST.get("comment") or "").strip()
        ticket.evaluated_at = timezone.now()
        ticket.save(update_fields=[
            "satisfaction_rating",
            "satisfaction_comment",
            "evaluated_at",
            "updated_at",
        ])

        if ticket.assigned_to:
            SendNotification.success(
                request,
                "Atendimento avaliado",
                f"O solicitante avaliou o chamado {ticket.hash} com nota {rating}/5.",
                False,
                ticket.assigned_to
            )

        UserNotification.objects.filter(
            user=request.user,
            notification__ticket_id=ticket.id,
            notification__action_kind="service_evaluation"
        ).update(read=True, hidden=True)

        messages.success(request, "Obrigado pela avaliacao do atendimento!")
        return redirect("ticket_detail", ticket_id=ticket.id)


@method_decorator(login_required(login_url="/"), name="dispatch")
class AddMessage(View):

    def post(self, request):

        form_ticket = request.POST.get("ticket")
        message = (request.POST.get("message") or "").strip()

        ticket = get_object_or_404(Ticket, hash=form_ticket)

        if not message:
            messages.error(request, "Digite uma mensagem válida.")
            return redirect("ticket_detail", ticket.id)

        if ticket.created_by == request.user:
            interaction_type = "requester"

        elif ticket.assigned_to == request.user:
            interaction_type = "technician"

        else:
            interaction_type = "system"

        TicketInteraction.objects.create(
            ticket=ticket,
            user=request.user,
            message=message,
            interaction_type=interaction_type
        )

        messages.success(request, "Mensagem adicionada com sucesso!")

        if ticket.created_by == request.user and ticket.assigned_to:

            SendNotification.success(
                request,
                "Nova mensagem recebida",
                f"O solicitante acabou de enviar uma nova mensagem sobre o chamado {ticket.hash}",
                False,
                ticket.assigned_to
            )

        elif ticket.assigned_to == request.user:

            SendNotification.success(
                request,
                "Nova mensagem recebida",
                f"O técnico acabou de enviar uma nova mensagem sobre o chamado {ticket.hash}",
                False,
                ticket.created_by
            )

        return redirect("ticket_detail", ticket.id)
    
    
