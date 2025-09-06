import pytest
from fastapi.testclient import TestClient

from app.cognito.api.routes.login import htmx_message
from app.cognito.token import create_access_token, decode_token
from config import USERS
from main import app


@pytest.fixture()
def client():
    return TestClient(app, follow_redirects=False)


def test_root_with_valid_reset_token_prefills_and_sets_hidden(client):
    token = create_access_token({"sub": "test@example.com", "purpose": "password_reset"})
    resp = client.get(f"/?reset_token={token}")
    assert resp.status_code == 200
    # Username field on reset side should be prefilled and readonly
    assert 'id="username-reset"' in resp.text
    assert 'value="test@example.com"' in resp.text
    # Hidden reset token should be present
    assert 'id="reset_token"' in resp.text


def test_root_with_invalid_reset_token_shows_error(client):
    resp = client.get("/?reset_token=not-a-valid-token")
    assert resp.status_code == 200
    assert "Password reset link is invalid or has expired." in resp.text


def test_forgot_password_accepts_username_and_succeeds(client, monkeypatch):
    # Avoid executing email-sending background task
    monkeypatch.setattr("app.cognito.mails.send_password_reset_email", lambda *args, **kwargs: None)
    resp = client.post("/forgot-password", data={"username": "user@example.com"})
    assert resp.status_code == 200
    assert "a reset link has been sent" in resp.text.lower()


def test_forgot_password_add_task_exception_is_ignored(client, monkeypatch):
    # Force the add_task call to raise, covering the try/except path
    def raise_in_add_task(self, *args, **kwargs):  # noqa: D401
        raise RuntimeError("boom")

    # Patch FastAPI's BackgroundTasks.add_task used in the route
    import fastapi

    monkeypatch.setattr(fastapi.BackgroundTasks, "add_task", raise_in_add_task)

    resp = client.post(
        "/forgot-password",
        data={"email": "user@example.com"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    # The endpoint should swallow the exception and still return the generic success
    assert resp.status_code == 200
    assert "a reset link has been sent" in resp.text.lower()


def test_reset_password_get_valid_redirects_with_token(client):
    token = create_access_token({"sub": "test@example.com", "purpose": "password_reset"})
    resp = client.get(f"/reset-password?token={token}", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers.get("location") == f"/?reset_token={token}"


def test_reset_password_get_invalid_redirects_with_error(client):
    resp = client.get("/reset-password?token=bad", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers.get("location") == "/?error=invalid_token"


def test_reset_password_post_mismatched_passwords_shows_error(client):
    resp = client.post(
        "/reset-password",
        data={
            "token": "any",
            "new_password": "one",
            "confirm_password": "two",
        },
    )
    assert resp.status_code == 200
    assert "Passwords do not match" in resp.text


def test_reset_password_post_invalid_token_shows_error(client):
    resp = client.post(
        "/reset-password",
        data={
            "token": "invalid",
            "new_password": "secret",
            "confirm_password": "secret",
        },
    )
    assert resp.status_code == 200
    assert "Invalid or expired reset token" in resp.text


def test_reset_password_post_valid_token_updates_and_triggers_hx_header(client):
    # Ensure user exists and capture original password
    email = "test@example.com"
    original = USERS[email]["password"]
    try:
        token = create_access_token({"sub": email, "purpose": "password_reset"})
        resp = client.post(
            "/reset-password",
            data={
                "token": token,
                "new_password": "newpass123",
                "confirm_password": "newpass123",
            },
        )
        assert resp.status_code == 200
        assert "Password updated successfully" in resp.text
        assert resp.headers.get("HX-Trigger") == "passwordResetSuccess"
        # Password updated in USERS
        assert USERS[email]["password"] == "newpass123"
    finally:
        USERS[email]["password"] = original


def test_logout_deletes_cookie_and_redirects(client):
    resp = client.post("/logout", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers.get("location") == "/"
    # A Set-Cookie header removing the access_token is expected
    set_cookie = resp.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie and (
        "Max-Age=0" in set_cookie or "expires=" in set_cookie.lower()
    )


def test_htmx_message_ok_and_error():
    r_ok = htmx_message("All good", ok=True)
    assert r_ok.status_code == 200 and 'class="ok"' in r_ok.body.decode()
    r_err = htmx_message("Oops", ok=False)
    assert r_err.status_code == 200 and 'class="error"' in r_err.body.decode()


def test_decode_token_purpose_mismatch_returns_false():
    t = create_access_token({"sub": "x@example.com", "purpose": "password_reset"})
    ok, email = decode_token(t, expected_purpose="something_else")
    assert ok is False and email is None
