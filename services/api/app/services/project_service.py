from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from packages.db.models import ProjectRow
from packages.shared.contracts.projects import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
)
from packages.shared.enums.project_status import ProjectStatus


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


class InMemoryProjectService:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_project(self, owner_id: str, payload: ProjectCreateRequest) -> ProjectResponse:
        timestamp = datetime.now(UTC).isoformat()
        project_id = f"proj_{uuid4().hex[:12]}"

        with self._session_factory() as session:
            session.add(
                ProjectRow(
                    project_id=project_id,
                    owner_id=owner_id,
                    title=payload.title,
                    summary=payload.summary,
                    platform=payload.platform,
                    aspect_ratio=payload.aspect_ratio,
                    status=payload.status.value,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            )
            session.commit()

        return ProjectResponse(
            project_id=project_id,
            title=payload.title,
            summary=payload.summary,
            platform=payload.platform,
            aspect_ratio=payload.aspect_ratio,
            status=payload.status,
            created_at=_parse_timestamp(timestamp),
            updated_at=_parse_timestamp(timestamp),
        )

    def list_projects(self, owner_id: str) -> ProjectListResponse:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ProjectRow)
                .where(ProjectRow.owner_id == owner_id)
                .order_by(ProjectRow.created_at)
            ).all()
        return ProjectListResponse(items=[_to_response(row) for row in rows])

    def get_project(self, owner_id: str, project_id: str) -> ProjectResponse | None:
        with self._session_factory() as session:
            row = session.get(ProjectRow, project_id)
            if row is None or row.owner_id != owner_id:
                return None
            return _to_response(row)


def _to_response(row: ProjectRow) -> ProjectResponse:
    return ProjectResponse(
        project_id=row.project_id,
        title=row.title,
        summary=row.summary,
        platform=row.platform,
        aspect_ratio=row.aspect_ratio,
        status=ProjectStatus(row.status),
        created_at=_parse_timestamp(row.created_at),
        updated_at=_parse_timestamp(row.updated_at),
    )
