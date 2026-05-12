from typing import Any

from src.agent.state.agent_state import AgentRuntimeState


def run_web(state: AgentRuntimeState, question: str | None = None) -> dict[str, Any]:
    from src.agent.tools.web_tool import WebTool

    q = (question or state.question).strip()
    if not q:
        raise ValueError("question is required for web tool")

    if state.web_tool_client is None:
        state.web_tool_client = WebTool(execution_id=state.execution_id, user_id=state.user_id)
    return state.web_tool_client.run(q)
