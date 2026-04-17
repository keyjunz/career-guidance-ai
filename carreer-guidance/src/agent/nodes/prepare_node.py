from src.agent.state.agent_state import AgentRuntimeState
from src.agent.state.user_store import UserStore


def prepare_request(state: AgentRuntimeState, store: UserStore) -> None:
    question = state.question.strip()
    if not question:
        raise ValueError("message is required for text chat")

    state.question = question
    store.stage_question(
        execution_id=state.execution_id,
        conversation_id=state.conversation_id,
        question=question,
    )
