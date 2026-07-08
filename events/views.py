from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import View

from accounts.models import UserPreferences
from .forms import EventCreateForm, EventForm
from .models import Event
from .services import (
    apply_event_filters,
    build_month_calendar,
    can_access_event,
    can_create_events,
    can_manage_events,
    cancel_event,
    complete_event,
    format_month_label,
    format_month_value,
    get_accessible_events,
    get_month_indicators,
    get_support_technicians,
    month_bounds,
    parse_month,
    serialize_event,
    shift_month,
)

def parse_iso_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


@method_decorator(login_required(login_url="/"), name="dispatch")
class EventCalendarView(View):
    def get(self, request):

        preferences, _ = UserPreferences.objects.get_or_create(user=request.user)

        month_date = parse_month(request.GET.get("month"))
        month_start, month_end = month_bounds(month_date)
        month_value = format_month_value(month_date)

        accessible_events = get_accessible_events(request.user)
        month_queryset = accessible_events.filter(
            event_date__gte=month_start,
            event_date__lte=month_end,
        )
        filtered_month_events = apply_event_filters(
            month_queryset,
            request.GET,
        ).order_by("event_date", "start_time", "title")
        filtered_month_count = filtered_month_events.count()

        upcoming_events = apply_event_filters(
            accessible_events,
            request.GET,
        ).filter(
            event_date__gte=timezone.localdate(),
        ).order_by("event_date", "start_time")[:8]

        query = request.GET.copy()
        query["month"] = month_value
        api_querystring = query.urlencode()

        def query_for(month):
            month_query = request.GET.copy()
            month_query["month"] = format_month_value(month)
            return month_query.urlencode()

        locations = (
            accessible_events
            .exclude(location="")
            .values_list("location", flat=True)
            .distinct()
            .order_by("location")[:100]
        )

        context = {
            "active_page": "events",
            "calendar_weeks": build_month_calendar(filtered_month_events, month_date),
            "indicators": get_month_indicators(month_queryset),
            "filtered_month_count": filtered_month_count,
            "upcoming_events": upcoming_events,
            "status_choices": Event.Status.choices,
            "priority_choices": Event.Priority.choices,
            "technicians": get_support_technicians(),
            "locations": locations,
            "filters": {
                "month": month_value,
                "status": request.GET.get("status", ""),
                "technician": request.GET.get("technician", ""),
                "location": request.GET.get("location", ""),
                "priority": request.GET.get("priority", ""),
                "future_only": request.GET.get("future_only") == "on",
                "pending_only": request.GET.get("pending_only") == "on",
            },
            "month_label": format_month_label(month_date),
            "month_value": month_value,
            "prev_month_query": query_for(shift_month(month_date, -1)),
            "next_month_query": query_for(shift_month(month_date, 1)),
            "today_query": query_for(timezone.localdate().replace(day=1)),
            "api_querystring": api_querystring,
            "can_create_events": can_create_events(request.user),
            "can_manage_events": can_manage_events(request.user),
            "preferences":preferences,
        }

        return render(request, "events/event_calendar.html", context)


@method_decorator(login_required(login_url="/"), name="dispatch")
class EventCreateView(View):
    def get(self, request):
        if not can_create_events(request.user):
            messages.warning(request, "Apenas usuarios autenticados podem criar eventos.")
            return redirect("events")

        initial = {}
        selected_date = parse_iso_date(request.GET.get("date"))

        if selected_date:
            initial["event_date"] = selected_date

        form = EventCreateForm(user=request.user, initial=initial)
        return render(
            request,
            "events/event_form.html",
            {
                "active_page": "events",
                "form": form,
                "form_title": "Novo Evento",
                "is_create": True,
                "system_defaults": self.get_system_defaults(request),
                "submit_label": "Criar evento",
            },
        )

    def post(self, request):
        if not can_create_events(request.user):
            messages.warning(request, "Apenas usuarios autenticados podem criar eventos.")
            return redirect("events")

        form = EventCreateForm(request.POST, user=request.user)

        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.requester = request.user
            event.responsible_technician = None
            event.status = Event.Status.PENDING
            event.priority = Event.Priority.MEDIUM
            event.save()
            messages.success(request, "Evento criado com sucesso!")
            return redirect("event_detail", event_id=event.id)

        messages.warning(request, "Revise os campos obrigatorios do evento.")
        return render(
            request,
            "events/event_form.html",
            {
                "active_page": "events",
                "form": form,
                "form_title": "Novo Evento",
                "is_create": True,
                "system_defaults": self.get_system_defaults(request),
                "submit_label": "Criar evento",
            },
        )

    def get_system_defaults(self, request):
        return {
            "requester": request.user.get_full_name() or request.user.username,
            "status": Event.Status.PENDING.label,
            "priority": Event.Priority.MEDIUM.label,
            "technician": "Definido posteriormente",
        }


