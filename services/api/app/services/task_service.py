from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from packages.shared.contracts.tasks import TaskCreateRequest, TaskListResponse, TaskResponse
from packages.shared.enums.task_status import TaskStatus


class InMemoryTaskService:
    def __init__(self) -> None:
        self._tasks: dict[str, TaskResponse] = {}
        self._task_owners: dict[str, str] = {}

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
