from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render
from django.views.generic import View
from datetime import timedelta
from django.utils import timezone
from accounts.models import Profile
from ticket.models import Ticket
from system.models import SystemSettings


def is_under_maintenance(request):
    settings = SystemSettings.objects.first()

    if settings and settings.status == "maintenance":
        return render(request, "maintenance.html")

    return None


@method_decorator(login_required(login_url="/"), name="dispatch")
class SystemView(View):

    def get(self, request):
        online_users = Profile.objects.filter(
            last_activity__gte=timezone.now() - timedelta(minutes=5)
        )

        total_online = online_users.count()
        total_tickets = Ticket.objects.count()

        return render(
            request,
            "maintenance_center.html",
            {
                "active_page": "maintenance_center",
                "online_users": total_online,
                "total_tickets": total_tickets,
            }
        )