from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import View

from approval_flow.models import ApprovalRequest
from notifications.views import SendNotification
from ticket.models import Ticket, TicketInteraction
from ticket.views import can_access_ticket, is_support_user


@method_decorator(login_required(login_url="/"), name="dispatch")
class RequestApprovalView(View):

    def post(self, request):
        ticket_id = request.POST.get("ticket_id")
        approver_id = request.POST.get("approver")
        reason = (request.POST.get("reason") or "").strip()

        ticket = get_object_or_404(Ticket, id=ticket_id)

        if not can_access_ticket(request.user, ticket) or not is_support_user(request.user):
            messages.warning(request, "Voce nao tem permissao para solicitar autorizacao neste chamado.")
            return redirect("ticket_detail", ticket_id=ticket.id)

        if len(reason) < 10:
            messages.warning(request, "Informe um motivo com pelo menos 10 caracteres.")
            return redirect("ticket_detail", ticket_id=ticket.id)

        approver = get_object_or_404(User, id=approver_id, is_active=True)

        approval = ApprovalRequest.objects.create(
            ticket=ticket,
            requested_by=request.user,
            approver=approver,
            reason=reason,
        )

        TicketInteraction.objects.create(
            ticket=ticket,
            user=request.user,
            message=f"Solicitou autorizacao de {approver.get_full_name() or approver.username}: {reason}",
            interaction_type="system"
        )

        SendNotification.warning(
            request,
            "Autorizacao solicitada",
            f"O chamado {ticket.hash} precisa da sua autorizacao.",
            False,
            approver,
            "approval_request",
            ticket.id
        )

        messages.success(request, "Solicitacao de autorizacao enviada com sucesso.")
        return redirect("ticket_detail", ticket_id=ticket.id)


@method_decorator(login_required(login_url="/"), name="dispatch")
class ApprovalDecisionView(View):

    def post(self, request, approval_id):
        approval = get_object_or_404(
            ApprovalRequest.objects.select_related("ticket", "requested_by", "approver"),
            id=approval_id
        )

        if approval.approver_id != request.user.id and not request.user.is_superuser:
            messages.warning(request, "Apenas o aprovador definido pode responder esta solicitacao.")
            return redirect("ticket_detail", ticket_id=approval.ticket_id)

        if approval.status != ApprovalRequest.STATUS_PENDING:
            messages.warning(request, "Esta solicitacao ja foi respondida.")
            return redirect("ticket_detail", ticket_id=approval.ticket_id)

        action = request.POST.get("decision")
        comment = (request.POST.get("response_comment") or "").strip()

        if action == "approve":
            approval.status = ApprovalRequest.STATUS_APPROVED
            label = "aprovada"
            notification_title = "Autorizacao aprovada"
        elif action == "reject":
            approval.status = ApprovalRequest.STATUS_REJECTED
            label = "rejeitada"
            notification_title = "Autorizacao rejeitada"
        else:
            messages.warning(request, "Acao invalida.")
            return redirect("ticket_detail", ticket_id=approval.ticket_id)

        approval.response_comment = comment
        approval.decided_at = timezone.now()
        approval.save(update_fields=["status", "response_comment", "decided_at", "updated_at"])

        message = f"Autorizacao {label} por {request.user.get_full_name() or request.user.username}."
        if comment:
            message = f"{message} Observacao: {comment}"

        TicketInteraction.objects.create(
            ticket=approval.ticket,
            user=request.user,
            message=message,
            interaction_type="system"
        )

        SendNotification.success(
            request,
            notification_title,
            f"A solicitacao do chamado {approval.ticket.hash} foi {label}.",
            False,
            approval.requested_by,
            ticket_id=approval.ticket_id
        )

        messages.success(request, f"Solicitacao {label} com sucesso.")
        return redirect("ticket_detail", ticket_id=approval.ticket_id)
