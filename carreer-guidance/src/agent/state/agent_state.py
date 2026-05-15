from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class AgentRuntimeState:
    user_id: str
    execution_id: str
    conversation_id: UUID
    question: str
    resolved_question: str | None = None
    history_context: str | None = None
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
    has_tool_errors: bool = False
    cacheable: bool = True
    # Reuse RAG / Web tool clients within one pipeline run (multi-intent + fixer).
    rag_tool_client: Any | None = None
    web_tool_client: Any | None = None
    # Hybrid retrieval cache hit for any RAG call in this execution (UI + metrics).
    retrieval_cache_hit: bool = False
    # Internal per-run token accounting; used by DB persistence after streaming.
    token_usage: Any | None = None
    # Multi-intent decomposition
    multi_intent: bool = False
    sub_queries: list[dict[str, Any]] = field(default_factory=list)
    tool_results_by_intent: dict[str, dict[str, Any]] = field(default_factory=dict)
    answer_sections: list[dict[str, Any]] = field(default_factory=list)
    _cancel_event: Any | None = field(default=None, repr=False, compare=False)
    _active_llm: Any | None = field(default=None, repr=False, compare=False)

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set() if self._cancel_event else False

    def cancel(self) -> None:
        if self._cancel_event:
            self._cancel_event.set()
        if self._active_llm and hasattr(self._active_llm, "unload"):
            try:
                self._active_llm.unload()
            except Exception:
                pass
