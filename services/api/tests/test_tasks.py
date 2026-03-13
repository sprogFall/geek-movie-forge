from fastapi.testclient import TestClient

from services.api.app.main import app
from services.api.tests.helpers import register_and_get_headers


def test_create_task_returns_201_with_task_payload() -> None:
    payload = {
        "project_id": "proj_001",
        "title": "Generate sci-fi teaser",
        "source_text": "A captain searches a silent planet.",
        "platform": "douyin",
    }

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        response = client.post("/api/v1/tasks", json=payload, headers=headers)

    body = response.json()

    assert response.status_code == 201
    assert body["project_id"] == payload["project_id"]
    assert body["title"] == payload["title"]
    assert body["source_text"] == payload["source_text"]
    assert body["platform"] == payload["platform"]
    assert body["status"] == "draft"
    assert body["task_id"]


def test_create_task_rejects_invalid_payload() -> None:
    payload = {
        "project_id": "proj_001",
        "title": "",
        "source_text": "",
        "platform": "douyin",
    }

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        response = client.post("/api/v1/tasks", json=payload, headers=headers)

    assert response.status_code == 422


def test_get_task_returns_existing_task() -> None:
    payload = {
        "project_id": "proj_002",
        "title": "Generate fantasy trailer",
        "source_text": "A dragon guards the last gate.",
        "platform": "xiaohongshu",
    }

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        create_response = client.post("/api/v1/tasks", json=payload, headers=headers)
        task_id = create_response.json()["task_id"]
        response = client.get(f"/api/v1/tasks/{task_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["task_id"] == task_id
    assert response.json()["title"] == payload["title"]


def test_get_task_returns_404_for_unknown_task() -> None:
    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        response = client.get("/api/v1/tasks/task_missing", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_task_access_is_isolated_per_user() -> None:
    payload = {
        "project_id": "proj_003",
        "title": "Private task",
        "source_text": "Only owner should see this task.",
        "platform": "douyin",
    }

    with TestClient(app) as client:
        owner_headers = register_and_get_headers(client, username="task_owner")
        other_headers = register_and_get_headers(client, username="task_viewer")
        create_response = client.post("/api/v1/tasks", json=payload, headers=owner_headers)
        task_id = create_response.json()["task_id"]

        other_response = client.get(f"/api/v1/tasks/{task_id}", headers=other_headers)

    assert create_response.status_code == 201
    assert other_response.status_code == 404
    assert other_response.json()["detail"] == "Task not found"


def test_list_tasks_returns_tasks_for_current_user_only() -> None:
    payload_owner = {
        "project_id": "proj_owner",
        "title": "Owner task",
        "source_text": "Owner source text",
        "platform": "douyin",
    }
    payload_other = {
        "project_id": "proj_other",
        "title": "Other task",
        "source_text": "Other source text",
        "platform": "douyin",
    }

    with TestClient(app) as client:
        owner_headers = register_and_get_headers(client, username="task_list_owner")
        other_headers = register_and_get_headers(client, username="task_list_other")
        client.post("/api/v1/tasks", json=payload_owner, headers=owner_headers)
        client.post("/api/v1/tasks", json=payload_other, headers=other_headers)

        response = client.get("/api/v1/tasks", headers=owner_headers)

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == payload_owner["title"]


def test_list_tasks_supports_filtering_by_project_id() -> None:
    payload_a = {
        "project_id": "proj_a",
        "title": "Task A",
        "source_text": "Text A",
        "platform": "douyin",
    }
    payload_b = {
        "project_id": "proj_b",
        "title": "Task B",
        "source_text": "Text B",
        "platform": "douyin",
    }

    with TestClient(app) as client:
        headers = register_and_get_headers(client, username="task_filter_user")
        client.post("/api/v1/tasks", json=payload_a, headers=headers)
        client.post("/api/v1/tasks", json=payload_b, headers=headers)

        response = client.get("/api/v1/tasks", params={"project_id": "proj_b"}, headers=headers)

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["project_id"] == "proj_b"


def test_list_tasks_rejects_invalid_status_filter() -> None:
    with TestClient(app) as client:
        headers = register_and_get_headers(client, username="task_invalid_status")
        response = client.get("/api/v1/tasks", params={"status": "not-a-real-status"}, headers=headers)

    assert response.status_code == 422
