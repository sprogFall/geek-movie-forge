from enum import Enum


class TaskStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    PROCESSING = "processing"
    WAITING_REVIEW = "waiting_review"
    COMPLETED = "completed"
    FAILED = "failed"
