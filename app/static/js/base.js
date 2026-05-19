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

// Carrega tema salvo do localStorage
const isDarkMode = localStorage.getItem("darkMode") === "true";

/**
 * Aplica o tema claro/escuro na interface
 * @param {boolean} dark - true = modo escuro
 */
function applyTheme(dark) {
    if (dark) {
        document.documentElement.classList.add("dark");
        if (modeText) modeText.innerText = "Dark Mode";

        if (modeIcon) {
            modeIcon.classList.remove("fa-sun");
            modeIcon.classList.add("fa-moon");
        }

    } else {
        document.documentElement.classList.remove("dark");
        if (modeText) modeText.innerText = "Light Mode";

        if (modeIcon) {
            modeIcon.classList.remove("fa-moon");
            modeIcon.classList.add("fa-sun");
        }
    }
}

// Aplica o tema salvo ao carregar a página
applyTheme(isDarkMode);

// Alternar tema ao clicar no botão
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

function newNotification(count = 1) {

    const btn = document.querySelector(".notification-btn");
    if (!btn) return;

    const badge = btn.querySelector(".badge");
    if (!badge) return;

    badge.textContent = count;

    btn.classList.add("animate");

    setTimeout(() => {

        btn.classList.remove("animate");

        btn.classList.add("show-badge");

    }, 3000);
}


newNotification()
