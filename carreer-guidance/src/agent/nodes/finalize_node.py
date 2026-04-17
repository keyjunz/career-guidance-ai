from src.agent.state.agent_state import AgentRuntimeState
from src.agent.state.user_store import UserStore


def save_final_answer(state: AgentRuntimeState, store: UserStore) -> None:
    store.save_answer(
        execution_id=state.execution_id,
        conversation_id=state.conversation_id,
        question=state.question,
        answer=state.answer,
        sources=state.sources,
        cache_hit=state.cache_hit,
    )
