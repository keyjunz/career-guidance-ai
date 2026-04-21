from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatRequest(BaseModel):
    """Incoming request for chat interaction."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    question: str = Field(..., min_length=1, max_length=5000)

    @model_validator(mode="after")
    def validate_payload(self) -> "ChatRequest":
        self.question = self.question.strip()
        if not self.question:
            raise ValueError("question must not be empty")
        return self
