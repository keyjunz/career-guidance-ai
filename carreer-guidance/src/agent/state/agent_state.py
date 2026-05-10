from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class AgentRuntimeState:
    user_id: str
    execution_id: str
    conversation_id: UUID
    question: str
    plan: str = "rag_only"
    plan_override: bool = False
    status_history: list[str] = field(default_factory=list)
    cache_hit: bool = False
    answer: str = ""
    sources: list[dict[str, Any]] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    tool_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    draft_answer: str = ""
    evaluation_score: float = 0.0
    evaluation_notes: list[str] = field(default_factory=list)
    retry_count: int = 0
    max_retry_count: int = 1
