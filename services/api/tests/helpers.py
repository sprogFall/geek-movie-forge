"""Shared test utilities for authenticated API tests."""

from fastapi.testclient import TestClient


def register_and_get_headers(
    client: TestClient,
    username: str = "test_user",
    password: str = "test_pass_123",
) -> dict[str, str]:
    """Register a user and return Authorization headers for authenticated requests."""
    res = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password},
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
