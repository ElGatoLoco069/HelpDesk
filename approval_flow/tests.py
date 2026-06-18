from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from approval_flow.models import ApprovalRequest
from notifications.models import UserNotification
from registers.models import AssignmentMethod, Category, Priority, Subcategory
from ticket.models import Ticket, Ticket_Status


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
