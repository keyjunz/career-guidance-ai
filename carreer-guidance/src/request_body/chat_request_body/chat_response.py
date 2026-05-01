from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.request_body.chat_request_body.content_item import ContentItem


class ChatResponse(BaseModel):
    """Structured response for chat endpoint."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["text", "image", "mixed"]
    content: list[ContentItem] = Field(default_factory=list)
    conversation_id: UUID
    execution_id: str
    statuses: list[str] = Field(default_factory=list)
    cached: bool = False
