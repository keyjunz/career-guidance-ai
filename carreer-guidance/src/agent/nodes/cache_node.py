from typing import Any

from src.agent.state.agent_state import AgentRuntimeState
from src.agent.state.user_store import UserStore


def try_cached_answer(
    state: AgentRuntimeState,
    store: UserStore,
) -> dict[str, Any] | None:
    return store.get_cached_answer(state.question)
