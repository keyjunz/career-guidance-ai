from src.agent.state.agent_state import AgentRuntimeState

MAX_QUESTION_LENGTH = 5000


def apply_guardrails(state: AgentRuntimeState) -> None:
    question = state.question.strip()
    if not question:
        raise ValueError("question must not be empty")
    if len(question) > MAX_QUESTION_LENGTH:
        raise ValueError("question exceeds maximum length")
    if not any(char.isalnum() for char in question):
        raise ValueError("question must include letters or numbers")

    state.question = question
