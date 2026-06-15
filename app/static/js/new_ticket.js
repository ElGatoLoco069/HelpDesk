const form = document.getElementById("ticket-form");
const categorySelect = document.getElementById("category");
const subcategorySelect = document.getElementById("subcategory");
const descriptionInput = document.getElementById("description");
const descriptionCounter = document.getElementById("descriptionCounter");
const previewCategory = document.getElementById("previewCategory");
const previewSubcategory = document.getElementById("previewSubcategory");
const previewDescription = document.getElementById("previewDescription");
const previewAttachments = document.getElementById("previewAttachments");
const upload = document.getElementById("fileUpload");
const input = document.getElementById("attachments");
const list = document.getElementById("fileList");
const uploadFeedback = document.getElementById("uploadFeedback");

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/png", "image/jpeg", "application/pdf"];

let files = [];

categorySelect.addEventListener("change", () => {
    updatePreview();
    loadSubcategories(categorySelect.value);
});

subcategorySelect.addEventListener("change", updatePreview);
descriptionInput.addEventListener("input", () => {
    updateDescriptionCounter();
    updatePreview();
});

upload.addEventListener("click", () => input.click());

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

form.addEventListener("submit", (event) => {
    event.preventDefault();

    const isValid = validateForm();
    const submitButton = document.getElementById("submitTicket");

    if (!isValid) {
        window.AppLoading?.resetButton(submitButton);
        window.AppLoading?.hide();
        showFeedback("Revise os campos destacados antes de confirmar.", "error");
        return;
    }

    window.AppLoading?.setButton(submitButton, "Abrindo chamado...");
    window.AppLoading?.show("Registrando chamado e anexos...");
    form.submit();
});

function loadSubcategories(categoryId) {
    const field = subcategorySelect.closest(".field");
    resetSubcategories("Carregando subcategorias...");
    field?.classList.add("is-loading");

    if (!categoryId) {
        field?.classList.remove("is-loading");
        resetSubcategories("Selecione uma categoria primeiro");
        updatePreview();
        return;
    }

    fetch(`/subcategories/${categoryId}/`)
        .then(response => response.json())
        .then(data => {
            subcategorySelect.innerHTML = "";

            if (!data.length) {
                resetSubcategories("Nenhuma subcategoria encontrada");
                updatePreview();
                return;
            }

            subcategorySelect.disabled = false;
            subcategorySelect.innerHTML = "<option value=''>Selecione uma subcategoria</option>";

            data.forEach(subcategory => {
                const option = document.createElement("option");
                option.value = subcategory.id;
                option.textContent = subcategory.name;
                subcategorySelect.appendChild(option);
            });

            updatePreview();
        })
        .catch(() => {
            resetSubcategories("Erro ao carregar subcategorias");
            showFeedback("Nao foi possivel carregar as subcategorias.", "error");
            updatePreview();
        })
        .finally(() => {
            field?.classList.remove("is-loading");
        });
}

function resetSubcategories(message) {
    subcategorySelect.disabled = true;
    subcategorySelect.innerHTML = `<option value="">${message}</option>`;
}

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

    updatePreview();
}

function syncFileInput() {
    const dataTransfer = new DataTransfer();
    files.forEach(file => dataTransfer.items.add(file));
    input.files = dataTransfer.files;
}

function validateForm() {
    const hasCategory = Boolean(categorySelect.value);
    const hasSubcategory = Boolean(subcategorySelect.value);
    const hasDescription = descriptionInput.value.trim().length >= 15;

    setFieldState(categorySelect, hasCategory);
    setFieldState(subcategorySelect, hasSubcategory);
    setFieldState(descriptionInput, hasDescription);

    return hasCategory && hasSubcategory && hasDescription;
}

function setFieldState(inputElement, isValid) {
    const field = inputElement.closest(".field");
    if (!field) return;

    field.classList.toggle("invalid", !isValid);
}

function updateDescriptionCounter() {
    const length = descriptionInput.value.length;
    const text = `${length}/550`;

    descriptionCounter.innerText = text;
    previewDescription.innerText = text;
    descriptionCounter.classList.toggle("counter-danger", length > 0 && length < 15);
}

function updatePreview() {
    const categoryText = categorySelect.selectedOptions[0]?.textContent || "";
    const subcategoryText = subcategorySelect.selectedOptions[0]?.textContent || "";
    const attachmentLabel = files.length === 1 ? "1 anexo" : `${files.length} anexos`;

    previewCategory.innerText = categorySelect.value ? categoryText : "Categoria nao selecionada";
    previewSubcategory.innerText = subcategorySelect.value ? subcategoryText : "Subcategoria pendente";
    previewAttachments.innerText = attachmentLabel;
}

function showFeedback(message, type = "") {
    uploadFeedback.innerText = message;
    uploadFeedback.classList.toggle("error", type === "error");
}

function clearFeedback() {
    uploadFeedback.innerText = "";
    uploadFeedback.classList.remove("error");
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

updateDescriptionCounter();
updatePreview();
