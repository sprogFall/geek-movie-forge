from __future__ import annotations

from uuid import uuid4

from packages.shared.contracts.tasks import TaskCreateRequest, TaskResponse
from packages.shared.enums.task_status import TaskStatus


class InMemoryTaskService:
    def __init__(self) -> None:
        self._tasks: dict[str, TaskResponse] = {}

    def create_task(self, payload: TaskCreateRequest) -> TaskResponse:
        task = TaskResponse(
            task_id=f"task_{uuid4().hex[:12]}",
            project_id=payload.project_id,
            title=payload.title,
            source_text=payload.source_text,
            platform=payload.platform,
            status=TaskStatus.DRAFT,
        )
        self._tasks[task.task_id] = task
        return task

    def get_task(self, task_id: str) -> TaskResponse | None:
        return self._tasks.get(task_id)
