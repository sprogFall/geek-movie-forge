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


def test_update_asset_allows_tags_for_image_and_text_edit_for_text() -> None:
    image_payload = {
        "asset_type": "image",
        "category": "reference",
        "name": "owner-image",
        "content_url": "https://cdn.example.com/assets/owner-image.png",
        "tags": ["a"],
    }
    text_payload = {
        "asset_type": "text",
        "category": "notes",
        "name": "owner-text",
        "content_text": "# hello",
        "tags": [],
    }

    with TestClient(app) as client:
        headers = register_and_get_headers(client, username="asset_update")
        image_res = client.post("/api/v1/assets", json=image_payload, headers=headers)
        text_res = client.post("/api/v1/assets", json=text_payload, headers=headers)
        image_id = image_res.json()["asset_id"]
        text_id = text_res.json()["asset_id"]

        image_update_ok = client.put(
            f"/api/v1/assets/{image_id}",
            json={"tags": ["a", "b"]},
            headers=headers,
        )
        image_update_bad = client.put(
            f"/api/v1/assets/{image_id}",
            json={"content_text": "nope"},
            headers=headers,
        )
        text_update_ok = client.put(
            f"/api/v1/assets/{text_id}",
            json={"tags": ["note"], "content_text": "# updated"},
            headers=headers,
        )

    assert image_res.status_code == 201
    assert text_res.status_code == 201
    assert image_update_ok.status_code == 200
    assert image_update_ok.json()["tags"] == ["a", "b"]
    assert image_update_bad.status_code == 400
    assert text_update_ok.status_code == 200
    assert text_update_ok.json()["content_text"] == "# updated"


def test_delete_asset_removes_from_list() -> None:
    payload = {
        "asset_type": "text",
        "category": "notes",
        "name": "to-delete",
        "content_text": "bye",
    }

    with TestClient(app) as client:
        headers = register_and_get_headers(client, username="asset_delete")
        create_response = client.post("/api/v1/assets", json=payload, headers=headers)
        asset_id = create_response.json()["asset_id"]
        delete_response = client.delete(f"/api/v1/assets/{asset_id}", headers=headers)
        list_response = client.get("/api/v1/assets", headers=headers)
        detail_response = client.get(f"/api/v1/assets/{asset_id}", headers=headers)

    assert create_response.status_code == 201
    assert delete_response.status_code == 204
    assert list_response.status_code == 200
    assert list_response.json()["items"] == []
    assert detail_response.status_code == 404
