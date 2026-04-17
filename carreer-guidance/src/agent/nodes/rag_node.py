from typing import Any

from src.agent.state.agent_state import AgentRuntimeState


def run_rag(state: AgentRuntimeState) -> dict[str, Any]:
    from src.agent.tools.rag_tool import RAGTool

    tool = RAGTool(execution_id=state.execution_id, user_id=state.user_id)
    return tool.run(state.question)
