from django import forms
from django.contrib.auth.models import User

from ticket.models import Ticket

from .models import Event


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "event_date",
            "start_time",
            "end_time",
            "location",
            "requester",
            "responsible_technician",
            "status",
            "priority",
            "estimated_people",
            "required_resources",
            "needs_onsite_support",
            "needs_live_stream",
            "technical_notes",
            "related_ticket",
        ]
        widgets = {
            "event_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "start_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "end_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "description": forms.Textarea(attrs={"rows": 5}),
            "required_resources": forms.Textarea(attrs={"rows": 5}),
            "technical_notes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields["event_date"].input_formats = ["%Y-%m-%d"]
        self.fields["start_time"].input_formats = ["%H:%M", "%H:%M:%S"]
        self.fields["end_time"].input_formats = ["%H:%M", "%H:%M:%S"]

        active_users = User.objects.filter(is_active=True).order_by(
            "first_name",
            "last_name",
            "username",
        )
        support_users = active_users.filter(profile__is_support=True)

        if "requester" in self.fields:
            self.fields["requester"].queryset = active_users
            self.fields["requester"].empty_label = "Selecione o solicitante"

        if "responsible_technician" in self.fields:
            self.fields["responsible_technician"].queryset = support_users
            self.fields["responsible_technician"].empty_label = "Sem tecnico responsavel"

        if "related_ticket" in self.fields:
            self.fields["related_ticket"].queryset = (
                Ticket.objects
                .select_related("title", "created_by")
                .order_by("-created_at")
            )
            self.fields["related_ticket"].empty_label = "Sem chamado vinculado"

        labels = {
            "title": "Titulo",
            "description": "Descricao",
            "event_date": "Data do evento",
            "start_time": "Horario de inicio",
            "end_time": "Horario de termino",
            "location": "Local",
            "requester": "Solicitante",
            "responsible_technician": "Tecnico responsavel",
            "status": "Status",
            "priority": "Prioridade",
            "estimated_people": "Quantidade estimada de pessoas",
            "required_resources": "Recursos necessarios",
            "needs_onsite_support": "Precisa de suporte presencial",
            "needs_live_stream": "Precisa de transmissao ao vivo",
            "technical_notes": "Observacoes tecnicas",
            "related_ticket": "Chamado vinculado",
        }

        for field_name, label in labels.items():
            if field_name not in self.fields:
                continue
            self.fields[field_name].label = label

        for field_name in [
            "title",
            "event_date",
            "start_time",
            "end_time",
            "location",
            "requester",
            "status",
        ]:
            if field_name in self.fields:
                self.fields[field_name].required = True

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if start_time and end_time and end_time <= start_time:
            self.add_error(
                "end_time",
                "O horario de termino deve ser maior que o horario de inicio.",
            )

        estimated_people = cleaned_data.get("estimated_people")

        if estimated_people is not None and estimated_people <= 0:
            self.add_error(
                "estimated_people",
                "A quantidade estimada de pessoas deve ser positiva.",
            )

        return cleaned_data


class EventCreateForm(EventForm):
    class Meta(EventForm.Meta):
        fields = [
            "title",
            "description",
            "event_date",
            "start_time",
            "end_time",
            "location",
            "estimated_people",
            "required_resources",
            "needs_onsite_support",
            "needs_live_stream",
            "technical_notes",
            "related_ticket",
        ]
