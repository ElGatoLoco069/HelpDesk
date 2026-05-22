// ================================
// SIDEBAR TOGGLE
// ================================

const sidebar = document.querySelector(".sidebar");
const sidebarToggleBtn = document.querySelectorAll(".sidebar-toggle");

sidebarToggleBtn.forEach(btn => {

    btn.addEventListener("click", () => {

        sidebar.classList.toggle("collapsed");

    });

});


// ================================
// THEME TOGGLE
// ================================

const themeToggleBtn = document.querySelector(".theme-toggle");
const modeText = document.querySelector(".theme-text");
const modeIcon = document.querySelector(".theme-icon");

// Recupera tema salvo
const isDarkMode = localStorage.getItem("darkMode") === "true";

/**
 * Aplica tema claro/escuro
 * @param {boolean} dark
 */
function applyTheme(dark) {

    if (dark) {

        document.documentElement.classList.add("dark");

        if (modeText) {
            modeText.innerText = "Dark Mode";
        }

        if (modeIcon) {

            modeIcon.classList.remove("fa-sun");
            modeIcon.classList.add("fa-moon");

        }

    } else {

        document.documentElement.classList.remove("dark");

        if (modeText) {
            modeText.innerText = "Light Mode";
        }

        if (modeIcon) {

            modeIcon.classList.remove("fa-moon");
            modeIcon.classList.add("fa-sun");

        }

    }

}

// Aplica tema ao carregar
applyTheme(isDarkMode);

// Alternar tema
if (themeToggleBtn) {

    themeToggleBtn.addEventListener("click", () => {

        const isDark = document.documentElement.classList.toggle("dark");

        localStorage.setItem("darkMode", isDark);

        applyTheme(isDark);

    });

}


// ================================
// SIDEBAR DROPDOWN
// ================================

const dropdowns = document.querySelectorAll(".dropdown-toggle");

dropdowns.forEach(dropdown => {

    dropdown.addEventListener("click", (e) => {

        e.preventDefault();

        const parent = dropdown.closest(".has-dropdown");

        parent.classList.toggle("active");

    });

});


// ================================
// NOTIFICAÇÕES
// ================================

const notificationBtn = document.querySelector(".notification-btn");
const notificationModal = document.getElementById("notificationModal");
const notificationOverlay = document.querySelector(".notification-overlay");
const closeNotification = document.querySelector(".close-notification");
const notificationBody = document.getElementById("notificationBody");


function getBadge() {
    return document.querySelector(".badge");
}


function updateNotificationBadge(count) {

    if (!notificationBtn) return;

    let currentBadge = getBadge();

    if (count > 0 && !currentBadge) {

        currentBadge = document.createElement("span");
        currentBadge.classList.add("badge");
        notificationBtn.appendChild(currentBadge);

    }

    if (count > 0) {

        currentBadge.textContent = count;
        newNotification(count);

        if (markReadBtn) {
            markReadBtn.innerHTML = "Marcar todas como lidas";
            markReadBtn.disabled = false;
        }

        return;

    }

    currentBadge?.remove();
    notificationBtn.classList.remove("show-badge");

}


/**
 * Anima botão de notificação
 * @param {number|string} count
 */
function newNotification(count = 1) {

    const currentBadge = getBadge();

    if (!notificationBtn || !currentBadge) return;

    currentBadge.textContent = count;

    notificationBtn.classList.add("animate");

    setTimeout(() => {

        notificationBtn.classList.remove("animate");

        notificationBtn.classList.add("show-badge");

    }, 300);

}


/**
 * Abre modal
 */
function openNotificationModal() {

    if (!notificationModal) return;

    notificationModal.classList.add("active");

    document.body.style.overflow = "hidden";

    notificationBtn?.classList.remove("show-badge");

}


/**
 * Fecha modal
 */
function closeNotificationModal() {

    if (!notificationModal) return;

    notificationModal.classList.remove("active");

    document.body.style.overflow = "";

}


// ================================
// EVENTOS
// ================================

// Abrir modal
if (notificationBtn) {

    notificationBtn.addEventListener("click", openNotificationModal);

}


// Fechar modal
if (closeNotification) {

    closeNotification.addEventListener("click", closeNotificationModal);

}


// Fechar clicando overlay
if (notificationOverlay) {

    notificationOverlay.addEventListener("click", closeNotificationModal);

}


// Fechar com ESC
document.addEventListener("keydown", (e) => {

    if (e.key === "Escape") {

        closeNotificationModal();

    }

});


// ================================
// ANIMA BADGE APENAS SE EXISTIR
// ================================

if (getBadge()) {

    const totalNotifications = Number(getBadge().textContent.trim());

    if (totalNotifications > 0) {

        newNotification(totalNotifications);

    }

}

