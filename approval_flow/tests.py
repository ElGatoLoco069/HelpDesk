from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from approval_flow.models import ApprovalRequest
from notifications.models import UserNotification
from registers.models import AssignmentMethod, Category, Priority, Subcategory
from ticket.models import Ticket, TicketInteraction, Ticket_Status


class ApprovalFlowTests(TestCase):

    def setUp(self):
        self.support = User.objects.create_user(username="support")
        self.support.profile.is_support = True
        self.support.profile.save(update_fields=["is_support"])

        self.approver = User.objects.create_user(username="approver")
        self.approver.profile.is_support = True
        self.approver.profile.save(update_fields=["is_support"])

        self.requester = User.objects.create_user(username="requester")

        status = Ticket_Status.objects.create(name="Novo", color="open")
        priority = Priority.objects.create(
            name="Alta",
            first_interaction_limit=30,
            estimated_service_time=120,
            color="high",
        )
        assignment = AssignmentMethod.objects.create(
            name="Demanda",
            method_type=AssignmentMethod.MethodType.DEMAND,
        )
        category = Category.objects.create(name="Infra")
        subcategory = Subcategory.objects.create(
            category=category,
            name="Computador",
            priority=priority,
            assignment_method=assignment,
        )
        self.ticket = Ticket.objects.create(
            hash="APR-20260618-0001",
            title=subcategory,
            description="Descricao suficiente para o chamado.",
            status=status,
            priority=priority,
            created_by=self.requester,
            assigned_to=self.support,
        )
        self.client = Client(HTTP_HOST="localhost")

    def create_approval(self):
        return ApprovalRequest.objects.create(
            ticket=self.ticket,
            requested_by=self.support,
            approver=self.approver,
            reason="Necessario aprovar compra de material.",
        )

    def test_support_can_request_approval(self):
        self.client.force_login(self.support)

        response = self.client.post(
            reverse("request_approval"),
            {
                "ticket_id": self.ticket.id,
                "approver": self.approver.id,
                "reason": "Necessario aprovar compra de material.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ApprovalRequest.objects.filter(
                ticket=self.ticket,
                requested_by=self.support,
                approver=self.approver,
                status=ApprovalRequest.STATUS_PENDING,
            ).exists()
        )
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.approver,
                notification__action_kind="approval_request",
                notification__ticket_id=self.ticket.id,
            ).exists()
        )

    def test_approver_can_approve_request(self):
        approval = self.create_approval()
        self.client.force_login(self.approver)

        response = self.client.post(
            reverse("approval_decision", args=[approval.id]),
            {"decision": "approve", "response_comment": "Compra autorizada."},
        )

        approval.refresh_from_db()
        self.assertRedirects(response, reverse("ticket_detail", args=[self.ticket.id]))
        self.assertEqual(approval.status, ApprovalRequest.STATUS_APPROVED)
        self.assertEqual(approval.response_comment, "Compra autorizada.")
        self.assertIsNotNone(approval.decided_at)
        self.assertTrue(
            TicketInteraction.objects.filter(
                ticket=self.ticket,
                user=self.approver,
                message__startswith="Autorizacao aprovada",
            ).exists()
        )

    def test_approver_can_reject_request(self):
        approval = self.create_approval()
        self.client.force_login(self.approver)

        response = self.client.post(
            reverse("approval_decision", args=[approval.id]),
            {"decision": "reject", "response_comment": "Compra nao autorizada."},
        )

        approval.refresh_from_db()
        self.assertRedirects(response, reverse("ticket_detail", args=[self.ticket.id]))
        self.assertEqual(approval.status, ApprovalRequest.STATUS_REJECTED)
        self.assertEqual(approval.response_comment, "Compra nao autorizada.")
        self.assertIsNotNone(approval.decided_at)
        self.assertTrue(
            TicketInteraction.objects.filter(
                ticket=self.ticket,
                user=self.approver,
                message__startswith="Autorizacao rejeitada",
            ).exists()
        )

    def test_unrelated_user_cannot_decide_request(self):
        approval = self.create_approval()
        self.client.force_login(self.requester)

        response = self.client.post(
            reverse("approval_decision", args=[approval.id]),
            {"decision": "approve"},
        )

        approval.refresh_from_db()
        self.assertRedirects(response, reverse("ticket_detail", args=[self.ticket.id]))
        self.assertEqual(approval.status, ApprovalRequest.STATUS_PENDING)
        self.assertIsNone(approval.decided_at)

    def test_decision_form_keeps_action_in_hidden_field(self):
        self.create_approval()
        self.client.force_login(self.approver)

        response = self.client.get(reverse("ticket_detail", args=[self.ticket.id]))

        self.assertContains(response, "data-approval-decision-form")
        self.assertContains(response, 'name="decision" data-approval-decision-field')
        self.assertContains(response, 'data-approval-decision="approve"')
        self.assertContains(response, 'data-approval-decision="reject"')
