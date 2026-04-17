from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class AgentRuntimeState:
    user_id: str
    execution_id: str
    conversation_id: UUID
    question: str
    status_history: list[str] = field(default_factory=list)
    cache_hit: bool = False
    answer: str = ""
    sources: list[dict[str, Any]] = field(default_factory=list)
