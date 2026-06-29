const campos = [
    ["nome","previewNome"],
    ["cargo","previewCargo"],
    ["departamento","previewDepartamento"],
    ["celular","previewCelular"],
    ["telefone","previewTelefone"],
    ["email","previewEmail"],
    ["site","previewSite"]
];

campos.forEach(([inputId,previewId]) => {

    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);

    if (!input || !preview) return;

    input.addEventListener("input", e => {

        preview.textContent = e.target.value;

    });

});

const logoUpload = document.getElementById("logoUpload");

logoUpload?.addEventListener("change", function(){

    const file = this.files[0];

    if(!file) return;

    const reader = new FileReader();

    reader.onload = function(e){

        document
            .getElementById("logoPreview")
            .src = e.target.result;

    }

    reader.readAsDataURL(file);

});

const copyButton = document.getElementById("copyBtn");

copyButton?.addEventListener("click", ()=>{

    const html =
        document.getElementById("signature").outerHTML;

    navigator.clipboard.writeText(html);

    alert("HTML copiado!");

});

const downloadButton = document.getElementById("downloadBtn");

downloadButton?.addEventListener("click", async () => {
    const signature = document.getElementById("signature");
    const logo = document.getElementById("logoPreview");

    if (!signature || typeof html2canvas !== "function") return;

    const originalButtonHtml = downloadButton.innerHTML;

    downloadButton.disabled = true;
    downloadButton.setAttribute("aria-busy", "true");
    downloadButton.innerHTML = `
        <i class="fas fa-circle-notch fa-spin"></i>
        Gerando assinatura...
    `;

    try {
        await document.fonts.ready;
        await waitForImage(logo);

        document.body.classList.add("signature-exporting");
        signature.classList.add("is-exporting");
        await nextFrame();

        const width = signature.offsetWidth;
        const height = signature.offsetHeight;

        const canvas = await html2canvas(signature, {
            backgroundColor: "#ffffff",
            scale: 2,
            useCORS: true,
            logging: false,
            width,
            height,
            scrollX: 0,
            scrollY: 0,
            windowWidth: width,
            windowHeight: height,
            onclone: clonedDocument => {
                clonedDocument.body.classList.add("signature-exporting");
                const clonedSignature = clonedDocument.getElementById("signature");
                clonedSignature?.classList.add("is-exporting");
            }
        });

        const link = document.createElement("a");
        link.download = "assinatura.png";
        link.href = canvas.toDataURL("image/png");
        link.click();
    } finally {
        document.body.classList.remove("signature-exporting");
        signature.classList.remove("is-exporting");
        downloadButton.disabled = false;
        downloadButton.removeAttribute("aria-busy");
        downloadButton.innerHTML = originalButtonHtml;
    }
});

function waitForImage(image) {
    if (!image || image.complete) {
        return Promise.resolve();
    }

    return new Promise(resolve => {
        image.addEventListener("load", resolve, { once: true });
        image.addEventListener("error", resolve, { once: true });
    });
}

function nextFrame() {
    return new Promise(resolve => {
        requestAnimationFrame(() => requestAnimationFrame(resolve));
    });
}
