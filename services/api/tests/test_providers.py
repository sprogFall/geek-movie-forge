from fastapi.testclient import TestClient

from services.api.app.main import app
from services.api.tests.helpers import register_and_get_headers


def _find_builtin_modelscope(items: list[dict]) -> dict:
    return next(item for item in items if item["is_builtin"] and item["adapter_type"] == "modelscope")


def _find_custom_provider(items: list[dict], provider_id: str) -> dict:
    return next(item for item in items if item["provider_id"] == provider_id)


def test_list_providers_includes_builtin_modelscope_provider() -> None:
    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        response = client.get("/api/v1/providers", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) >= 1
    builtin = _find_builtin_modelscope(body["items"])
    assert builtin["name"] == "魔搭 ModelScope"
    assert builtin["base_url"].rstrip("/") == "https://api-inference.modelscope.cn"
    assert builtin["routes"]["text"]["path"] == "/v1/chat/completions"
    assert builtin["routes"]["image"]["path"] == "/v1/images/generations"


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
        assert body["is_builtin"] is False

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
    assert _find_custom_provider(list_response.json()["items"], provider_id)["provider_id"] == provider_id


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


def test_provider_configuration_is_isolated_per_user() -> None:
    payload = {
        "name": "Shared Name Provider",
        "base_url": "https://provider.example.com/v1",
        "api_key": "super-secret-key",
        "models": [{"model": "forge-image-v1", "capabilities": ["image"]}],
    }

    with TestClient(app) as client:
        owner_headers = register_and_get_headers(client, username="provider_owner")
        other_headers = register_and_get_headers(client, username="provider_viewer")

        create_response = client.post("/api/v1/providers", json=payload, headers=owner_headers)
        provider_id = create_response.json()["provider_id"]

        other_list_response = client.get("/api/v1/providers", headers=other_headers)
        other_detail_response = client.get(
            f"/api/v1/providers/{provider_id}", headers=other_headers
        )
        other_update_response = client.put(
            f"/api/v1/providers/{provider_id}",
            json={"base_url": "https://provider.example.com/private"},
            headers=other_headers,
        )
        other_create_response = client.post(
            "/api/v1/providers", json=payload, headers=other_headers
        )

    assert create_response.status_code == 201
    assert other_list_response.status_code == 200
    assert len(other_list_response.json()["items"]) == 1
    assert _find_builtin_modelscope(other_list_response.json()["items"])["is_builtin"] is True
    assert other_detail_response.status_code == 404
    assert other_update_response.status_code == 404
    assert other_create_response.status_code == 201


def test_delete_provider_returns_204_and_removes_from_list() -> None:
    payload = {
        "name": "Delete Me Provider",
        "base_url": "https://provider.example.com/v1",
        "api_key": "super-secret-key",
        "models": [{"model": "forge-image-v1", "capabilities": ["image"]}],
    }

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        create_response = client.post("/api/v1/providers", json=payload, headers=headers)
        provider_id = create_response.json()["provider_id"]

        delete_response = client.delete(f"/api/v1/providers/{provider_id}", headers=headers)
        list_response = client.get("/api/v1/providers", headers=headers)

    assert delete_response.status_code == 204
    items = list_response.json()["items"]
    assert len(items) == 1
    assert _find_builtin_modelscope(items)["is_builtin"] is True


def test_delete_nonexistent_provider_returns_404() -> None:
    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        response = client.delete("/api/v1/providers/provider_nonexistent", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Provider not found"


def test_delete_builtin_provider_returns_409() -> None:
    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        list_response = client.get("/api/v1/providers", headers=headers)
        builtin_id = _find_builtin_modelscope(list_response.json()["items"])["provider_id"]
        delete_response = client.delete(f"/api/v1/providers/{builtin_id}", headers=headers)

    assert delete_response.status_code == 409
    assert delete_response.json()["detail"] == "Built-in provider cannot be deleted"


def test_update_builtin_provider_keeps_builtin_marker() -> None:
    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        list_response = client.get("/api/v1/providers", headers=headers)
        builtin = _find_builtin_modelscope(list_response.json()["items"])

        update_response = client.put(
            f"/api/v1/providers/{builtin['provider_id']}",
            json={"api_key": "ms-updated-token-123456", "name": "魔搭 ModelScope 主账号"},
            headers=headers,
        )
        detail_response = client.get(
            f"/api/v1/providers/{builtin['provider_id']}",
            headers=headers,
        )
        delete_response = client.delete(
            f"/api/v1/providers/{builtin['provider_id']}",
            headers=headers,
        )

    assert update_response.status_code == 200
    assert update_response.json()["is_builtin"] is True
    assert update_response.json()["name"] == "魔搭 ModelScope 主账号"
    assert detail_response.status_code == 200
    assert detail_response.json()["is_builtin"] is True
    assert delete_response.status_code == 409


def test_delete_other_users_provider_returns_404() -> None:
    payload = {
        "name": "Private Provider",
        "base_url": "https://provider.example.com/v1",
        "api_key": "super-secret-key",
        "models": [{"model": "forge-image-v1", "capabilities": ["image"]}],
    }

    with TestClient(app) as client:
        owner_headers = register_and_get_headers(client, username="delete_owner")
        other_headers = register_and_get_headers(client, username="delete_other")

        create_response = client.post("/api/v1/providers", json=payload, headers=owner_headers)
        provider_id = create_response.json()["provider_id"]

        delete_response = client.delete(
            f"/api/v1/providers/{provider_id}", headers=other_headers
        )
        owner_list = client.get("/api/v1/providers", headers=owner_headers)

    assert delete_response.status_code == 404
    assert len(owner_list.json()["items"]) == 2


def test_can_recreate_provider_with_same_name_after_delete() -> None:
    payload = {
        "name": "Recyclable Provider",
        "base_url": "https://provider.example.com/v1",
        "api_key": "super-secret-key",
        "models": [{"model": "forge-image-v1", "capabilities": ["image"]}],
    }

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        first_create = client.post("/api/v1/providers", json=payload, headers=headers)
        provider_id = first_create.json()["provider_id"]

        client.delete(f"/api/v1/providers/{provider_id}", headers=headers)
        second_create = client.post("/api/v1/providers", json=payload, headers=headers)

    assert first_create.status_code == 201
    assert second_create.status_code == 201
    assert second_create.json()["provider_id"] != provider_id
