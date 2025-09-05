from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import EmailStr

from app.cognito.htmx import htmx_message
from app.cognito.mails import send_magic_link_email
from app.cognito.token import create_access_token, decode_token
from config import USERS

router = APIRouter(tags=["login"])

templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request, error: str | None = None):
    """Welcome page for unauthorized user"""
    error_message = None
    if error == "invalid_token":
        error_message = "Magic link is invalid or has expired."
    content = {"request": request, "error": error_message}
    return templates.TemplateResponse("login.html", content)


@router.post("/login")
async def login_password(
    request: Request,
    username: Annotated[EmailStr, Form(...)],  # required, validated
    password: Annotated[str, Form(...)],  # required
):
    user = USERS.get(username)
    if not user or user["password"] != password:
        return htmx_message("Invalid email or password.")

    access_token = create_access_token(data={"sub": username})
    response = Response()
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    response.headers["HX-Redirect"] = "/welcome"
    return response


@router.get("/forgot-password/fragment", response_class=HTMLResponse)
async def forgot_password_fragment():
    # Button posts to /forgot-password and includes #email value from the page
    from app.cognito.htmx import send_reset_link_button_html

    return HTMLResponse(send_reset_link_button_html)


@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password(request: Request, background: BackgroundTasks, email: str = Form(None)):
    if not email:
        return htmx_message("Email is required.")

    try:
        # Send email in the background (use your mailer)
        from app.cognito.mails import send_password_reset_email

        background.add_task(send_password_reset_email, str(email), request)
    except Exception:
        # Intentionally ignore to avoid leaking information
        pass

    # Return the same message regardless of existence
    # Always respond the same to avoid user enumeration
    from app.cognito.htmx import reset_link_sent_html

    return HTMLResponse(reset_link_sent_html)


@router.post("/magic-login", response_class=HTMLResponse)
async def login_magic_link(
    request: Request, background: BackgroundTasks, username: Annotated[EmailStr, Form(...)]
):
    user = USERS.get(username)
    # if not user: return htmx_message("Email not found.")

    if user:
        # Send the email (in background so the response is snappy)
        background.add_task(send_magic_link_email, str(username), request)

    return htmx_message("If the email exists, a magic link has been sent.")


@router.get("/magic-link-verify")
async def verify_magic_link(request: Request, token: str):
    success, email = decode_token(token)
    if not success:
        return RedirectResponse(url="/?error=invalid_token")

    access_token = create_access_token(data={"sub": email})
    response = RedirectResponse(url="/welcome")
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response
