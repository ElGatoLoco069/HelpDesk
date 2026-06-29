(() => {
    const MAX_FILE_SIZE = 10 * 1024 * 1024;
    const ACCEPTED_TYPES = ["image/png", "image/jpeg", "application/pdf"];

    function setupFileUpload(upload) {
        const input = upload.querySelector("input[type='file']");
        const list = upload.querySelector("[data-file-list]");
        const feedback = upload.querySelector("[data-upload-feedback]");
        const files = [];

        if (!input || !list) return;

        upload.addEventListener("click", (event) => {
            if (event.target === input) return;
            if (event.target.closest(".file-remove")) return;
            input.click();
        });

        input.addEventListener("change", (event) => {
            handleFiles(event.target.files);
        });

        upload.addEventListener("dragover", (event) => {
            event.preventDefault();
            upload.classList.add("dragover");
        });

        upload.addEventListener("dragleave", () => {
            upload.classList.remove("dragover");
        });

        upload.addEventListener("drop", (event) => {
            event.preventDefault();
            upload.classList.remove("dragover");
            handleFiles(event.dataTransfer.files);
        });

        list.addEventListener("click", (event) => {
            const button = event.target.closest(".file-remove");
            if (!button) return;

            files.splice(Number(button.dataset.index), 1);
            syncFileInput();
            renderFiles();
        });

        upload.fileUploadApi = {
            hasFiles: () => files.length > 0,
            showFeedback,
        };

        function handleFiles(selectedFiles) {
            clearFeedback();

            Array.from(selectedFiles).forEach(file => {
                if (!ACCEPTED_TYPES.includes(file.type)) {
                    showFeedback(`${file.name} nao e um arquivo PNG, JPG ou PDF.`, "error");
                    return;
                }

                if (file.size > MAX_FILE_SIZE) {
                    showFeedback(`${file.name} excede o limite de 10MB.`, "error");
                    return;
                }

                const alreadyAdded = files.some(item =>
                    item.name === file.name &&
                    item.size === file.size &&
                    item.lastModified === file.lastModified
                );

                if (!alreadyAdded) {
                    files.push(file);
                }
            });

            syncFileInput();
            renderFiles();
        }

        function renderFiles() {
            list.innerHTML = "";
            upload.classList.toggle("has-files", files.length > 0);

            files.forEach((file, index) => {
                const item = document.createElement("div");
                item.classList.add("file-item");

                item.innerHTML = `
                    <div class="file-info">
                        <i class="fas fa-file"></i>
                        <span title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>
                        <small class="file-size">${formatFileSize(file.size)}</small>
                    </div>
                    <button class="file-remove" type="button" data-index="${index}" title="Remover anexo">
                        <i class="fas fa-times"></i>
                    </button>
                `;

                list.appendChild(item);
            });
        }

        function syncFileInput() {
            const dataTransfer = new DataTransfer();
            files.forEach(file => dataTransfer.items.add(file));
            input.files = dataTransfer.files;
        }

        function showFeedback(message, type = "") {
            if (!feedback) return;

            feedback.innerText = message;
            feedback.classList.toggle("error", type === "error");
        }

        function clearFeedback() {
            if (!feedback) return;

            feedback.innerText = "";
            feedback.classList.remove("error");
        }
    }

    function setupRequiredAttachmentForm(form) {
        const upload = form.querySelector(".js-file-upload");
        const input = form.querySelector("input[type='file']");
        const submitButton = form.querySelector("[type='submit']");

        form.addEventListener("submit", (event) => {
            if (input?.files?.length) {
                window.AppLoading?.setButton(
                    submitButton,
                    submitButton?.dataset.loadingLabel || "Enviando..."
                );
                window.AppLoading?.show("Enviando anexos...");
                return;
            }

            event.preventDefault();
            upload?.fileUploadApi?.showFeedback("Selecione ao menos um anexo.", "error");
        });
    }

    function setupApprovalDecisionForm(form) {
        const decisionField = form.querySelector("[data-approval-decision-field]");

        if (!decisionField) return;

        form.addEventListener("submit", (event) => {
            const decision = event.submitter?.dataset.approvalDecision || "";
            decisionField.value = decision;
        });
    }

    function setupTicketTabs(tabList) {
        const buttons = Array.from(tabList.querySelectorAll("[data-ticket-tab]"));
        const panels = Array.from(document.querySelectorAll("[data-ticket-tab-panel]"));
        const slider = tabList.querySelector("[data-ticket-tab-slider]");
        const storageKey = `ticket-active-tab:${window.location.pathname}`;

        if (!buttons.length || !panels.length) return;

        function activateTab(panelId, focusButton = false) {
            const activeButton = buttons.find(button => button.dataset.ticketTab === panelId);
            const activePanel = panels.find(panel => panel.id === panelId);

            if (!activeButton || !activePanel) return;

            buttons.forEach(button => {
                const isActive = button === activeButton;
                button.classList.toggle("active", isActive);
                button.setAttribute("aria-selected", String(isActive));
                button.tabIndex = isActive ? 0 : -1;
            });

            panels.forEach(panel => {
                const isActive = panel === activePanel;
                panel.classList.toggle("active", isActive);
                panel.hidden = !isActive;
            });

            if (slider) {
                slider.style.width = `${activeButton.offsetWidth}px`;
                slider.style.left = `${activeButton.offsetLeft}px`;
                tabList.classList.add("ready");
            }

            try {
                sessionStorage.setItem(storageKey, panelId);
            } catch (error) {}

            if (focusButton) activeButton.focus();
        }

        buttons.forEach((button, index) => {
            button.addEventListener("click", () => {
                activateTab(button.dataset.ticketTab);
            });

            button.addEventListener("keydown", event => {
                if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;

                event.preventDefault();

                let nextIndex = index;

                if (event.key === "ArrowLeft") nextIndex = (index - 1 + buttons.length) % buttons.length;
                if (event.key === "ArrowRight") nextIndex = (index + 1) % buttons.length;
                if (event.key === "Home") nextIndex = 0;
                if (event.key === "End") nextIndex = buttons.length - 1;

                activateTab(buttons[nextIndex].dataset.ticketTab, true);
            });
        });

        let savedPanelId = "";

        try {
            savedPanelId = sessionStorage.getItem(storageKey) || "";
        } catch (error) {}

        activateTab(savedPanelId || buttons[0].dataset.ticketTab);

        window.addEventListener("resize", () => {
            const activeButton = buttons.find(button => button.getAttribute("aria-selected") === "true");

            if (!activeButton || !slider) return;

            slider.style.width = `${activeButton.offsetWidth}px`;
            slider.style.left = `${activeButton.offsetLeft}px`;
        });
    }

    function formatFileSize(size) {
        if (size >= 1024 * 1024) {
            return `${(size / 1024 / 1024).toFixed(1)}MB`;
        }

        return `${Math.max(1, Math.round(size / 1024))}KB`;
    }

    function escapeHtml(value) {
        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll(".js-file-upload").forEach(setupFileUpload);
        document
            .querySelectorAll("[data-require-attachments='true']")
            .forEach(setupRequiredAttachmentForm);
        document
            .querySelectorAll("[data-approval-decision-form]")
            .forEach(setupApprovalDecisionForm);
        document
            .querySelectorAll("[data-ticket-tabs]")
            .forEach(setupTicketTabs);
    });
})();
