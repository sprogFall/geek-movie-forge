from fastapi.testclient import TestClient

from services.api.app.main import app
from services.api.tests.helpers import register_and_get_headers


def test_create_project_returns_201_with_project_payload() -> None:
    payload = {
        "title": "Mars Echo teaser",
        "summary": "Sci-fi narration package with bilingual subtitles.",
        "platform": "douyin",
        "aspect_ratio": "9:16",
        "status": "active",
    }

    with TestClient(app) as client:
        headers = register_and_get_headers(client, username="project_creator")
        response = client.post("/api/v1/projects", json=payload, headers=headers)

    body = response.json()

    assert response.status_code == 201
    assert body["project_id"]
    assert body["title"] == payload["title"]
    assert body["summary"] == payload["summary"]
    assert body["platform"] == payload["platform"]
    assert body["aspect_ratio"] == payload["aspect_ratio"]
    assert body["status"] == payload["status"]
    assert body["created_at"]
    assert body["updated_at"]


def test_create_project_rejects_invalid_payload() -> None:
    payload = {
        "title": "",
        "summary": "",
        "platform": "douyin",
        "aspect_ratio": "9:16",
    }

    with TestClient(app) as client:
        headers = register_and_get_headers(client, username="project_invalid")
        response = client.post("/api/v1/projects", json=payload, headers=headers)

    assert response.status_code == 422


def test_list_projects_returns_only_current_user_projects() -> None:
    payload_owner = {
        "title": "Owner project",
        "summary": "Owner summary",
        "platform": "douyin",
        "aspect_ratio": "9:16",
    }
    payload_other = {
        "title": "Other project",
        "summary": "Other summary",
        "platform": "douyin",
        "aspect_ratio": "9:16",
    }

    with TestClient(app) as client:
        owner_headers = register_and_get_headers(client, username="project_list_owner")
        other_headers = register_and_get_headers(client, username="project_list_other")
        client.post("/api/v1/projects", json=payload_owner, headers=owner_headers)
        client.post("/api/v1/projects", json=payload_other, headers=other_headers)

        response = client.get("/api/v1/projects", headers=owner_headers)

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == payload_owner["title"]


def test_get_project_returns_existing_project() -> None:
    payload = {
        "title": "Project detail",
        "summary": "Project detail summary",
        "platform": "xiaohongshu",
        "aspect_ratio": "4:5",
    }

    with TestClient(app) as client:
        headers = register_and_get_headers(client, username="project_detail_user")
        create_response = client.post("/api/v1/projects", json=payload, headers=headers)
        project_id = create_response.json()["project_id"]

        response = client.get(f"/api/v1/projects/{project_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["project_id"] == project_id
    assert response.json()["title"] == payload["title"]


def test_get_project_returns_404_for_unknown_project() -> None:
    with TestClient(app) as client:
        headers = register_and_get_headers(client, username="project_missing_user")
        response = client.get("/api/v1/projects/proj_missing", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_project_access_is_isolated_per_user() -> None:
    payload = {
        "title": "Private project",
        "summary": "Only owner should see this project.",
        "platform": "douyin",
        "aspect_ratio": "9:16",
    }

    with TestClient(app) as client:
        owner_headers = register_and_get_headers(client, username="project_owner")
        other_headers = register_and_get_headers(client, username="project_viewer")
        create_response = client.post("/api/v1/projects", json=payload, headers=owner_headers)
        project_id = create_response.json()["project_id"]

        other_response = client.get(f"/api/v1/projects/{project_id}", headers=other_headers)
        other_list = client.get("/api/v1/projects", headers=other_headers)

    assert create_response.status_code == 201
    assert other_response.status_code == 404
    assert other_response.json()["detail"] == "Project not found"
    assert other_list.status_code == 200
    assert other_list.json()["items"] == []

