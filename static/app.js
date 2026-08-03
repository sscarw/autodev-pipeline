function openTicket(key) {
    const overlay = document.getElementById("detail-overlay");
    const panel = document.getElementById("detail-panel");
    if (!overlay || !panel) return;

    panel.innerHTML = '<div class="detail-loading">Loading...</div>';
    overlay.classList.add("open");

    fetch(`/ticket/${encodeURIComponent(key)}`)
        .then((res) => res.text())
        .then((html) => {
            panel.innerHTML = html;
        });
}

function closeTicket(event) {
    const overlay = document.getElementById("detail-overlay");
    if (overlay) overlay.classList.remove("open");
}

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeTicket();
});

let lastBoardHtml = null;

function refreshBoard() {
    const wrap = document.getElementById("board-wrap");
    if (!wrap) return;

    fetch("/partials/board")
        .then((res) => res.text())
        .then((html) => {
            // Skip the DOM write entirely when nothing changed, so we don't
            // disrupt scroll position or an in-progress click every cycle.
            if (html === lastBoardHtml) return;
            lastBoardHtml = html;
            wrap.innerHTML = html;
        });
}

if (document.getElementById("board-wrap")) {
    setInterval(refreshBoard, 5000);
}

function toggleSecret(inputId, button) {
    const input = document.getElementById(inputId);
    if (!input) return;

    if (input.type === "password") {
        input.type = "text";
        button.classList.add("revealed");
        button.setAttribute("aria-label", "Hide value");
    } else {
        input.type = "password";
        button.classList.remove("revealed");
        button.setAttribute("aria-label", "Show value");
    }
}
