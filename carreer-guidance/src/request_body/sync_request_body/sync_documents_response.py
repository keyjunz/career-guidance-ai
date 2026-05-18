from pydantic import BaseModel, ConfigDict, Field


class SyncDocumentsResponse(BaseModel):
    """Job status payload after submitting sync request."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: str
    processed: int = 0
    failed: int = 0
    downloaded: int = 0
    skipped: int = 0
    total_pages: int = 0
    file_page_counts: dict[str, int] = Field(default_factory=dict)
    execution_time_ms: int = 0
