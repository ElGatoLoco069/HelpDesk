from django.urls import path

from .views import (
    EventApiView,
    EventCalendarView,
    EventCancelView,
    EventCompleteView,
    EventCreateView,
    EventDetailView,
    EventEditView,
)


urlpatterns = [
    path("", EventCalendarView.as_view(), name="events"),
    path("create/", EventCreateView.as_view(), name="event_create"),
    path("api/", EventApiView.as_view(), name="events_api"),
    path("<int:event_id>/", EventDetailView.as_view(), name="event_detail"),
    path("<int:event_id>/edit/", EventEditView.as_view(), name="event_edit"),
    path("<int:event_id>/cancel/", EventCancelView.as_view(), name="event_cancel"),
    path("<int:event_id>/complete/", EventCompleteView.as_view(), name="event_complete"),
]
