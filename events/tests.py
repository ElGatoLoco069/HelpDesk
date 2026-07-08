from datetime import date, time

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from .models import Event


class EventModuleTests(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST="localhost")
        self.requester = User.objects.create_user(
            username="requester",
            first_name="Maria",
            last_name="Silva",
        )
        self.support = User.objects.create_user(
            username="support",
            first_name="Joao",
            last_name="Tecnico",
        )
        self.support.profile.is_support = True
        self.support.profile.save(update_fields=["is_support"])

    def event_data(self, **overrides):
        data = {
            "title": "Audiencia Publica",
            "description": "Evento com suporte audiovisual.",
            "event_date": "2026-07-15",
            "start_time": "09:00",
            "end_time": "11:30",
            "location": "Camara Municipal",
            "requester": str(self.requester.id),
            "responsible_technician": str(self.support.id),
            "status": Event.Status.PLANNED,
            "priority": Event.Priority.HIGH,
            "estimated_people": "80",
            "required_resources": "Projetor\nMicrofone",
            "needs_onsite_support": "on",
            "technical_notes": "Checar som antes do inicio.",
        }
        data.update(overrides)
        return data

    def create_event(self, **overrides):
        data = {
            "title": "Audiencia Publica",
            "description": "Evento com suporte audiovisual.",
            "event_date": date(2026, 7, 15),
            "start_time": time(9, 0),
            "end_time": time(11, 30),
            "location": "Camara Municipal",
            "requester": self.requester,
            "responsible_technician": self.support,
            "status": Event.Status.PLANNED,
            "priority": Event.Priority.HIGH,
            "created_by": self.support,
        }
        data.update(overrides)
        return Event.objects.create(**data)

    def test_create_event_with_valid_data(self):
        self.client.force_login(self.support)

        response = self.client.post(reverse("event_create"), self.event_data())

        event = Event.objects.get(title="Audiencia Publica")
        self.assertRedirects(response, reverse("event_detail", args=[event.id]))
        self.assertEqual(event.location, "Camara Municipal")
        self.assertEqual(event.created_by, self.support)
        self.assertEqual(event.requester, self.support)
        self.assertIsNone(event.responsible_technician)
        self.assertEqual(event.status, Event.Status.PENDING)
        self.assertEqual(event.priority, Event.Priority.MEDIUM)

    def test_regular_user_can_create_event(self):
        self.client.force_login(self.requester)

        response = self.client.post(reverse("event_create"), self.event_data())

        event = Event.objects.get(title="Audiencia Publica")
        self.assertRedirects(response, reverse("event_detail", args=[event.id]))
        self.assertEqual(event.created_by, self.requester)
        self.assertEqual(event.requester, self.requester)
        self.assertIsNone(event.responsible_technician)
        self.assertEqual(event.status, Event.Status.PENDING)
        self.assertEqual(event.priority, Event.Priority.MEDIUM)

    def test_create_form_hides_system_defined_fields(self):
        self.client.force_login(self.support)

        response = self.client.get(reverse("event_create"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="status"')
        self.assertNotContains(response, 'name="priority"')
        self.assertNotContains(response, 'name="requester"')
        self.assertNotContains(response, 'name="responsible_technician"')
        self.assertContains(response, "Definicoes iniciais")

    def test_create_form_prefills_date_from_calendar_query(self):
        self.client.force_login(self.support)

        response = self.client.get(reverse("event_create"), {"date": "2026-07-20"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="event_date"')
        self.assertContains(response, 'value="2026-07-20"')

    def test_event_requires_date(self):
        event = self.create_event()
        event.event_date = None

        with self.assertRaises(ValidationError):
            event.full_clean()

    def test_event_requires_start_and_end_time(self):
        event = self.create_event()
        event.start_time = None

        with self.assertRaises(ValidationError):
            event.full_clean()

        event.start_time = time(9, 0)
        event.end_time = None

        with self.assertRaises(ValidationError):
            event.full_clean()

    def test_event_requires_location(self):
        event = self.create_event()
        event.location = ""

        with self.assertRaises(ValidationError):
            event.full_clean()

    def test_end_time_must_be_after_start_time(self):
        with self.assertRaises(ValidationError):
            self.create_event(end_time=time(9, 0))

    def test_estimated_people_must_be_positive_when_informed(self):
        with self.assertRaises(ValidationError):
            self.create_event(estimated_people=0)

    def test_event_appears_in_calendar_and_api(self):
        event = self.create_event()
        self.client.force_login(self.support)

        response = self.client.get(reverse("events"), {"month": "2026-07"})

        self.assertContains(response, event.title)
        self.assertContains(response, event.location)
        self.assertContains(response, reverse("event_detail", args=[event.id]))

        api_response = self.client.get(reverse("events_api"), {"month": "2026-07"})
        self.assertEqual(api_response.status_code, 200)
        payload = api_response.json()
        self.assertEqual(payload[0]["title"], event.title)
        self.assertEqual(payload[0]["status_slug"], Event.Status.PLANNED)

    def test_regular_user_can_see_events_created_by_others(self):
        event = self.create_event()
        self.client.force_login(self.requester)

        response = self.client.get(reverse("events"), {"month": "2026-07"})
        detail_response = self.client.get(reverse("event_detail", args=[event.id]))
        api_response = self.client.get(reverse("events_api"), {"month": "2026-07"})

        self.assertContains(response, event.title)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(api_response.json()[0]["title"], event.title)

    def test_regular_user_does_not_receive_manage_actions(self):
        event = self.create_event()
        self.client.force_login(self.requester)

        response = self.client.get(reverse("event_detail", args=[event.id]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("event_edit", args=[event.id]))
        self.assertNotContains(response, reverse("event_cancel", args=[event.id]))
        self.assertNotContains(response, reverse("event_complete", args=[event.id]))

    def test_cancelled_event_sets_timestamp_and_color(self):
        event = self.create_event()
        self.client.force_login(self.support)

        response = self.client.post(reverse("event_cancel", args=[event.id]))

        self.assertRedirects(response, reverse("event_detail", args=[event.id]))
        event.refresh_from_db()
        self.assertEqual(event.status, Event.Status.CANCELLED)
        self.assertIsNotNone(event.cancelled_at)

        calendar_response = self.client.get(reverse("events"), {"month": "2026-07"})
        self.assertContains(calendar_response, "event-status-cancelado")
        self.assertContains(calendar_response, "Cancelado")

    def test_completed_event_sets_timestamp_and_color(self):
        event = self.create_event()
        self.client.force_login(self.support)

        response = self.client.post(reverse("event_complete", args=[event.id]))

        self.assertRedirects(response, reverse("event_detail", args=[event.id]))
        event.refresh_from_db()
        self.assertEqual(event.status, Event.Status.COMPLETED)
        self.assertIsNotNone(event.completed_at)

        calendar_response = self.client.get(reverse("events"), {"month": "2026-07"})
        self.assertContains(calendar_response, "event-status-concluido")
        self.assertContains(calendar_response, "Concluido")

    def test_filter_by_status(self):
        planned = self.create_event(title="Evento Planejado", status=Event.Status.PLANNED)
        self.create_event(title="Evento Pendente", status=Event.Status.PENDING)
        self.client.force_login(self.support)

        response = self.client.get(
            reverse("events"),
            {"month": "2026-07", "status": Event.Status.PLANNED},
        )

        self.assertContains(response, planned.title)
        self.assertNotContains(response, "Evento Pendente")

    def test_calendar_event_link_points_to_detail(self):
        event = self.create_event()
        self.client.force_login(self.support)

        response = self.client.get(reverse("events"), {"month": "2026-07"})

        self.assertContains(response, f'href="{reverse("event_detail", args=[event.id])}"')

    def test_calendar_day_links_to_prefilled_create_form(self):
        self.client.force_login(self.requester)

        response = self.client.get(reverse("events"), {"month": "2026-07"})

        create_url = f"{reverse('event_create')}?date=2026-07-15"
        self.assertContains(response, f'href="{create_url}"')
        self.assertContains(response, f'data-event-create-url="{create_url}"')
