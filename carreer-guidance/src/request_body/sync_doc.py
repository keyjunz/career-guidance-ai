"""Schemas for document synchronization APIs."""


from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SyncDocumentsRequest(BaseModel):
    """Internal request model for sync operations."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    file_urls: list[str] = Field(min_length=1)
    download_dir: str | None = None
    industry_type: str | None = None


class SyncDocumentsResponse(BaseModel):
    """Job status payload after submitting sync request."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: str
    processed: int = 0
    failed: int = 0
    downloaded: int = 0
    total_pages: int = 0
    file_page_counts: dict[str, int] = Field(default_factory=dict)
    execution_time_ms: int = 0
