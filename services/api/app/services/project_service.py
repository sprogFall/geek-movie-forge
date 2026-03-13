from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from packages.shared.contracts.projects import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectRecord,
    ProjectResponse,
)


class InMemoryProjectService:
    def __init__(self) -> None:
        self._projects: dict[str, ProjectRecord] = {}

    def create_project(self, owner_id: str, payload: ProjectCreateRequest) -> ProjectResponse:
        timestamp = datetime.now(UTC)
        record = ProjectRecord(
            project_id=f"proj_{uuid4().hex[:12]}",
            owner_id=owner_id,
            title=payload.title,
            summary=payload.summary,
            platform=payload.platform,
            aspect_ratio=payload.aspect_ratio,
            status=payload.status,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._projects[record.project_id] = record
        return record.to_response()

    def list_projects(self, owner_id: str) -> ProjectListResponse:
        items = [
            record.to_response()
            for record in self._projects.values()
            if record.owner_id == owner_id
        ]
        items.sort(key=lambda item: item.created_at)
        return ProjectListResponse(items=items)

    def get_project(self, owner_id: str, project_id: str) -> ProjectResponse | None:
        record = self._projects.get(project_id)
        if record is None or record.owner_id != owner_id:
            return None
        return record.to_response()

