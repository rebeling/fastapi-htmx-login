import pytest
from fastapi.testclient import TestClient

from app.cognito.token import create_access_token
from main import app


@pytest.fixture()
def client():
    return TestClient(app, follow_redirects=False)


def test_root_page_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Login with Password" in resp.text


def test_root_with_invalid_token_error_shows_message(client):
    resp = client.get("/?error=invalid_token")
    assert resp.status_code == 200
    assert "invalid or has expired" in resp.text


def test_password_login_failure_shows_error(client):
    resp = client.post("/login", data={"username": "nope@example.com", "password": "bad"})
    assert resp.status_code == 200
    assert "Invalid email or password" in resp.text


def test_password_login_success_sets_cookie_and_hx_redirect(client):
    resp = client.post("/login", data={"username": "test@example.com", "password": "password123"})
    assert resp.status_code == 200
    # Cookie is set and HX-Redirect header points to /welcome
    assert "access_token=" in resp.headers.get("set-cookie", "")
    assert resp.headers.get("HX-Redirect") == "/welcome"


def test_welcome_requires_auth_redirects_to_root(client):
    resp = client.get("/welcome")
    assert resp.status_code in (302, 307)
    assert resp.headers.get("location") == "/"


def test_welcome_with_cookie_succeeds(client):
    token = create_access_token({"sub": "test@example.com"})
    cookies = {"access_token": f"Bearer {token}"}
    resp = client.get("/welcome", cookies=cookies)
    assert resp.status_code == 200
    assert "test@example.com" in resp.text


def test_magic_login_returns_generic_message(client, monkeypatch):
    # Avoid sending real emails in background task
    monkeypatch.setattr("app.cognito.mails.send_magic_link_email", lambda *args, **kwargs: None)
    resp = client.post("/magic-login", data={"username": "test@example.com"})
    assert resp.status_code == 200
    assert "magic link has been sent" in resp.text.lower()


def test_magic_link_verify_sets_cookie_and_redirects(client):
    token = create_access_token({"sub": "test@example.com"})
    resp = client.get(f"/magic-link-verify?token={token}", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers.get("location") == "/welcome"
    assert "access_token=" in resp.headers.get("set-cookie", "")


def test_magic_link_verify_invalid_token_redirects_with_error(client):
    resp = client.get("/magic-link-verify?token=not-a-valid-token", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers.get("location") == "/?error=invalid_token"


def test_forgot_password_fragment_and_post(client, monkeypatch):
    # Fragment renders the button snippet
    frag = client.get("/forgot-password/fragment")
    assert frag.status_code == 200
    assert "Send reset link" in frag.text

    # Avoid sending real emails
    monkeypatch.setattr("app.cognito.mails.send_password_reset_email", lambda *args, **kwargs: None)
    res = client.post("/forgot-password", data={"email": "test@example.com"})
    assert res.status_code == 200
    assert "reset link has been sent" in res.text.lower()


def test_forgot_password_requires_email(client):
    res = client.post("/forgot-password")
    assert res.status_code == 200
    assert "email is required" in res.text.lower()
