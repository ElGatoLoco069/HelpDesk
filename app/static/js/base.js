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
const badge = document.querySelector(".badge");


/**
 * Anima botão de notificação
 * @param {number|string} count
 */
function newNotification(count = 1) {

    if (!notificationBtn || !badge) return;

    badge.textContent = count;

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

if (badge) {

    const totalNotifications = Number(badge.textContent.trim());

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
                if (badge) {
                    badge.remove();
                }

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