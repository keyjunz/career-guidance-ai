from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


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
