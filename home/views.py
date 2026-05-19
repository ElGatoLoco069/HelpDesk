from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render

from ticket.models import Ticket, Ticket_Status
from registers.models import Priority

from django.views.generic import View
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta

# Create your views here.

@method_decorator(login_required(login_url="/"), name="dispatch")
class HomeView(View):
    
    def get(self, request):

        search = (request.GET.get("search") or "").strip()
        status_filter = request.GET.get("status") or ""
        priority_filter = request.GET.get("priority") or ""

        if status_filter and not status_filter.isdigit():
            status_filter = ""

        if priority_filter and not priority_filter.isdigit():
            priority_filter = ""

        status = list(Ticket_Status.objects.filter(status=True).order_by("id"))
        prioritys = list(Priority.objects.filter(status=True).order_by("id"))

        done_status = next((item for item in status if item.name.lower() == "concluido"), None)
        in_service_status = next((item for item in status if item.name.lower() == "em andamento"), None)
        waiting_status = next((item for item in status if item.name.lower() == "aguardando"), None)
        high_priority = next((item for item in prioritys if item.name.lower() == "alta"), None)

        base_tickets = Ticket.objects.select_related(
            "title",
            "title__category",
            "priority",
            "status",
            "created_by",
            "assigned_to",
        )

        active_tickets = base_tickets
        if done_status:
            active_tickets = active_tickets.exclude(status=done_status)

        if request.user.profile.is_support:
            active_tickets = base_tickets
        else:
            active_tickets = base_tickets.filter(created_by=request.user)

        tickets = active_tickets

        if search:
            tickets = tickets.filter(
                Q(hash__icontains=search) |
                Q(title__name__icontains=search) |
                Q(created_by__first_name__icontains=search) |
                Q(created_by__last_name__icontains=search)
            )

        if status_filter:
            tickets = tickets.filter(status_id=status_filter)

        if priority_filter:
            tickets = tickets.filter(priority_id=priority_filter)

        tickets = tickets.order_by("-created_at")[:50]
        attention_tickets = active_tickets.filter(priority=high_priority).order_by("-updated_at")[:5] if high_priority else []

        hoje = timezone.now().date()
        stale_limit = timezone.now() - timedelta(hours=24)
        counters = active_tickets.aggregate(
            open_tickets=Count("id"),
            in_service=Count("id", filter=Q(status=in_service_status)) if in_service_status else Count("id", filter=Q(id__isnull=True)),
            waiting=Count("id", filter=Q(status=waiting_status)) if waiting_status else Count("id", filter=Q(id__isnull=True)),
            critical=Count("id", filter=Q(priority=high_priority)) if high_priority else Count("id", filter=Q(id__isnull=True)),
            open_today=Count("id", filter=Q(created_at__date=hoje)),
            stale_waiting=Count("id", filter=Q(status=waiting_status, updated_at__lt=stale_limit)) if waiting_status else Count("id", filter=Q(id__isnull=True)),
        )

        open_tickets = counters["open_tickets"]
        in_service = counters["in_service"]
        waiting = counters["waiting"]
        critical = counters["critical"]
        open_today = counters["open_today"]
        stale_waiting = counters["stale_waiting"]
        status_counts = dict(
            active_tickets.values("status_id").annotate(total=Count("id")).values_list("status_id", "total")
        )
        status_summary = []

        for status_item in status:
            count = status_counts.get(status_item.id, 0)
            percent = 0
            if open_tickets:
                percent = round((count / open_tickets) * 100)

            status_summary.append({
                "name": status_item.name,
                "count": count,
                "percent": percent,
            })
        
        return render(
            request, 
            "home.html",
            {
                "active_page": "home",
                "tickets": tickets,
                "open_tickets":open_tickets,
                "open_today":open_today,
                "in_service":in_service,
                "waiting":waiting,
                "critical":critical,
                "stale_waiting": stale_waiting,
                "status_summary": status_summary,
                "attention_tickets": attention_tickets,
                "prioritys":prioritys,
                "status":status,
                "filters": {
                    "search": search,
                    "status": status_filter,
                    "priority": priority_filter,
                },
            }
            )
