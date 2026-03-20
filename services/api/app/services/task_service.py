from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from packages.db.models import TaskRow
from packages.shared.contracts.tasks import TaskCreateRequest, TaskListResponse, TaskResponse
from packages.shared.enums.task_status import TaskStatus


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


class InMemoryTaskService:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_task(self, owner_id: str, payload: TaskCreateRequest) -> TaskResponse:
        created_at = datetime.now(UTC).isoformat()
        task_id = f"task_{uuid4().hex[:12]}"

        with self._session_factory() as session:
            session.add(
                TaskRow(
                    task_id=task_id,
                    owner_id=owner_id,
                    project_id=payload.project_id,
                    title=payload.title,
                    source_text=payload.source_text,
                    platform=payload.platform,
                    status=TaskStatus.DRAFT.value,
                    created_at=created_at,
                )
            )
            session.commit()

        return TaskResponse(
            task_id=task_id,
            project_id=payload.project_id,
            title=payload.title,
            source_text=payload.source_text,
            platform=payload.platform,
            status=TaskStatus.DRAFT,
            created_at=_parse_timestamp(created_at),
        )

    def get_task(self, owner_id: str, task_id: str) -> TaskResponse | None:
        with self._session_factory() as session:
            row = session.get(TaskRow, task_id)
            if row is None or row.owner_id != owner_id:
                return None
            return _to_response(row)

    def list_tasks(
        self,
        *,
        owner_id: str,
        project_id: str | None = None,
        status: TaskStatus | None = None,
    ) -> TaskListResponse:
        stmt = select(TaskRow).where(TaskRow.owner_id == owner_id)
        if project_id is not None:
            stmt = stmt.where(TaskRow.project_id == project_id)
        if status is not None:
            stmt = stmt.where(TaskRow.status == status.value)
        stmt = stmt.order_by(TaskRow.created_at)

        with self._session_factory() as session:
            rows = session.scalars(stmt).all()
        return TaskListResponse(items=[_to_response(row) for row in rows])


def _to_response(row: TaskRow) -> TaskResponse:
    return TaskResponse(
        task_id=row.task_id,
        project_id=row.project_id,
        title=row.title,
        source_text=row.source_text,
        platform=row.platform,
        status=TaskStatus(row.status),
        created_at=_parse_timestamp(row.created_at),
    )
