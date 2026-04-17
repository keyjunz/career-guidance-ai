from collections.abc import Callable

from src.agent.nodes.cache_node import try_cached_answer
from src.agent.nodes.finalize_node import save_final_answer
from src.agent.nodes.prepare_node import prepare_request
from src.agent.nodes.rag_node import run_rag
from src.agent.prompts.status_prompts import STATUS_MESSAGES
from src.agent.state.agent_state import AgentRuntimeState
from src.agent.state.user_store import UserStore


def _push_status(
    state: AgentRuntimeState,
    store: UserStore,
    status_key: str,
    status_callback: Callable[[str], None] | None,
) -> None:
    text = STATUS_MESSAGES[status_key]
    state.status_history.append(text)
    store.append_status(state.execution_id, text)
    if status_callback is not None:
        status_callback(text)


def run_pipeline(
    state: AgentRuntimeState,
    store: UserStore,
    *,
    status_callback: Callable[[str], None] | None = None,
) -> AgentRuntimeState:
    _push_status(state, store, "received", status_callback)

    prepare_request(state, store)
    _push_status(state, store, "question_stored", status_callback)

    _push_status(state, store, "cache_checking", status_callback)
    cached = try_cached_answer(state, store)
    if cached is not None:
        state.cache_hit = True
        state.answer = str(cached.get("answer") or "")
        state.sources = list(cached.get("sources") or [])
        _push_status(state, store, "cache_hit", status_callback)
    else:
        _push_status(state, store, "rag_running", status_callback)
        rag_payload = run_rag(state)
        state.answer = str(rag_payload.get("answer") or "")
        state.sources = list(rag_payload.get("sources") or [])

    save_final_answer(state, store)
    _push_status(state, store, "answer_stored", status_callback)
    _push_status(state, store, "done", status_callback)
    return state
