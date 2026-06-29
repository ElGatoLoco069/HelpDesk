(function () {
    "use strict";

    const POLL_INTERVAL_MS = 60_000;
    const DISMISS_FOR_MS = 7 * 24 * 60 * 60 * 1000;
    const prompt = document.getElementById("browserNotificationPrompt");

    if (!prompt || !("Notification" in window) || !window.isSecureContext) return;

    const pendingUrl = prompt.dataset.pendingUrl;
    const iconUrl = prompt.dataset.iconUrl;
    const userId = prompt.dataset.userId;
    const storagePrefix = `helpdesk-browser-notification:${userId}:`;
    const dismissedKey = `helpdesk-browser-notification-dismissed:${userId}`;
    const displayedThisPage = new Set();
    let pollingStarted = false;

    function getCookie(name) {
        const prefix = `${name}=`;
        const cookie = document.cookie
            .split(";")
            .map(item => item.trim())
            .find(item => item.startsWith(prefix));
        return cookie ? decodeURIComponent(cookie.substring(prefix.length)) : "";
    }

    async function post(url) {
        const response = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            keepalive: true,
            headers: {
                "X-CSRFToken": prompt.dataset.csrfToken || getCookie("csrftoken"),
                "X-Requested-With": "XMLHttpRequest"
            }
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
    }

    function wasDisplayed(notificationId) {
        if (displayedThisPage.has(notificationId)) return true;

        try {
            return localStorage.getItem(`${storagePrefix}${notificationId}`) === "shown";
        } catch (error) {
            return false;
        }
    }

    function rememberDisplayed(notificationId) {
        displayedThisPage.add(notificationId);
        try {
            localStorage.setItem(`${storagePrefix}${notificationId}`, "shown");
        } catch (error) {}
    }

    async function createNativeNotification(item, appName) {
        if (wasDisplayed(item.id)) {
            await post(item.mark_displayed_url);
            return;
        }

        rememberDisplayed(item.id);

        let nativeNotification;
        try {
            nativeNotification = new Notification(`${appName} - ${item.title}`, {
                body: item.message,
                icon: iconUrl,
                tag: `${storagePrefix}${item.id}`,
                renotify: false,
                data: {url: item.url, notificationId: item.id}
            });
        } catch (error) {
            displayedThisPage.delete(item.id);
            try {
                localStorage.removeItem(`${storagePrefix}${item.id}`);
            } catch (storageError) {}
            throw error;
        }

        nativeNotification.onclick = function () {
            nativeNotification.close();
            window.focus();
            post(item.mark_read_url).catch(error => {
                console.error("Nao foi possivel marcar a notificacao como lida.", error);
            });
            window.location.assign(item.url);
        };

        await post(item.mark_displayed_url);
    }

    async function displayWithTabLock(item, appName) {
        const show = () => createNativeNotification(item, appName);

        // No Chrome, Web Locks evita que duas abas mostrem o mesmo aviso ao mesmo tempo.
        if (navigator.locks?.request) {
            await navigator.locks.request(
                `${storagePrefix}${item.id}`,
                {ifAvailable: true},
                async lock => {
                    if (lock) await show();
                }
            );
            return;
        }

        await show();
    }

    async function poll() {
        if (Notification.permission !== "granted" || !navigator.onLine) return;

        try {
            const response = await fetch(pendingUrl, {
                credentials: "same-origin",
                cache: "no-store",
                headers: {"X-Requested-With": "XMLHttpRequest"}
            });

            if (response.status === 401 || response.redirected) return;
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            if (!data.success) return;

            for (const item of data.notifications) {
                await displayWithTabLock(item, data.app_name || "HelpDesk");
            }
        } catch (error) {
            console.error("Falha ao consultar notificacoes do navegador.", error);
        }
    }

    function startPolling() {
        if (pollingStarted) return;
        pollingStarted = true;
        prompt.hidden = true;
        poll();
        window.setInterval(poll, POLL_INTERVAL_MS);
        window.addEventListener("online", poll);
    }

    function shouldShowFriendlyPrompt() {
        try {
            const dismissedAt = Number(localStorage.getItem(dismissedKey) || 0);
            return !dismissedAt || Date.now() - dismissedAt > DISMISS_FOR_MS;
        } catch (error) {
            return true;
        }
    }

    prompt.querySelector("[data-notification-allow]")?.addEventListener("click", async () => {
        const permission = await Notification.requestPermission();
        prompt.hidden = true;
        if (permission === "granted") startPolling();
    });

    prompt.querySelector("[data-notification-dismiss]")?.addEventListener("click", () => {
        prompt.hidden = true;
        try {
            localStorage.setItem(dismissedKey, String(Date.now()));
        } catch (error) {}
    });

    if (Notification.permission === "granted") {
        startPolling();
    } else if (Notification.permission === "default" && shouldShowFriendlyPrompt()) {
        prompt.hidden = false;
    }
    // permission === "denied": nenhuma acao; as notificacoes internas seguem normais.
})();
