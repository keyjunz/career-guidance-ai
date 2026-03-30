"""Schemas for chat API requests and responses."""


from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class ContentItem(BaseModel):
    """A single chat response item that can be text or image."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["text", "image"]
    text: str | None = None
    image_url: HttpUrl | None = None

    @model_validator(mode="after")
    def validate_content_by_type(self) -> "ContentItem":
        if self.type == "text" and not self.text:
            raise ValueError("text is required when type='text'")
        if self.type == "text" and self.image_url is not None:
            raise ValueError("image_url must be None when type='text'")
        if self.type == "image" and self.image_url is None:
            raise ValueError("image_url is required when type='image'")
        if self.type == "image" and self.text is not None:
            raise ValueError("text must be None when type='image'")
        return self


class ChatRequest(BaseModel):
    """Incoming request for chat interaction."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    message: str | None = Field(default=None, max_length=5000)
    image_url: HttpUrl | None = None
    conversation_id: UUID | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "ChatRequest":
        msg = (self.message or "").strip()
        if self.message is not None:
            self.message = msg
        if not msg and self.image_url is None:
            raise ValueError("At least one of message or image_url must be provided")
        return self


class ChatResponse(BaseModel):
    """Structured response for chat endpoint."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["text", "image", "mixed"]
    content: list[ContentItem] = Field(default_factory=list)
    conversation_id: UUID
    trace_id: str
