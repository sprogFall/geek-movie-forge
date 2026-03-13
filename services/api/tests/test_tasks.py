from fastapi.testclient import TestClient

from services.api.app.main import app


def test_create_task_returns_201_with_task_payload() -> None:
    payload = {
        "project_id": "proj_001",
        "title": "Generate sci-fi teaser",
        "source_text": "A captain searches a silent planet.",
        "platform": "douyin",
    }

    with TestClient(app) as client:
        response = client.post("/api/v1/tasks", json=payload)

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
        response = client.post("/api/v1/tasks", json=payload)

    assert response.status_code == 422


def test_get_task_returns_existing_task() -> None:
    payload = {
        "project_id": "proj_002",
        "title": "Generate fantasy trailer",
        "source_text": "A dragon guards the last gate.",
        "platform": "xiaohongshu",
    }

    with TestClient(app) as client:
        create_response = client.post("/api/v1/tasks", json=payload)
        task_id = create_response.json()["task_id"]
        response = client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200
    assert response.json()["task_id"] == task_id
    assert response.json()["title"] == payload["title"]


def test_get_task_returns_404_for_unknown_task() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/tasks/task_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"
