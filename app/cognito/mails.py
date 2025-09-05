import logging
from dataclasses import dataclass
from datetime import timedelta

# from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import emails  # type: ignore
from fastapi import Request
from jinja2 import Template

from app.cognito.token import create_access_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


SMTP_HOST = "localhost"
SMTP_PORT = 1025  # Mailcatcher
EMAILS_FROM_NAME = "Dev"
EMAILS_FROM_EMAIL = "dev@local.test"
EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48
PROJECT_NAME = "FastAPI HTMX Login"


@dataclass
class EmailData:
    html_content: str
    subject: str


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (Path(__file__).parent / "email-templates" / "build" / template_name).read_text()
    html_content = Template(template_str).render(context)
    return html_content


def send_email(
    *,
    email: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    # assert settings.emails_enabled, "no provided configuration for email variables"
    message = emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(EMAILS_FROM_NAME, EMAILS_FROM_EMAIL),
    )
    smtp_options = {"host": SMTP_HOST, "port": SMTP_PORT}
    # if settings.SMTP_TLS:
    #     smtp_options["tls"] = True
    # elif settings.SMTP_SSL:
    #     smtp_options["ssl"] = True
    # if settings.SMTP_USER:
    #     smtp_options["user"] = settings.SMTP_USER
    # if settings.SMTP_PASSWORD:
    #     smtp_options["password"] = settings.SMTP_PASSWORD
    response = message.send(to=email, smtp=smtp_options)
    logger.info(f"send email result: {response}")


def send_magic_link_email(email: str, request: Request):
    logger.info("send magic email in background ;) ")
    project_name = PROJECT_NAME
    subject = f"{project_name} - Magic link for user {email}"

    magic_token = create_access_token(data={"sub": email}, expires_delta=timedelta(minutes=5))
    magic_link = f"/magic-link-verify?token={magic_token}"
    magical = f"{request.base_url.scheme}://{request.base_url.netloc}{magic_link}"
    logger.info(f"Magic Link for {email}: {magical}")

    html_content = render_email_template(
        template_name="magic_link_email.html",
        context={
            "project_name": PROJECT_NAME,
            "username": email,
            "email": email,
            # MJML expects `link`; magic link expires in 5 minutes (wording in template)
            "link": magical,
        },
    )

    email_data = EmailData(html_content=html_content, subject=subject)

    send_email(
        email=email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )


def send_password_reset_email(email: str, request: Request):
    logger.info("send reset email in background ;) ")
    project_name = PROJECT_NAME
    subject = f"{project_name} - Reset password link for user {email}"

    # Issue a short-lived reset token (different purpose than access)
    reset_token = create_access_token({"sub": email, "purpose": "password_reset"})
    reset_link = (
        f"{request.base_url.scheme}://{request.base_url.netloc}/reset-password?token={reset_token}"
    )
    logger.info(f"Reset Link for {email}: {reset_link}")

    html_content = render_email_template(
        template_name="reset_password.html",
        context={
            "project_name": PROJECT_NAME,
            "username": email,
            "email": email,
            "link": reset_link,
            # Surface validity to template text
            "valid_hours": EMAIL_RESET_TOKEN_EXPIRE_HOURS,
        },
    )

    email_data = EmailData(html_content=html_content, subject=subject)

    send_email(
        email=email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
