from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from packages.shared.contracts.tasks import TaskCreateRequest, TaskListResponse, TaskResponse
from packages.shared.enums.task_status import TaskStatus
from services.api.app.core.store import JsonFileStore

_NAMESPACE = "tasks"


class InMemoryTaskService:
    def __init__(self, *, store: JsonFileStore | None = None) -> None:
        self._tasks: dict[str, TaskResponse] = {}
        self._task_owners: dict[str, str] = {}
        self._store = store
        self._load()

    def create_task(self, owner_id: str, payload: TaskCreateRequest) -> TaskResponse:
        created_at = datetime.now(UTC)
        task = TaskResponse(
            task_id=f"task_{uuid4().hex[:12]}",
            project_id=payload.project_id,
            title=payload.title,
            source_text=payload.source_text,
            platform=payload.platform,
            status=TaskStatus.DRAFT,
            created_at=created_at,
        )
        self._tasks[task.task_id] = task
        self._task_owners[task.task_id] = owner_id
        self._persist()
        return task

    def get_task(self, owner_id: str, task_id: str) -> TaskResponse | None:
        task = self._tasks.get(task_id)
        if task is None or self._task_owners.get(task_id) != owner_id:
            return None
        return task

    def list_tasks(
        self,
        *,
        owner_id: str,
        project_id: str | None = None,
        status: TaskStatus | None = None,
    ) -> TaskListResponse:
        items = [
            task
            for task_id, task in self._tasks.items()
            if self._task_owners.get(task_id) == owner_id
        ]
        if project_id is not None:
            items = [task for task in items if task.project_id == project_id]
        if status is not None:
            items = [task for task in items if task.status == status]
        items.sort(key=lambda item: item.created_at)
        return TaskListResponse(items=items)

    def _persist(self) -> None:
        if self._store is None:
            return
        data = {
            "tasks": {k: v.model_dump(mode="json") for k, v in self._tasks.items()},
            "owners": self._task_owners,
        }
        self._store.save(_NAMESPACE, data)

    def _load(self) -> None:
        if self._store is None:
            return
        data = self._store.load(_NAMESPACE)
        if data is None:
            return
        for key, value in data.get("tasks", {}).items():
            try:
                self._tasks[key] = TaskResponse(**value)
            except Exception:
                logging.getLogger(__name__).warning(
                    "Skipping corrupt task entry %s", key
                )
        self._task_owners = data.get("owners", {})
