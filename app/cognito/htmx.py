from fastapi.responses import HTMLResponse

send_reset_link_button_html = """
<div id="forgot-container" class="form-control mt-4" aria-live="polite">
    <p class="hint mb-2">Click the button below to receive a password reset link.</p>
    <button class="btn btn-soft btn-primary rounded-lg" onclick="sendResetLink(event)">
    <i class="fas fa-link"></i> Send reset link
    </button>
</div>
"""

reset_link_sent_html = """
<div id="forgot-container" class="form-control mt-4" aria-live="polite">
    <p class="hint">If an account exists for that address, a reset link has been sent.</p>
</div>
"""


def htmx_message(message: str, ok: bool = False) -> HTMLResponse:
    """
    Returns a small snippet for HTMX swaps into #response-container.
    Always 200 so HTMX swaps the content without navigating away.
    """
    cls = "ok" if ok else "error"
    html = f'<div id="response-container" class="{cls}">{message}</div>'
    return HTMLResponse(html, status_code=200)
