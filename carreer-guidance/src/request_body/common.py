"""Common request/response models shared by API endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Standard error payload returned by API endpoints."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., examples=["VALIDATION_ERROR"])
    message: str = Field(..., examples=["Input validation failed"])
    details: dict[str, Any] | None = Field(default=None)
    trace_id: str | None = Field(default=None)
