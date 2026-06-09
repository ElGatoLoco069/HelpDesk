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

    document
        .getElementById(inputId)
        .addEventListener("input", e => {

            document
                .getElementById(previewId)
                .textContent = e.target.value;

        });

});

document
.getElementById("logoUpload")
.addEventListener("change", function(){

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

document
.getElementById("copyBtn")
.addEventListener("click", ()=>{

    const html =
        document.getElementById("signature").outerHTML;

    navigator.clipboard.writeText(html);

    alert("HTML copiado!");

});