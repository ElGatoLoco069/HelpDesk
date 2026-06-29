"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import AccountsView, SettingsView, logout_view
from home.views import HomeView
from ticket.views import TicketDetailView, TicketEditView, TicketView, AddMessage, AddTicketAttachment
from registers.views import CategoryView, get_subcategories
from notifications.views import (
    mark_browser_notification_displayed,
    mark_browser_notification_read,
    mark_notifications_read,
    notifications_events,
    notifications_snapshot,
    pending_browser_notifications,
)
from signature.views import SignatureView
from approval_flow.views import ApprovalDecisionView, RequestApprovalView


urlpatterns = [
    path('admin/', admin.site.urls),
    path("", AccountsView.as_view(), name="account"),
    path("account/logout/", logout_view, name="logout"),
    path("settings/", SettingsView.as_view(), name="settings"),
    path("home/", HomeView.as_view(), name="home"),
    path("registers/new_ticket/", TicketView.as_view(), name="new_ticket"),
    path("tickets/<int:ticket_id>/", TicketDetailView.as_view(), name="ticket_detail"),
    path("tickets/<int:ticket_id>/edit/", TicketEditView.as_view(), name="ticket_edit"),
    path("tickets/<int:ticket_id>/attachments/", AddTicketAttachment.as_view(), name="add_ticket_attachment"),
    path("tickets/add_message/", AddMessage.as_view(), name="add_message"),
    path("registers/categories/", CategoryView.as_view(), name="categories"),
    path("registers/singnature/new_singnature/", SignatureView.as_view(), name="new_signature"),
    path("subcategories/<int:category_id>/", get_subcategories, name="get_subcategories"),
    path("mark-read/", mark_notifications_read, name="mark_notifications_read"),
    path("notifications/snapshot/", notifications_snapshot, name="notifications_snapshot"),
    path("notifications/events/", notifications_events, name="notifications_events"),
    path(
        "notifications/browser/pending/",
        pending_browser_notifications,
        name="pending_browser_notifications",
    ),
    path(
        "notifications/browser/<int:notification_id>/displayed/",
        mark_browser_notification_displayed,
        name="mark_browser_notification_displayed",
    ),
    path(
        "notifications/browser/<int:notification_id>/read/",
        mark_browser_notification_read,
        name="mark_browser_notification_read",
    ),
    path("settings/update_dashboard/", SettingsView.as_view(), name="update_dashboard"),
    path("approval/request/", RequestApprovalView.as_view(), name="request_approval"),
    path("approval/<int:approval_id>/decision/", ApprovalDecisionView.as_view(), name="approval_decision"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
