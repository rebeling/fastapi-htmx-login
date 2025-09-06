from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import EmailStr

import app.cognito.mails as mails
from app.cognito.token import create_access_token, decode_token
from config import USERS

router = APIRouter(tags=["login"])

templates = Jinja2Templates(directory="templates")


def htmx_message(message: str, ok: bool = False) -> HTMLResponse:
    """
    Returns a small snippet for HTMX swaps into #response-container.
    Always 200 so HTMX swaps the content without navigating away.
    """
    cls = "ok" if ok else "error"
    html = f'<div id="response-container" class="{cls}">{message}</div>'
    return HTMLResponse(html, status_code=200)


@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request, error: str | None = None, reset_token: str | None = None):
    """Welcome page for unauthorized user"""
    error_message = None
    if error == "invalid_token":
        error_message = "Magic link is invalid or has expired."

    reset_email = None
    if reset_token:
        success, email = decode_token(reset_token, expected_purpose="password_reset")
        if success:
            reset_email = email
        else:
            error_message = "Password reset link is invalid or has expired."
            reset_token = None

    content = {
        "request": request,
        "error": error_message,
        "reset_token": reset_token,
        "reset_email": reset_email,
    }
    return templates.TemplateResponse("login.html", content)


@router.post("/login")
async def login_password(
    request: Request,
    username: Annotated[EmailStr, Form(...)],  # required, validated
    password: Annotated[str, Form(...)],  # required
):
    user = USERS.get(username)
    if not user or user["password"] != password:
        return templates.TemplateResponse(
            "partials/error_message.html",
            {"request": request, "message": "Invalid email or password."},
        )

    access_token = create_access_token(data={"sub": username})
    response = Response()
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    response.headers["HX-Redirect"] = "/welcome"
    return response


@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password(
    request: Request,
    background: BackgroundTasks,
):
    # Robustly accept both 'email' and 'username' fields
    form = await request.form()
    email_value = (form.get("email") or form.get("username") or "").strip()
    try:
        # Send email in the background (use your mailer)
        background.add_task(mails.send_password_reset_email, str(email_value), request)
    except Exception:
        # Intentionally ignore to avoid leaking information
        pass

    # Return the same message regardless of existence
    # Always respond the same to avoid user enumeration

    # Then show success message in main response container
    return templates.TemplateResponse(
        "partials/success_message.html",
        {
            "request": request,
            "message": "If an account exists for that address, a reset link has been sent.",
        },
    )


@router.post("/magic-login", response_class=HTMLResponse)
async def login_magic_link(
    request: Request, background: BackgroundTasks, username: Annotated[EmailStr, Form(...)]
):
    user = USERS.get(username)
    # if not user: return htmx_message("Email not found.")

    if user:
        # Send the email (in background so the response is snappy)
        background.add_task(mails.send_magic_link_email, str(username), request)

    return templates.TemplateResponse(
        "partials/success_message.html",
        {
            "request": request,
            "message": "If an account exists for that address, a magic link has been sent.",
        },
    )


@router.get("/magic-link-verify")
async def verify_magic_link(request: Request, token: str):
    success, email = decode_token(token)
    if not success:
        return RedirectResponse(url="/?error=invalid_token")

    access_token = create_access_token(data={"sub": email})
    response = RedirectResponse(url="/welcome")
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response


@router.get("/reset-password")
async def reset_password_form(request: Request, token: str):
    """Redirect to login page with reset token for password reset flow."""
    success, email = decode_token(token, expected_purpose="password_reset")
    if not success:
        return RedirectResponse(url="/?error=invalid_token")

    return RedirectResponse(url=f"/?reset_token={token}")


@router.post("/reset-password")
async def reset_password(
    request: Request,
    token: Annotated[str, Form(...)],
    new_password: Annotated[str, Form(...)],
    confirm_password: Annotated[str, Form(...)],
):
    """Process password reset with token validation."""
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "partials/error_message.html",
            {"request": request, "message": "Passwords do not match."},
        )

    success, email = decode_token(token, expected_purpose="password_reset")
    if not success:
        return templates.TemplateResponse(
            "partials/error_message.html",
            {"request": request, "message": "Invalid or expired reset token."},
        )

    # Update password in USERS dict
    if email in USERS:
        USERS[email]["password"] = new_password

    # Return success response that triggers card flip back to login
    response = templates.TemplateResponse(
        "partials/success_message.html",
        {
            "request": request,
            "message": "Password updated successfully! Please login with your new password.",
            "email": email,
        },
    )
    response.headers["HX-Trigger"] = "passwordResetSuccess"
    return response


@router.post("/logout")
async def logout():
    """Clear the auth cookie and redirect to root."""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response
