from fastapi.testclient import TestClient

from services.api.app.main import app
from services.api.tests.helpers import register_and_get_headers


def test_assets_are_isolated_per_user() -> None:
    payload = {
        "asset_type": "image",
        "category": "reference",
        "name": "owner-image",
        "content_url": "https://cdn.example.com/assets/owner-image.png",
    }

    with TestClient(app) as client:
        owner_headers = register_and_get_headers(client, username="asset_owner")
        other_headers = register_and_get_headers(client, username="asset_viewer")

        create_response = client.post("/api/v1/assets", json=payload, headers=owner_headers)
        asset_id = create_response.json()["asset_id"]

        owner_list_response = client.get("/api/v1/assets", headers=owner_headers)
        other_list_response = client.get("/api/v1/assets", headers=other_headers)
        other_detail_response = client.get(f"/api/v1/assets/{asset_id}", headers=other_headers)

    assert create_response.status_code == 201
    assert owner_list_response.status_code == 200
    assert len(owner_list_response.json()["items"]) == 1
    assert other_list_response.status_code == 200
    assert other_list_response.json()["items"] == []
    assert other_detail_response.status_code == 404


def test_create_asset_supports_origin_query_param() -> None:
    payload = {
        "asset_type": "text",
        "category": "generated",
        "name": "generated-text",
        "content_text": "hello",
    }

    with TestClient(app) as client:
        headers = register_and_get_headers(client, username="asset_origin")
        response = client.post("/api/v1/assets?origin=generated", json=payload, headers=headers)

    assert response.status_code == 201
    assert response.json()["origin"] == "generated"
