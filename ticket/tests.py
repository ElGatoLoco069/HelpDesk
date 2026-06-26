import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from registers.models import AssignmentMethod, Category, Priority, Subcategory
from ticket.models import (
    Ticket,
    TicketAttachment,
    TicketInteraction,
    Ticket_Status,
)


class TicketFlowTests(TestCase):

    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        self.requester = User.objects.create_user(username="requester")
        self.other_user = User.objects.create_user(username="other")
        self.support = User.objects.create_user(username="support")
        self.support.profile.is_support = True
        self.support.profile.save(update_fields=["is_support"])

        self.status = Ticket_Status.objects.create(name="Novo", color="open")
        self.priority = Priority.objects.create(
            name="Alta",
            first_interaction_limit=30,
            estimated_service_time=120,
            color="high",
        )
        self.assignment = AssignmentMethod.objects.create(
            name="Demanda",
            method_type=AssignmentMethod.MethodType.DEMAND,
        )
        self.category = Category.objects.create(name="Infra")
        self.subcategory = Subcategory.objects.create(
            category=self.category,
            name="Computador",
            priority=self.priority,
            assignment_method=self.assignment,
        )
        self.ticket = Ticket.objects.create(
            hash="TEST-20260618-0001",
            title=self.subcategory,
            description="Descricao suficiente para o chamado.",
            status=self.status,
            priority=self.priority,
            created_by=self.requester,
            assigned_to=self.support,
        )
        self.client = Client(HTTP_HOST="localhost")

    def test_ticket_detail_blocks_unrelated_user(self):
        self.client.force_login(self.other_user)

        response = self.client.get(reverse("ticket_detail", args=[self.ticket.id]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("home"))

    def test_ticket_detail_allows_requester(self):
        self.client.force_login(self.requester)

        response = self.client.get(reverse("ticket_detail", args=[self.ticket.id]))

        self.assertEqual(response.status_code, 200)

    def test_add_message_does_not_save_attachments(self):
        self.client.force_login(self.requester)
        attachment = SimpleUploadedFile(
            "evidencia.pdf",
            b"%PDF-1.4\n",
            content_type="application/pdf",
        )

        response = self.client.post(
            reverse("add_message"),
            {
                "ticket": self.ticket.hash,
                "message": "Segue evidencia do problema.",
                "attachments": attachment,
            },
        )

        self.assertEqual(response.status_code, 302)
        interaction = TicketInteraction.objects.get(message="Segue evidencia do problema.")
        self.assertEqual(interaction.attachments.count(), 0)
        self.assertFalse(TicketAttachment.objects.filter(ticket=self.ticket).exists())

    def test_add_ticket_attachment_saves_file_on_existing_ticket(self):
        self.client.force_login(self.requester)
        attachment = SimpleUploadedFile(
            "novo-anexo.pdf",
            b"%PDF-1.4\n",
            content_type="application/pdf",
        )

        response = self.client.post(
            reverse("add_ticket_attachment", args=[self.ticket.id]),
            {"attachments": attachment},
        )

        self.assertRedirects(response, reverse("ticket_detail", args=[self.ticket.id]))
        self.assertTrue(
            TicketAttachment.objects.filter(
                ticket=self.ticket,
                original_name="novo-anexo.pdf",
            ).exists()
        )

    def test_add_ticket_attachment_blocks_unrelated_user(self):
        self.client.force_login(self.other_user)
        attachment = SimpleUploadedFile(
            "privado.pdf",
            b"%PDF-1.4\n",
            content_type="application/pdf",
        )

        response = self.client.post(
            reverse("add_ticket_attachment", args=[self.ticket.id]),
            {"attachments": attachment},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("home"))
        self.assertFalse(TicketAttachment.objects.filter(ticket=self.ticket).exists())
