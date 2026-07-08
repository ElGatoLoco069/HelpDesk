(function () {
    const calendar = document.querySelector("[data-events-calendar]");
    const drawer = document.querySelector("[data-event-drawer]");

    if (!calendar || !drawer) {
        return;
    }

    const closeButtons = drawer.querySelectorAll("[data-event-drawer-close]");
    const fields = {
        title: drawer.querySelector("[data-event-drawer-title]"),
        date: drawer.querySelector("[data-event-drawer-date]"),
        time: drawer.querySelector("[data-event-drawer-time]"),
        location: drawer.querySelector("[data-event-drawer-location]"),
        status: drawer.querySelector("[data-event-drawer-status]"),
        priority: drawer.querySelector("[data-event-drawer-priority]"),
        technician: drawer.querySelector("[data-event-drawer-technician]"),
        url: drawer.querySelector("[data-event-drawer-url]"),
    };

    const eventsById = new Map();

    function formatDate(value) {
        const date = new Date(`${value}T00:00:00`);
        return date.toLocaleDateString("pt-BR", {
            weekday: "long",
            day: "2-digit",
            month: "long",
            year: "numeric",
        });
    }

    function openDrawer(eventData) {
        fields.title.textContent = eventData.title;
        fields.date.textContent = formatDate(eventData.event_date);
        fields.time.textContent = `${eventData.start_time} - ${eventData.end_time}`;
        fields.location.textContent = eventData.location;
        fields.status.textContent = eventData.status;
        fields.priority.textContent = eventData.priority;
        fields.technician.textContent = eventData.technician || "Sem tecnico responsavel";
        fields.url.href = eventData.url;
        drawer.hidden = false;
        drawer.classList.add("active");
    }

    function closeDrawer() {
        drawer.classList.remove("active");
        window.setTimeout(() => {
            drawer.hidden = true;
        }, 180);
    }

    closeButtons.forEach((button) => {
        button.addEventListener("click", closeDrawer);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !drawer.hidden) {
            closeDrawer();
        }
    });

    fetch(calendar.dataset.apiUrl, {
        credentials: "same-origin",
        headers: {
            "X-Requested-With": "XMLHttpRequest",
        },
    })
        .then((response) => response.json())
        .then((events) => {
            events.forEach((eventData) => {
                eventsById.set(String(eventData.id), eventData);
            });
        })
        .catch((error) => {
            console.error("Erro ao carregar eventos do calendario:", error);
        });

    calendar.addEventListener("click", (event) => {
        const card = event.target.closest("[data-event-id]");

        if (!card || event.ctrlKey || event.metaKey || event.shiftKey) {
            const day = event.target.closest("[data-event-create-url]");
            const interactiveElement = event.target.closest(
                "a, button, input, select, textarea, label"
            );

            if (
                day &&
                !interactiveElement &&
                !event.ctrlKey &&
                !event.metaKey &&
                !event.shiftKey
            ) {
                window.location.href = day.dataset.eventCreateUrl;
            }

            return;
        }

        const eventData = eventsById.get(card.dataset.eventId);

        if (!eventData) {
            return;
        }

        event.preventDefault();
        openDrawer(eventData);
    });
})();
