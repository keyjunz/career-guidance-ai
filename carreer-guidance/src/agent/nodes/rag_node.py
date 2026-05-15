from typing import Any

from src.agent.state.agent_state import AgentRuntimeState


def run_rag(state: AgentRuntimeState, question: str | None = None) -> dict[str, Any]:
    from src.agent.tools.rag_tool import RAGTool

    q = (question or state.question).strip()
    if not q:
        raise ValueError("question is required for RAG tool")

    if state.rag_tool_client is None:
        state.rag_tool_client = RAGTool(execution_id=state.execution_id, user_id=state.user_id)
    
    state._active_llm = getattr(state.rag_tool_client, "llm_service", None)
    
    payload = state.rag_tool_client.run(q)
    if bool(payload.get("retrieval_cache_hit")):
        state.retrieval_cache_hit = True
    return payload