@method_decorator(login_required(login_url="/"), name="dispatch")
class EventDetailView(View):
    def get(self, request, event_id):
        event = get_object_or_404(
            Event.objects.select_related(
                "requester",
                "responsible_technician",
                "created_by",
                "related_ticket",
            ),
            id=event_id,
        )

        if not can_access_event(request.user, event):
            messages.warning(request, "Voce nao tem permissao para acessar este evento.")
            return redirect("events")

        return render(
            request,
            "events/event_detail.html",
            {
                "active_page": "events",
                "event": event,
                "can_manage_events": can_manage_events(request.user),
            },
        )


@method_decorator(login_required(login_url="/"), name="dispatch")
class EventEditView(View):
    def get(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)

        if not can_manage_events(request.user):
            messages.warning(request, "Apenas usuarios autorizados podem editar eventos.")
            return redirect("event_detail", event_id=event.id)

        form = EventForm(instance=event, user=request.user)
        return render(
            request,
            "events/event_form.html",
            {
                "active_page": "events",
                "event": event,
                "form": form,
                "form_title": "Editar Evento",
                "submit_label": "Salvar alteracoes",
            },
        )

    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)

        if not can_manage_events(request.user):
            messages.warning(request, "Apenas usuarios autorizados podem editar eventos.")
            return redirect("event_detail", event_id=event.id)

        form = EventForm(request.POST, instance=event, user=request.user)

        if form.is_valid():
            event = form.save()
            messages.success(request, "Evento atualizado com sucesso!")
            return redirect("event_detail", event_id=event.id)

        messages.warning(request, "Revise os campos obrigatorios do evento.")
        return render(
            request,
            "events/event_form.html",
            {
                "active_page": "events",
                "event": event,
                "form": form,
                "form_title": "Editar Evento",
                "submit_label": "Salvar alteracoes",
            },
        )


@method_decorator(login_required(login_url="/"), name="dispatch")
class EventCancelView(View):
    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)

        if not can_manage_events(request.user):
            messages.warning(request, "Apenas usuarios autorizados podem cancelar eventos.")
            return redirect("event_detail", event_id=event.id)

        cancel_event(event)
        messages.success(request, "Evento cancelado com sucesso!")
        return redirect("event_detail", event_id=event.id)

    def get(self, request, event_id):
        return redirect("event_detail", event_id=event_id)


@method_decorator(login_required(login_url="/"), name="dispatch")
class EventCompleteView(View):
    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)

        if not can_manage_events(request.user):
            messages.warning(request, "Apenas usuarios autorizados podem concluir eventos.")
            return redirect("event_detail", event_id=event.id)

        complete_event(event)
        messages.success(request, "Evento concluido com sucesso!")
        return redirect("event_detail", event_id=event.id)

    def get(self, request, event_id):
        return redirect("event_detail", event_id=event_id)


@method_decorator(login_required(login_url="/"), name="dispatch")
class EventApiView(View):
    def get(self, request):
        queryset = apply_event_filters(
            get_accessible_events(request.user),
            request.GET,
        )

        start_date = parse_iso_date(request.GET.get("start"))
        end_date = parse_iso_date(request.GET.get("end"))

        if start_date and end_date:
            queryset = queryset.filter(event_date__gte=start_date, event_date__lte=end_date)
        elif request.GET.get("month"):
            month_date = parse_month(request.GET.get("month"))
            month_start, month_end = month_bounds(month_date)
            queryset = queryset.filter(event_date__gte=month_start, event_date__lte=month_end)

        queryset = queryset.order_by("event_date", "start_time", "title")[:500]

        return JsonResponse(
            [serialize_event(event) for event in queryset],
            safe=False,
        )
