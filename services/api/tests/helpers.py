"""Shared test utilities for authenticated API tests."""

from uuid import uuid4

from fastapi.testclient import TestClient


def register_and_get_headers(
    client: TestClient,
    username: str = "test_user",
    password: str = "test_pass_123",
) -> dict[str, str]:
    """Register a user and return Authorization headers for authenticated requests."""
    actual_username = f"{username}_{uuid4().hex[:8]}"
    res = client.post(
        "/api/v1/auth/register",
        json={"username": actual_username, "password": password},
    )
    if res.status_code == 201:
        token = res.json()["access_token"]
    else:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": actual_username, "password": password},
        )
        token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
