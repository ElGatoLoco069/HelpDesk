// ================================
// SIDEBAR TOGGLE
// ================================

const sidebar = document.querySelector(".sidebar");
const sidebarToggleBtn = document.querySelectorAll(".sidebar-toggle");

function getSavedSidebarState() {
    try {
        return localStorage.getItem("sidebarCollapsed") === "true";
    } catch (error) {
        return false;
    }
}

function saveSidebarState(isCollapsed) {
    try {
        localStorage.setItem("sidebarCollapsed", String(isCollapsed));
    } catch (error) {}
}

if (sidebar && getSavedSidebarState()) {
    sidebar.classList.add("collapsed");
}

// ================================
// LOADING GLOBAL
// ================================

const AppLoading = (() => {
    let overlay = null;
    let overlayTimer = null;

    function ensureOverlay() {
        if (overlay) return overlay;

        overlay = document.createElement("div");
        overlay.className = "page-loader";
        overlay.setAttribute("role", "status");
        overlay.setAttribute("aria-live", "polite");
        overlay.innerHTML = `
            <div class="page-loader-card">
                <span class="loader-mark" aria-hidden="true"></span>
                <span class="loader-copy">
                    <span class="loader-title">Carregando</span>
                    <span class="loader-text">Preparando as informacoes...</span>
                </span>
            </div>
        `;

        document.body.appendChild(overlay);
        return overlay;
    }

    function show(message = "Preparando as informacoes...", options = {}) {
        const currentOverlay = ensureOverlay();
        const text = currentOverlay.querySelector(".loader-text");
        const delay = Number(options.delay ?? 650);

        if (text) {
            text.textContent = message;
        }

        window.clearTimeout(overlayTimer);
        overlayTimer = window.setTimeout(() => {
            currentOverlay.classList.add("active");
            document.body.classList.add("app-busy");
        }, delay);
    }

    function hide() {
        window.clearTimeout(overlayTimer);

        if (overlay) {
            overlay.classList.remove("active");
        }

        document.body.classList.remove("app-busy");
    }

    function setButton(button, label = "Aguarde...") {
        if (!button || button.dataset.loading === "true") return;

        button.dataset.loading = "true";
        button.dataset.originalHtml = button.innerHTML;
        button.disabled = true;
        button.setAttribute("aria-busy", "true");
        button.innerHTML = `
            <i class="fas fa-circle-notch" aria-hidden="true"></i>
            <span>${label}</span>
        `;
    }

    function resetButton(button) {
        if (!button || button.dataset.loading !== "true") return;

        button.innerHTML = button.dataset.originalHtml || button.innerHTML;
        button.disabled = false;
        button.removeAttribute("aria-busy");
        delete button.dataset.loading;
        delete button.dataset.originalHtml;
    }

    return {
        show,
        hide,
        setButton,
        resetButton
    };
})();

window.AppLoading = AppLoading;

document.addEventListener("submit", (event) => {
    const form = event.target;

    if (!(form instanceof HTMLFormElement) || form.dataset.skipLoading === "true") return;

    const submitter = event.submitter || form.querySelector("[type='submit']");
    AppLoading.setButton(submitter, submitter?.dataset.loadingLabel || "Enviando...");

    if (!event.defaultPrevented) {
        AppLoading.show(form.dataset.loadingMessage || "Salvando as informacoes...");
    }
}, true);

document.addEventListener("click", (event) => {
    if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
    ) return;

    const link = event.target.closest("a[href]");

    if (!link || link.target || link.hasAttribute("download")) return;

    const href = link.getAttribute("href");

    if (
        !href ||
        href.startsWith("#") ||
        href.startsWith("javascript:") ||
        link.dataset.skipLoading === "true"
    ) return;

    const url = new URL(href, window.location.href);

    if (url.origin !== window.location.origin) return;

    AppLoading.show(
        link.dataset.loadingMessage || "Abrindo pagina...",
        { delay: Number(link.dataset.loadingDelay || 700) }
    );
});

window.addEventListener("pageshow", () => {
    AppLoading.hide();
});

sidebarToggleBtn.forEach(btn => {

    btn.addEventListener("click", () => {

        if (!sidebar) return;

        const isCollapsed = sidebar.classList.toggle("collapsed");

        saveSidebarState(isCollapsed);

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

        if (sidebar?.classList.contains("collapsed")) {
            sidebar.classList.remove("collapsed");
            saveSidebarState(false);
        }

        if (!parent) return;

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
        AppLoading.setButton(markReadBtn, "Marcando...");

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
                    Todas notificacoes lidas
                `;

                markReadBtn.disabled = true;
                markReadBtn.removeAttribute("aria-busy");
                delete markReadBtn.dataset.loading;
                delete markReadBtn.dataset.originalHtml;

            }

        } catch (error) {

            console.error("Erro ao marcar notificações:", error);
            AppLoading.resetButton(markReadBtn);

        }

    });

}


// ================================
// ATUALIZAR NOTIFICAÇÕES
// ================================

document.addEventListener("click", function (event) {
    const notification = event.target.closest(".notification-item[data-url]");

    if (!notification) return;

    if (
        event.target.closest("button") ||
        event.target.closest("form") ||
        event.target.closest(".notification-actions") ||
        event.target.closest(".notification-rating")
    ) {
        return;
    }

    window.location.href = notification.dataset.url;
});

async function refreshNotifications() {

    if (!notificationBody?.dataset.refreshUrl) return;

    try {
        notificationBody.classList.add("is-loading");

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
    } finally {
        notificationBody.classList.remove("is-loading");

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
