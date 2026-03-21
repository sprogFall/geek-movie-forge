from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, sessionmaker

from packages.db.models import VideoGenerationTaskRow
from packages.shared.contracts.generations import (
    MediaGenerationResponse,
    MultiVideoGenerationRequest,
    MultiVideoGenerationResponse,
    VideoGenerationRequest,
    VideoGenerationTaskListResponse,
    VideoGenerationTaskResponse,
)
from services.api.app.services.errors import NotFoundServiceError
from services.api.app.services.generation_service import GenerationService

logger = logging.getLogger(__name__)


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


class InMemoryVideoGenerationTaskService:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        generation_service: GenerationService,
    ) -> None:
        self._session_factory = session_factory
        self._generation_service = generation_service
        self._running_tasks: dict[str, asyncio.Task[None]] = {}
        self._mark_incomplete_tasks_as_interrupted()

    async def submit_single_video(
        self,
        owner_id: str,
        payload: VideoGenerationRequest,
    ) -> VideoGenerationTaskResponse:
        record = self._create_task_record(
            owner_id=owner_id,
            task_kind="single",
            provider_id=payload.provider_id,
            model=payload.model,
            prompt=payload.prompt,
            scene_prompt_texts=payload.scene_prompt_texts,
            requested_count=payload.count,
            requested_segment_count=None,
            request_summary=_build_task_request_summary(
                prompt=payload.prompt,
                scene_prompt_texts=payload.scene_prompt_texts,
            ),
        )
        self._spawn_background_task(
            task_id=record.task_id,
            runner=self._run_single_video_task,
            owner_id=owner_id,
            payload=payload.model_copy(deep=True),
        )
        return record

    async def submit_multi_video(
        self,
        owner_id: str,
        payload: MultiVideoGenerationRequest,
    ) -> VideoGenerationTaskResponse:
        record = self._create_task_record(
            owner_id=owner_id,
            task_kind="multi",
            provider_id=payload.provider_id,
            model=payload.model,
            prompt=payload.prompt,
            scene_prompt_texts=payload.scene_prompt_texts,
            requested_count=1,
            requested_segment_count=len(payload.segments),
            request_summary=_build_task_request_summary(
                prompt=payload.prompt,
                scene_prompt_texts=payload.scene_prompt_texts,
                segment_titles=[segment.title for segment in payload.segments],
            ),
        )
        self._spawn_background_task(
            task_id=record.task_id,
            runner=self._run_multi_video_task,
            owner_id=owner_id,
            payload=payload.model_copy(deep=True),
        )
        return record

    async def list_tasks(self, owner_id: str) -> VideoGenerationTaskListResponse:
        with self._session_factory() as session:
            rows = session.scalars(
                select(VideoGenerationTaskRow)
                .where(VideoGenerationTaskRow.owner_id == owner_id)
                .order_by(desc(VideoGenerationTaskRow.created_at))
            ).all()
        return VideoGenerationTaskListResponse(items=[_to_response(row) for row in rows])

    async def get_task(self, owner_id: str, task_id: str) -> VideoGenerationTaskResponse:
        with self._session_factory() as session:
            row = session.get(VideoGenerationTaskRow, task_id)
            if row is None or row.owner_id != owner_id:
                raise NotFoundServiceError("Video generation task not found")
            return _to_response(row)

    def _create_task_record(
        self,
        *,
        owner_id: str,
        task_kind: str,
        provider_id: str,
        model: str,
        prompt: str | None,
        scene_prompt_texts: list[str],
        requested_count: int,
        requested_segment_count: int | None,
        request_summary: str,
    ) -> VideoGenerationTaskResponse:
        now = datetime.now(UTC).isoformat()
        task_id = f"video_task_{uuid4().hex[:12]}"
        row = VideoGenerationTaskRow(
            task_id=task_id,
            owner_id=owner_id,
            task_kind=task_kind,
            status="queued",
            provider_id=provider_id,
            model=model,
            request_summary=request_summary[:200],
            prompt=prompt,
            scene_prompt_texts_json=list(scene_prompt_texts),
            requested_count=requested_count,
            requested_segment_count=requested_segment_count,
            error_detail=None,
            result_json=None,
            batch_result_json=None,
            created_at=now,
            updated_at=now,
        )
        with self._session_factory() as session:
            session.add(row)
            session.commit()
            session.refresh(row)
        return _to_response(row)

    def _spawn_background_task(self, *, task_id: str, runner, owner_id: str, payload) -> None:
        background_task = asyncio.create_task(runner(task_id, owner_id, payload))
        self._running_tasks[task_id] = background_task

        def _cleanup(done_task: asyncio.Task[None], *, current_task_id: str = task_id) -> None:
            self._running_tasks.pop(current_task_id, None)
            try:
                done_task.result()
            except Exception:
                logger.exception("Unhandled exception in background video generation task")

        background_task.add_done_callback(_cleanup)

    async def _run_single_video_task(
        self,
        task_id: str,
        owner_id: str,
        payload: VideoGenerationRequest,
    ) -> None:
        self._update_task_status(task_id, status="running")
        try:
            result = await self._generation_service.generate_video(owner_id, payload)
        except Exception as exc:
            self._fail_task(task_id, str(exc))
            return
        self._complete_task(task_id, result=result)

    async def _run_multi_video_task(
        self,
        task_id: str,
        owner_id: str,
        payload: MultiVideoGenerationRequest,
    ) -> None:
        self._update_task_status(task_id, status="running")
        try:
            batch_result = await self._generation_service.generate_multi_video(owner_id, payload)
        except Exception as exc:
            self._fail_task(task_id, str(exc))
            return
        self._complete_task(task_id, batch_result=batch_result)

    def _update_task_status(self, task_id: str, *, status: str) -> None:
        with self._session_factory() as session:
            row = session.get(VideoGenerationTaskRow, task_id)
            if row is None:
                return
            row.status = status
            row.updated_at = datetime.now(UTC).isoformat()
            session.commit()

    def _complete_task(
        self,
        task_id: str,
        *,
        result: MediaGenerationResponse | None = None,
        batch_result: MultiVideoGenerationResponse | None = None,
    ) -> None:
        with self._session_factory() as session:
            row = session.get(VideoGenerationTaskRow, task_id)
            if row is None:
                return
            row.status = "completed"
            row.result_json = result.model_dump(mode="json") if result is not None else None
            row.batch_result_json = (
                batch_result.model_dump(mode="json") if batch_result is not None else None
            )
            row.error_detail = None
            row.updated_at = datetime.now(UTC).isoformat()
            session.commit()

    def _fail_task(self, task_id: str, detail: str) -> None:
        with self._session_factory() as session:
            row = session.get(VideoGenerationTaskRow, task_id)
            if row is None:
                return
            row.status = "failed"
            row.error_detail = detail
            row.updated_at = datetime.now(UTC).isoformat()
            session.commit()

    def _mark_incomplete_tasks_as_interrupted(self) -> None:
        with self._session_factory() as session:
            rows = session.scalars(
                select(VideoGenerationTaskRow).where(
                    VideoGenerationTaskRow.status.in_(("queued", "running"))
                )
            ).all()
            if not rows:
                return
            now = datetime.now(UTC).isoformat()
            for row in rows:
                row.status = "failed"
                row.error_detail = (
                    "Task interrupted by service restart before completion"
                )
                row.updated_at = now
            session.commit()


