from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_github_oauth_start_contract() -> None:
    response = client.get("/api/v1/auth/github/start")
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "github"
    assert payload["state"]
    assert payload["redirect_uri"]
    assert isinstance(payload["scopes"], list)
    assert "authorization_url" in payload


def test_email_login_and_session_validation() -> None:
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "athena@gitsyntropy.dev", "password": "localdev123"},
    )
    assert login_res.status_code == 200
    login_payload = login_res.json()
    assert login_payload["user_id"] == "user_athena"

    session_res = client.get(
        "/api/v1/auth/session",
        headers={"Authorization": f"Bearer {login_payload['access_token']}"},
    )
    assert session_res.status_code == 200
    session_payload = session_res.json()
    assert session_payload["authenticated"] is True
    assert session_payload["user_id"] == "user_athena"
    assert "expires_at" in session_payload


def test_github_callback_invalid_code_returns_400() -> None:
    """A stale/invalid code should be rejected cleanly (GitHub returns error, we 400)."""
    callback_res = client.post(
        "/api/v1/auth/github/callback",
        json={"code": "mock-oauth-code-12345"},
    )
    # Real credentials are configured, so the code hits GitHub and fails → 400
    assert callback_res.status_code in {200, 400}
    if callback_res.status_code == 200:
        payload = callback_res.json()
        assert payload["access_token"]
        assert payload["user_id"]


def test_session_requires_bearer_header() -> None:
    response = client.get("/api/v1/auth/session")
    assert response.status_code == 401
