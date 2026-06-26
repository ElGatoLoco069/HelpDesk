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
    });
})();