def _to_response(row: VideoGenerationTaskRow) -> VideoGenerationTaskResponse:
    return VideoGenerationTaskResponse(
        task_id=row.task_id,
        task_kind=row.task_kind,
        status=row.status,
        provider_id=row.provider_id,
        model=row.model,
        request_summary=row.request_summary,
        prompt=row.prompt,
        scene_prompt_texts=list(row.scene_prompt_texts_json or []),
        requested_count=row.requested_count,
        requested_segment_count=row.requested_segment_count,
        error_detail=row.error_detail,
        result=MediaGenerationResponse.model_validate(row.result_json) if row.result_json else None,
        batch_result=(
            MultiVideoGenerationResponse.model_validate(row.batch_result_json)
            if row.batch_result_json
            else None
        ),
        created_at=_parse_timestamp(row.created_at),
        updated_at=_parse_timestamp(row.updated_at),
    )


def _build_task_request_summary(
    *,
    prompt: str | None,
    scene_prompt_texts: list[str],
    segment_titles: list[str] | None = None,
) -> str:
    prompt_value = (prompt or "").strip()
    if prompt_value:
        return prompt_value[:160]
    first_scene_text = next((item.strip() for item in scene_prompt_texts if item.strip()), "")
    if first_scene_text:
        return first_scene_text[:160]
    if segment_titles:
        joined = " / ".join(item.strip() for item in segment_titles if item.strip())
        if joined:
            return joined[:160]
    return "视频生成任务"
