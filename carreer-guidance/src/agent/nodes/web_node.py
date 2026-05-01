from typing import Any

from src.agent.state.agent_state import AgentRuntimeState


def run_web(state: AgentRuntimeState) -> dict[str, Any]:
    from src.agent.tools.web_tool import WebTool

    tool = WebTool(execution_id=state.execution_id, user_id=state.user_id)
    return tool.run(state.question)
