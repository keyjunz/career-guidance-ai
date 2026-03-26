"""Schemas for sync document module orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

JobStatus = Literal["start", "processing", "failed", "completed"]


@dataclass(slots=True)
class SyncExecutionSummary:
    ingestion_job_id: str
    downloaded: int
    processed: int
    failed: int
    status: JobStatus
    execution_id: str
