
const username = document.querySelector('input[name="username"]');
const remember = document.querySelector('input[name="remember"]');
const loginForm = document.querySelector(".login-form");

function showAuthLoader() {
    let loader = document.querySelector(".auth-loader");

    if (!loader) {
        loader = document.createElement("div");
        loader.className = "auth-loader";
        loader.setAttribute("role", "status");
        loader.setAttribute("aria-live", "polite");
        loader.innerHTML = `
            <div class="auth-loader-card">
                <span class="auth-loader-mark" aria-hidden="true"></span>
                <span class="auth-loader-copy">
                    <strong>Entrando</strong>
                    <span>Validando suas credenciais...</span>
                </span>
            </div>
        `;
        document.body.appendChild(loader);
    }

    window.setTimeout(() => {
        loader.classList.add("active");
        document.body.classList.add("auth-busy");
    }, 1000);
}

document.addEventListener("DOMContentLoaded", () => {
    if (!username || !remember) return;

    const savedUser = localStorage.getItem("username");

    if (savedUser) {
        username.value = savedUser;
        remember.checked = true;
    }

    remember.addEventListener("change", () => {
        if (remember.checked) {
            localStorage.setItem("username", username.value);
        } else {
            localStorage.removeItem("username");
        }
    });

    loginForm?.addEventListener("submit", (event) => {
        if (!loginForm.checkValidity()) return;

        const button = loginForm.querySelector(".btn-login");

        if (button) {
            button.disabled = true;
            button.setAttribute("aria-busy", "true");
            button.innerHTML = `
                <i class="fas fa-circle-notch" aria-hidden="true"></i>
                <span>Entrando...</span>
            `;
        }

        showAuthLoader();
    });
});
