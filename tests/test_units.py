from types import SimpleNamespace

import pytest

from app.cognito import mails as mails_mod
from app.cognito import utils as utils_mod
from app.cognito.token import create_access_token, decode_token


def test_token_decode_invalid_returns_false_none():
    ok, email = decode_token("invalid.token")
    assert ok is False and email is None


def test_token_decode_missing_sub_returns_false():
    token = create_access_token({})  # no 'sub'
    ok, email = decode_token(token)
    assert ok is False and email is None


def test_get_current_user_no_cookie_raises_redirect():
    req = SimpleNamespace(cookies={})
    with pytest.raises(Exception) as exc:
        utils_mod.get_current_user(req)
    assert hasattr(exc.value, "headers") and exc.value.headers.get("Location") == "/"


def test_get_current_user_invalid_token_redirects():
    req = SimpleNamespace(cookies={"access_token": "Bearer not-a-token"})
    with pytest.raises(Exception) as exc:
        utils_mod.get_current_user(req)
    assert exc.value.headers.get("Location") == "/"


def test_get_current_user_valid_token_returns_user():
    token = create_access_token({"sub": "test@example.com"})
    req = SimpleNamespace(cookies={"access_token": f"Bearer {token}"})
    user = utils_mod.get_current_user(req)
    assert user["email"] == "test@example.com"


def test_get_current_user_token_without_sub_redirects():
    # Create a signed token without a 'sub' claim
    token = create_access_token({})
    req = SimpleNamespace(cookies={"access_token": f"Bearer {token}"})
    with pytest.raises(Exception) as exc:
        utils_mod.get_current_user(req)
    assert exc.value.headers.get("Location") == "/"


def test_mails_send_magic_and_reset_email(monkeypatch):
    sent = []

    class DummyMessage:
        def __init__(self, subject, html, mail_from):  # noqa: D401
            self.subject = subject
            self.html = html
            self.mail_from = mail_from

        def send(self, to, smtp):
            sent.append(
                {
                    "to": to,
                    "subject": self.subject,
                    "html": self.html,
                    "smtp": smtp,
                }
            )
            return "ok"

    # Patch emails.Message used inside mails module
    monkeypatch.setattr(mails_mod, "emails", SimpleNamespace(Message=DummyMessage))

    # Fake request with just what mails accesses
    fake_request = SimpleNamespace(base_url=SimpleNamespace(scheme="http", netloc="test.local"))

    mails_mod.send_magic_link_email("user@example.com", fake_request)
    mails_mod.send_password_reset_email("user@example.com", fake_request)

    assert len(sent) == 2
    subj = {s["subject"] for s in sent}
    assert any("Magic link" in s for s in subj)
    assert any("Reset password" in s for s in subj)
    # HTML should contain the constructed link placeholder
    assert any("/magic-link-verify?token=" in s["html"] for s in sent)
    assert any("/reset-password?token=" in s["html"] for s in sent)
