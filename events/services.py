import calendar
from collections import defaultdict
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile

from .models import Event


MONTH_NAMES = [
    "",
    "Janeiro",
    "Fevereiro",
    "Marco",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
]

EVENT_NOTIFICATION_TRIGGERS = (
    "event_tomorrow",
    "event_in_one_hour",
    "event_without_technician",
    "event_preparing",
    "event_cancelled",
    "event_completed",
)


def is_support_user(user):
    if not user.is_authenticated:
        return False

    try:
        return user.is_superuser or user.profile.is_support
    except Profile.DoesNotExist:
        return user.is_superuser


def can_manage_events(user):
    if not user.is_authenticated:
        return False

    return is_support_user(user) or user.has_perm("events.manage_events")


def can_create_events(user):
    return user.is_authenticated


def can_access_event(user, event):
    return user.is_authenticated


def get_accessible_events(user):
    queryset = Event.objects.select_related(
        "requester",
        "responsible_technician",
        "created_by",
        "related_ticket",
    )

    if not user.is_authenticated:
        return queryset.none()

    return queryset


def parse_month(month_value):
    today = timezone.localdate()

    if not month_value:
        return today.replace(day=1)

    try:
        year, month = [int(part) for part in month_value.split("-", 1)]
        return date(year, month, 1)
    except (TypeError, ValueError):
        return today.replace(day=1)


def month_bounds(month_date):
    last_day = calendar.monthrange(month_date.year, month_date.month)[1]
    first_day = month_date.replace(day=1)
    last_date = month_date.replace(day=last_day)
    return first_day, last_date


def shift_month(month_date, offset):
    month_index = month_date.month - 1 + offset
    year = month_date.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def format_month_value(month_date):
    return month_date.strftime("%Y-%m")


def format_month_label(month_date):
    return f"{MONTH_NAMES[month_date.month]} {month_date.year}"


def apply_event_filters(queryset, params):
    status = params.get("status") or ""
    technician = params.get("technician") or ""
    location = (params.get("location") or "").strip()
    priority = params.get("priority") or ""

    valid_statuses = {choice.value for choice in Event.Status}
    valid_priorities = {choice.value for choice in Event.Priority}

    if status in valid_statuses:
        queryset = queryset.filter(status=status)

    if technician.isdigit():
        queryset = queryset.filter(responsible_technician_id=technician)

    if location:
        queryset = queryset.filter(location__icontains=location)

    if priority in valid_priorities:
        queryset = queryset.filter(priority=priority)

    if params.get("future_only") == "on":
        queryset = queryset.filter(event_date__gte=timezone.localdate())

    if params.get("pending_only") == "on":
        queryset = queryset.filter(status=Event.Status.PENDING)

    return queryset


def build_month_calendar(events, month_date):
    events_by_day = defaultdict(list)

    for event in events:
        events_by_day[event.event_date].append(event)

    today = timezone.localdate()
    calendar_weeks = []
    month_calendar = calendar.Calendar(firstweekday=calendar.SUNDAY)

    for week in month_calendar.monthdatescalendar(month_date.year, month_date.month):
        calendar_weeks.append([
            {
                "date": day,
                "in_month": day.month == month_date.month,
                "is_today": day == today,
                "events": events_by_day.get(day, []),
            }
            for day in week
        ])

    return calendar_weeks


def get_month_indicators(month_queryset):
    counters = month_queryset.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status=Event.Status.PENDING)),
        planned=Count("id", filter=Q(status=Event.Status.PLANNED)),
        preparing=Count("id", filter=Q(status=Event.Status.PREPARING)),
        completed=Count("id", filter=Q(status=Event.Status.COMPLETED)),
        cancelled=Count("id", filter=Q(status=Event.Status.CANCELLED)),
    )

    return {key: value or 0 for key, value in counters.items()}


def get_support_technicians():
    return User.objects.filter(
        is_active=True,
        profile__is_support=True,
    ).order_by("first_name", "last_name", "username")


def serialize_event(event):
    technician = ""

    if event.responsible_technician:
        technician = (
            event.responsible_technician.get_full_name()
            or event.responsible_technician.username
        )

    return {
        "id": event.id,
        "title": event.title,
        "event_date": event.event_date.isoformat(),
        "start_time": event.start_time.strftime("%H:%M"),
        "end_time": event.end_time.strftime("%H:%M"),
        "location": event.location,
        "status": event.get_status_display(),
        "status_slug": event.status_slug,
        "priority": event.get_priority_display(),
        "priority_slug": event.priority_slug,
        "technician": technician,
        "url": reverse("event_detail", args=[event.id]),
    }


def cancel_event(event):
    event.status = Event.Status.CANCELLED
    event.save(update_fields=["status", "updated_at"])
    return event


def complete_event(event):
    event.status = Event.Status.COMPLETED
    event.save(update_fields=["status", "updated_at"])
    return event


def get_events_pending_notification_review(reference=None):
    reference = reference or timezone.now()
    tomorrow = reference.date() + timedelta(days=1)
    in_one_hour = reference + timedelta(hours=1)

    return {
        "event_tomorrow": Event.objects.filter(event_date=tomorrow),
        "event_in_one_hour": Event.objects.filter(
            event_date=reference.date(),
            start_time__hour=in_one_hour.hour,
        ),
        "event_without_technician": Event.objects.filter(
            responsible_technician__isnull=True,
            status__in=[
                Event.Status.PENDING,
                Event.Status.PLANNED,
                Event.Status.PREPARING,
            ],
        ),
    }
