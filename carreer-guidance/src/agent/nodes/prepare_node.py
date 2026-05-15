import logging

from src.agent.state.agent_state import AgentRuntimeState
from src.agent.state.user_store import UserStore
from src.services.llm_service.main import LLMService

logger = logging.getLogger(__name__)

MAX_HISTORY_TURNS = 3
MAX_HISTORY_CHARS = 1200


def _format_history(history: list[dict]) -> str:
    parts: list[str] = []
    for item in history:
        user_msg = str(item.get("question") or "").strip()
        assistant_msg = str(item.get("answer") or "").strip()
        if user_msg:
            parts.append(f"User: {user_msg}")
        if assistant_msg:
            parts.append(f"Assistant: {assistant_msg}")
    compact = "\n".join(parts).strip()
    if len(compact) <= MAX_HISTORY_CHARS:
        return compact
    return compact[-MAX_HISTORY_CHARS:]


def _rewrite_question_with_history(
    *,
    question: str,
    history_context: str,
    execution_id: str,
) -> str:
    prompt = (
        "Rewrite the user's question into a standalone question using the chat history. "
        "Resolve pronouns and references. Keep the original language. "
        "Return only the rewritten question.\n\n"
        f"CHAT HISTORY:\n{history_context}\n\n"
        f"USER QUESTION:\n{question}\n\n"
        "STANDALONE QUESTION:"
    )
    try:
        llm = LLMService(
            execution_id=execution_id, api_key_env_override="GEMINI_AGENT_API_KEY"
        )
        result = llm.generate_raw(prompt=prompt, max_tokens=120, temperature=0.0)
        llm.unload()
        rewritten = str(result.get("answer") or "").strip()
        if rewritten and not rewritten.startswith("[API Error]"):
            return rewritten
    except Exception as exc:
        logger.warning("Question rewrite failed: %s", exc)
    return question


def prepare_request(state: AgentRuntimeState, store: UserStore) -> None:
    question = state.question.strip()
    if not question:
        raise ValueError("message is required for text chat")

    state.question = question
    state.resolved_question = question
    state.history_context = None

    history = store.get_recent_history(
        conversation_id=str(state.conversation_id),
        limit=MAX_HISTORY_TURNS,
    )
    history_context = _format_history(history)
    if history_context:
        state.history_context = history_context
        state.resolved_question = _rewrite_question_with_history(
            question=question,
            history_context=history_context,
            execution_id=state.execution_id,
        )

    store.stage_question(
        execution_id=state.execution_id,
        conversation_id=state.conversation_id,
        question=question,
    )
