"""Schemas for document synchronization APIs."""


from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SyncDocumentsRequest(BaseModel):
    """Input payload to start a document synchronization job."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    file_urls: list[str] = Field(min_length=1)
    download_dir: str | None = None

    @field_validator("file_urls")
    @classmethod
    def validate_file_urls(cls, value: list[str]) -> list[str]:
        cleaned = [url.strip() for url in value]
        invalid = [
            url
            for url in cleaned
            if not (url.startswith("http://") or url.startswith("https://"))
        ]
        if invalid:
            raise ValueError("All file_urls must start with 'http://' or 'https://'")
        return cleaned

    @field_validator("download_dir")
    @classmethod
    def validate_download_dir(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("download_dir must be non-empty when provided")
        return cleaned


class SyncDocumentsResponse(BaseModel):
    """Job status payload after submitting sync request."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: str
    processed: int = 0
    failed: int = 0
    downloaded: int = 0
