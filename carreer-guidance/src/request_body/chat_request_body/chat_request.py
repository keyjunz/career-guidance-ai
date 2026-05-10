from uuid import UUID
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatRequest(BaseModel):
    """Incoming request for chat interaction."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1, max_length=5000)
    plan: (
        Literal[
            "direct_answer",
            "rag_only",
            "web_only",
            "rag_web_parallel",
        ]
        | None
    ) = None
    # Injected from auth layer; keep it as a real field so ChatHandler can assign to it,
    # but hide it from Swagger/OpenAPI schema.
    user_id: UUID | None = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def validate_payload(self) -> "ChatRequest":
        self.question = self.question.strip()
        if not self.question:
            raise ValueError("question must not be empty")
        return self

    @classmethod
    def model_json_schema(cls, *args, **kwargs) -> dict:
        schema = super().model_json_schema(*args, **kwargs)
        schema.get("properties", {}).pop("user_id", None)
        return schema
