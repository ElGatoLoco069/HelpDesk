
const username = document.querySelector('input[name="username"]');
const remember = document.querySelector('input[name="remember"]');

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
});
