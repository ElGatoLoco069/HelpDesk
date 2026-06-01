from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.contrib.auth.models import User

from ticket.models import Ticket, Ticket_Status
from registers.models import Priority

from django.views.generic import View
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta

from accounts.models import UserPreferences

@method_decorator(login_required(login_url="/"), name="dispatch")
class HomeView(View):

    def get(self, request):

        preferences = UserPreferences.objects.get(user=request.user)
        search = (request.GET.get("search") or "").strip()
        status_filter = request.GET.get("status") or ""
        priority_filter = request.GET.get("priority") or ""
        tecnico_filter = request.GET.get("tecnico") or ""

        # =========================
        # VALIDAÇÃO DOS FILTROS
        # =========================
        if status_filter and not status_filter.isdigit():
            status_filter = ""

        if priority_filter and not priority_filter.isdigit():
            priority_filter = ""

        if tecnico_filter and not tecnico_filter.isdigit():
            tecnico_filter = ""

        # =========================
        # DADOS AUXILIARES
        # =========================
        status = list(
            Ticket_Status.objects.filter(
                status=True
            ).order_by("id")
        )

        prioritys = list(
            Priority.objects.filter(
                status=True
            ).order_by("id")
        )

        done_status = next(
            (
                item for item in status
                if item.name.lower() == "concluido"
            ),
            None
        )

        in_service_status = next(
            (
                item for item in status
                if item.name.lower() == "em andamento"
            ),
            None
        )

        waiting_status = next(
            (
                item for item in status
                if item.name.lower() == "aguardando"
            ),
            None
        )

        high_priority = next(
            (
                item for item in prioritys
                if item.name.lower() == "alta"
            ),
            None
        )

        # =========================
        # QUERY BASE
        # =========================
        base_tickets = Ticket.objects.select_related(
            "title",
            "title__category",
            "priority",
            "status",
            "created_by",
            "created_by__profile",
            "assigned_to",
            "assigned_to__profile",
        )

        # =========================
        # QUERY DOS INDICADORES
        # =========================
        dashboard_tickets = base_tickets

        # Usuário comum vê apenas os próprios chamados
        if not request.user.profile.is_support:
            dashboard_tickets = dashboard_tickets.filter(
                created_by=request.user
            )

        # Remove concluídos do dashboard
        if done_status:
            dashboard_tickets = dashboard_tickets.exclude(
                status=done_status
            )

        # =========================
        # QUERY DA LISTAGEM
        # =========================
        tickets = dashboard_tickets

        # Se usuário filtrar concluídos,
        # utiliza base original
        if (
            done_status and
            status_filter and
            int(status_filter) == done_status.id
        ):

            tickets = base_tickets

            if not request.user.profile.is_support:
                tickets = tickets.filter(
                    created_by=request.user
                )

        # =========================
        # BUSCA TEXTUAL
        # =========================
        if search:
            tickets = tickets.filter(
                Q(hash__icontains=search) |
                Q(title__name__icontains=search) |
                Q(created_by__first_name__icontains=search) |
                Q(created_by__last_name__icontains=search)
            )

        # =========================
        # FILTRO STATUS
        # =========================
        if status_filter:
            tickets = tickets.filter(
                status_id=status_filter
            )

        # =========================
        # FILTRO PRIORIDADE
        # =========================
        if priority_filter:
            tickets = tickets.filter(
                priority_id=priority_filter
            )

        # =========================
        # FILTRO TÉCNICO
        # =========================
        if tecnico_filter:
            tickets = tickets.filter(
                assigned_to__id=tecnico_filter
            )

        # =========================
        # ORDENAÇÃO
        # =========================
        tickets = tickets.order_by(
            "-created_at"
        )[:50]

        if request.GET.get("partial") == "tickets":
            html = render_to_string(
                "partials/ticket_list_items.html",
                {"tickets": tickets},
                request=request
            )

            return JsonResponse({
                "success": True,
                "html": html,
            })

        # =========================
        # CHAMADOS DE ATENÇÃO
        # =========================
        attention_tickets = (
            dashboard_tickets
            .filter(priority=high_priority)
            .order_by("-updated_at")[:5]
            if high_priority else []
        )

        # =========================
        # MÉTRICAS
        # =========================
        hoje = timezone.now().date()

        stale_limit = (
            timezone.now() - timedelta(hours=24)
        )

        counters = dashboard_tickets.aggregate(

            open_tickets=Count("id"),

            in_service=Count(
                "id",
                filter=Q(status=in_service_status)
            ) if in_service_status else Count(
                "id",
                filter=Q(id__isnull=True)
            ),

            waiting=Count(
                "id",
                filter=Q(status=waiting_status)
            ) if waiting_status else Count(
                "id",
                filter=Q(id__isnull=True)
            ),

            critical=Count(
                "id",
                filter=Q(priority=high_priority)
            ) if high_priority else Count(
                "id",
                filter=Q(id__isnull=True)
            ),

            open_today=Count(
                "id",
                filter=Q(created_at__date=hoje)
            ),

            stale_waiting=Count(
                "id",
                filter=Q(
                    status=waiting_status,
                    updated_at__lt=stale_limit
                )
            ) if waiting_status else Count(
                "id",
                filter=Q(id__isnull=True)
            ),
        )

        open_tickets = counters["open_tickets"]
        in_service = counters["in_service"]
        waiting = counters["waiting"]
        critical = counters["critical"]
        open_today = counters["open_today"]
        stale_waiting = counters["stale_waiting"]

        # =========================
        # RESUMO POR STATUS
        # =========================
        status_counts = dict(
            dashboard_tickets
            .values("status_id")
            .annotate(total=Count("id"))
            .values_list("status_id", "total")
        )

        status_summary = []

        for status_item in status:

            count = status_counts.get(
                status_item.id,
                0
            )

            percent = 0

            if open_tickets:
                percent = round(
                    (count / open_tickets) * 100
                )

            status_summary.append({
                "name": status_item.name,
                "count": count,
                "percent": percent,
            })

        # =========================
        # TÉCNICOS
        # =========================
        tecnicos = User.objects.filter(
            profile__is_support=True
        ).order_by(
            "first_name",
            "last_name"
        )

        context = {
                "preferences": preferences,
                "active_page": "home",

                "tickets": tickets,

                "open_tickets": open_tickets,
                "open_today": open_today,
                "in_service": in_service,
                "waiting": waiting,
                "critical": critical,
                "stale_waiting": stale_waiting,

                "status_summary": status_summary,
                "attention_tickets": attention_tickets,

                "prioritys": prioritys,
                "status": status,
                "tecnicos": tecnicos,

                "filters": {
                    "search": search,
                    "status": status_filter,
                    "priority": priority_filter,
                    "tecnico": tecnico_filter,
                },
            }

        # =========================
        # RENDER
        # =========================
        return render(
            request,
            "home.html",
            context
        )
        
