import shutil
import tempfile
from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from registers.models import AssignmentMethod, Category, Priority, Subcategory
from ticket.services import auto_close_expired_solution_proposals
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

    def test_ticket_detail_groups_content_in_three_tabs(self):
        self.client.force_login(self.requester)

        response = self.client.get(reverse("ticket_detail", args=[self.ticket.id]))

        self.assertContains(response, 'data-ticket-tab="ticket-service-panel"')
        self.assertContains(response, 'data-ticket-tab="ticket-attachments-panel"')
        self.assertContains(response, 'data-ticket-tab="ticket-records-panel"')
        self.assertContains(response, 'id="ticket-service-panel"')
        self.assertContains(response, 'id="ticket-attachments-panel"')
        self.assertContains(response, 'id="ticket-records-panel"')
        self.assertContains(response, "Atendimento")
        self.assertContains(response, "Anexos")
        self.assertContains(response, "Registros")

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

    def test_assignment_date_is_set_only_once(self):
        self.assertIsNotNone(self.ticket.assigned_at)
        assigned_at = self.ticket.assigned_at

        self.ticket.title = self.subcategory
        self.ticket.save(update_fields=["title"])
        self.ticket.refresh_from_db()

        self.assertEqual(self.ticket.assigned_at, assigned_at)

    def test_done_and_cancelled_statuses_set_lifecycle_dates(self):
        done = Ticket_Status.objects.create(name="Concluido", color="done")
        self.ticket.status = done
        self.ticket.save(update_fields=["status"])
        self.ticket.refresh_from_db()

        self.assertIsNotNone(self.ticket.closed_at)
        self.assertIsNone(self.ticket.cancelled_at)

        reopened = Ticket_Status.objects.create(name="Em andamento", color="progress")
        self.ticket.status = reopened
        self.ticket.save(update_fields=["status"])
        self.ticket.refresh_from_db()

        self.assertIsNotNone(self.ticket.reopened_at)

        cancelled = Ticket_Status.objects.create(name="Cancelado", color="cancelled")
        self.ticket.status = cancelled
        self.ticket.save(update_fields=["status"])
        self.ticket.refresh_from_db()

        self.assertIsNotNone(self.ticket.cancelled_at)

    def test_resolution_timer_pauses_and_accumulates_when_waiting_status_ends(self):
        paused_status = Ticket_Status.objects.create(name="Acao do cliente", color="warning")
        in_service_status = Ticket_Status.objects.create(name="Em andamento", color="progress")

        self.ticket.status = paused_status
        self.ticket.save(update_fields=["status"])
        self.ticket.refresh_from_db()

        self.assertIsNotNone(self.ticket.resolution_paused_at)

        Ticket.objects.filter(id=self.ticket.id).update(
            resolution_paused_at=timezone.now() - timedelta(minutes=90)
        )
        self.ticket.refresh_from_db()

        self.ticket.status = in_service_status
        self.ticket.save(update_fields=["status"])
        self.ticket.refresh_from_db()

        self.assertIsNone(self.ticket.resolution_paused_at)
        self.assertGreaterEqual(self.ticket.resolution_paused_seconds, 89 * 60)
        self.assertLessEqual(self.ticket.resolution_paused_seconds, 91 * 60)

    def test_report_views_discount_resolution_pause_and_expose_technician_ratings(self):
        done = Ticket_Status.objects.create(name="Concluido", color="done")
        now = timezone.now()

        self.ticket.status = done
        self.ticket.satisfaction_rating = 4
        self.ticket.evaluated_at = now
        self.ticket.save(update_fields=[
            "status",
            "satisfaction_rating",
            "evaluated_at",
            "updated_at",
        ])
        Ticket.objects.filter(id=self.ticket.id).update(
            created_at=now - timedelta(hours=5),
            closed_at=now,
            resolution_paused_seconds=2 * 60 * 60,
            resolution_paused_at=None,
        )

        call_command("create_report_views", stdout=StringIO())

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    tempo_resolucao_horas,
                    tempo_resolucao_corrida_horas,
                    tempo_pausado_resolucao_horas
                FROM vw_relatorio_chamados_geral
                WHERE chamado_id = %s
                """,
                [self.ticket.id],
            )
            active_hours, elapsed_hours, paused_hours = cursor.fetchone()

            cursor.execute(
                """
                SELECT total_avaliacoes, nota_media
                FROM vw_notas_tecnicos
                WHERE tecnico_id = %s
                """,
                [self.support.id],
            )
            total_ratings, average_rating = cursor.fetchone()

        self.assertEqual(active_hours, 3)
        self.assertEqual(elapsed_hours, 5)
        self.assertEqual(paused_hours, 2)
        self.assertEqual(total_ratings, 1)
        self.assertEqual(average_rating, 4)

    def test_first_technician_interaction_sets_first_response_once(self):
        TicketInteraction.objects.create(
            ticket=self.ticket,
            user=self.requester,
            message="Mensagem inicial do solicitante.",
            interaction_type="requester",
        )
        self.ticket.refresh_from_db()
        self.assertIsNone(self.ticket.first_response_at)

        first = TicketInteraction.objects.create(
            ticket=self.ticket,
            user=self.support,
            message="Primeira resposta tecnica.",
            interaction_type="technician",
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.first_response_at, first.created_at)

        first_response_at = self.ticket.first_response_at
        TicketInteraction.objects.create(
            ticket=self.ticket,
            user=self.support,
            message="Segunda resposta tecnica.",
            interaction_type="technician",
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.first_response_at, first_response_at)

    def test_expired_solution_proposal_is_closed_and_rated_automatically(self):
        solution_status = Ticket_Status.objects.create(
            name="Proposta de Solucao",
            color="warning",
        )
        done_status = Ticket_Status.objects.create(
            name="Concluido",
            color="open",
        )
        now = timezone.now()

        self.ticket.status = solution_status
        self.ticket.solution_proposed_at = now - timedelta(days=8)
        self.ticket.requester_solution_accepted = None
        self.ticket.satisfaction_rating = None
        self.ticket.save(update_fields=[
            "status",
            "solution_proposed_at",
            "requester_solution_accepted",
            "satisfaction_rating",
            "updated_at",
        ])

        closed_count = auto_close_expired_solution_proposals(now=now)

        self.assertEqual(closed_count, 1)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, done_status)
        self.assertTrue(self.ticket.requester_solution_accepted)
        self.assertEqual(self.ticket.satisfaction_rating, 5)
        self.assertIsNotNone(self.ticket.solution_responded_at)
        self.assertIsNotNone(self.ticket.evaluated_at)
        self.assertIsNotNone(self.ticket.closed_at)

    def test_recent_solution_proposal_is_not_closed_automatically(self):
        solution_status = Ticket_Status.objects.create(
            name="Proposta de Solucao",
            color="warning",
        )
        Ticket_Status.objects.create(
            name="Concluido",
            color="open",
        )
        now = timezone.now()

        self.ticket.status = solution_status
        self.ticket.solution_proposed_at = now - timedelta(days=6, hours=23)
        self.ticket.requester_solution_accepted = None
        self.ticket.satisfaction_rating = None
        self.ticket.save(update_fields=[
            "status",
            "solution_proposed_at",
            "requester_solution_accepted",
            "satisfaction_rating",
            "updated_at",
        ])

        closed_count = auto_close_expired_solution_proposals(now=now)

        self.assertEqual(closed_count, 0)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, solution_status)
        self.assertIsNone(self.ticket.satisfaction_rating)
