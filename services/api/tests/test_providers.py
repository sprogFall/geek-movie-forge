from fastapi.testclient import TestClient

from services.api.app.main import app
from services.api.tests.helpers import register_and_get_headers


def test_create_and_update_provider_configuration() -> None:
    create_payload = {
        "name": "Forge Provider",
        "base_url": "https://provider.example.com/v1",
        "api_key": "super-secret-key",
        "models": [
            {"model": "forge-text-v1", "capabilities": ["text"]},
            {"model": "forge-image-v1", "capabilities": ["image", "video"]},
        ],
    }

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        create_response = client.post("/api/v1/providers", json=create_payload, headers=headers)

        assert create_response.status_code == 201
        body = create_response.json()
        provider_id = body["provider_id"]

        assert body["name"] == create_payload["name"]
        assert body["base_url"] == create_payload["base_url"]
        assert body["api_key_masked"].startswith("sup")
        assert body["api_key_masked"].endswith("key")
        assert body["models"] == create_payload["models"]
        assert body["routes"]["image"]["path"] == "/image/generations"
        assert body["routes"]["video"]["path"] == "/video/generations"

        update_payload = {
            "base_url": "https://provider.example.com/api",
            "api_key": "another-secret-key",
            "models": [
                {"model": "forge-text-v2", "capabilities": ["text"]},
                {"model": "forge-video-v1", "capabilities": ["video"]},
            ],
        }
        update_response = client.put(
            f"/api/v1/providers/{provider_id}", json=update_payload, headers=headers
        )
        list_response = client.get("/api/v1/providers", headers=headers)
        detail_response = client.get(f"/api/v1/providers/{provider_id}", headers=headers)

    assert update_response.status_code == 200
    assert list_response.status_code == 200
    assert detail_response.status_code == 200

    updated_body = update_response.json()
    assert updated_body["provider_id"] == provider_id
    assert updated_body["base_url"] == update_payload["base_url"]
    assert updated_body["models"] == update_payload["models"]
    assert updated_body["api_key_masked"].startswith("ano")
    assert detail_response.json()["models"] == update_payload["models"]
    assert list_response.json()["items"][0]["provider_id"] == provider_id


def test_create_provider_rejects_duplicate_name() -> None:
    payload = {
        "name": "Duplicate Provider",
        "base_url": "https://provider.example.com/v1",
        "api_key": "super-secret-key",
        "models": [{"model": "forge-image-v1", "capabilities": ["image"]}],
    }

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        first_response = client.post("/api/v1/providers", json=payload, headers=headers)
        second_response = client.post("/api/v1/providers", json=payload, headers=headers)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Provider name already exists"
