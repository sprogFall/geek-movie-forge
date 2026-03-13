from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from packages.shared.contracts.projects import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectRecord,
    ProjectResponse,
)
from services.api.app.core.store import JsonFileStore

_NAMESPACE = "projects"


class InMemoryProjectService:
    def __init__(self, *, store: JsonFileStore | None = None) -> None:
        self._projects: dict[str, ProjectRecord] = {}
        self._store = store
        self._load()

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
        self._persist()
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

    def _persist(self) -> None:
        if self._store is None:
            return
        data = {k: v.model_dump(mode="json") for k, v in self._projects.items()}
        self._store.save(_NAMESPACE, data)

    def _load(self) -> None:
        if self._store is None:
            return
        data = self._store.load(_NAMESPACE)
        if data is None:
            return
        for key, value in data.items():
            try:
                self._projects[key] = ProjectRecord(**value)
            except Exception:
                logging.getLogger(__name__).warning(
                    "Skipping corrupt project entry %s", key
                )