// ================================
// MARCAR NOTIFICAÇÕES COMO LIDAS
// ================================

const markReadBtn = document.getElementById("markReadBtn");

function getCSRFToken() {

    return document.querySelector('[name=csrfmiddlewaretoken]')?.value
        || getCookie("csrftoken");

}


/**
 * Recupera cookie
 */
function getCookie(name) {

    let cookieValue = null;

    if (document.cookie && document.cookie !== "") {

        const cookies = document.cookie.split(";");

        for (let cookie of cookies) {

            cookie = cookie.trim();

            if (cookie.startsWith(name + "=")) {

                cookieValue = decodeURIComponent(
                    cookie.substring(name.length + 1)
                );

                break;

            }

        }

    }

    return cookieValue;

}


if (markReadBtn) {

    markReadBtn.addEventListener("click", async () => {

        try {

            const url = markReadBtn.dataset.url;

            const response = await fetch(url, {

                method: "POST",
                credentials: "same-origin",
                headers: {
                    "X-CSRFToken": getCSRFToken(),
                    "Content-Type": "application/json"
                }

            });

            const data = await response.json();

            if (data.success) {

                // Remove destaque unread
                document.querySelectorAll(".notification-item.unread")
                    .forEach(item => {
                        item.classList.remove("unread");
                    });

                // Remove badge
                getBadge()?.remove();

                // Feedback visual
                markReadBtn.innerHTML = `
                    <i class="fas fa-check"></i>
                    Todas notificações lidas
                `;

                markReadBtn.disabled = true;

            }

        } catch (error) {

            console.error("Erro ao marcar notificações:", error);

        }

    });

}


// ================================
// ATUALIZAR NOTIFICAÇÕES
// ================================

async function refreshNotifications() {

    if (!notificationBody?.dataset.refreshUrl) return;

    try {

        const response = await fetch(notificationBody.dataset.refreshUrl, {
            credentials: "same-origin",
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }
        });

        const data = await response.json();

        applyNotificationsPayload(data);

    } catch (error) {

        console.error("Erro ao atualizar notificações:", error);

    }

}


function applyNotificationsPayload(data) {

    if (!data?.success || !notificationBody) return;

    notificationBody.innerHTML = data.html;
    notificationBody.dataset.latestNotificationId = data.latest_notification_id || 0;
    updateNotificationBadge(Number(data.unread_notifications || 0));
    setupNotificationShowMore();

}


function startNotificationEvents() {

    if (!notificationBody?.dataset.eventsUrl || !window.EventSource) return false;

    const lastSeen = notificationBody.dataset.latestNotificationId || "0";
    const url = `${notificationBody.dataset.eventsUrl}?last_seen=${encodeURIComponent(lastSeen)}`;
    const source = new EventSource(url);

    source.onmessage = (event) => {

        try {
            applyNotificationsPayload(JSON.parse(event.data));
        } catch (error) {
            console.error("Erro ao processar notificações:", error);
        }

        source.close();
        startNotificationEvents();

    };

    source.addEventListener("heartbeat", () => {

        source.close();
        startNotificationEvents();

    });

    source.onerror = () => {

        source.close();
        setTimeout(startNotificationEvents, 5000);

    };

    return true;

}


if (notificationBody) {

    setupNotificationShowMore();

    refreshNotifications().then(() => {

        if (!startNotificationEvents()) {
            setInterval(refreshNotifications, 10000);
        }

    });

}


// ================================
// VER MAIS NOTIFICAÇÕES
// ================================
function setupNotificationShowMore() {

    if (!notificationBody) return;

    const visibleLimit = 4;

    const items = Array.from(
        notificationBody.querySelectorAll(".notification-item")
    );

    const oldButton = notificationBody.querySelector(".notification-more-btn");

    oldButton?.remove();

    if (items.length <= visibleLimit) {
        items.forEach(item => item.classList.remove("is-hidden"));
        return;
    }

    // Estado inicial
    items.forEach((item, index) => {
        item.classList.toggle("is-hidden", index >= visibleLimit);
    });

    const button = document.createElement("button");

    button.type = "button";
    button.className = "notification-more-btn";
    button.textContent = `Ver mais ${items.length - visibleLimit}`;
    button.dataset.expanded = "false";

    button.addEventListener("click", () => {

        const expanded = button.dataset.expanded === "true";

        // Se estiver expandido -> esconder
        // Se estiver recolhido -> mostrar
        items.forEach((item, index) => {

            if (index < visibleLimit) return;

            item.classList.toggle("is-hidden", expanded);

        });

        button.dataset.expanded = expanded ? "false" : "true";

        button.textContent = expanded
            ? `Ver mais ${items.length - visibleLimit}`
            : "Mostrar menos";

    });

    notificationBody.appendChild(button);

}
