from typing import Any

from src.agent.nodes.draft_node import compose_draft_answer
from src.agent.nodes.rag_node import run_rag
from src.agent.nodes.web_node import run_web
from src.agent.state.agent_state import AgentRuntimeState


def _retry_tool(tool_name: str, state: AgentRuntimeState) -> dict[str, Any]:
    try:
        if tool_name == "rag":
            payload = run_rag(state)
        else:
            payload = run_web(state)

        if not isinstance(payload, dict):
            payload = {"answer": str(payload)}

        payload.setdefault("answer", "")
        payload.setdefault("sources", [])
        payload.setdefault("images", [])
        payload.setdefault("snippets", [])
        payload.setdefault("latency_ms", 0.0)
        payload["success"] = True
        payload["tool_name"] = tool_name
        payload["error"] = ""
        return payload
    except Exception as exc:
        return {
            "tool_name": tool_name,
            "success": False,
            "answer": "",
            "sources": [],
            "images": [],
            "snippets": [],
            "latency_ms": 0.0,
            "error": str(exc),
        }


def run_fixer(state: AgentRuntimeState) -> None:
    state.retry_count += 1

    if state.plan in {"rag_only", "rag_web_parallel"}:
        rag_payload = state.tool_results.get("rag", {})
        if not rag_payload.get("success"):
            state.tool_results["rag"] = _retry_tool("rag", state)

    if state.plan in {"web_only", "rag_web_parallel"}:
        web_payload = state.tool_results.get("web", {})
        if not web_payload.get("success"):
            state.tool_results["web"] = _retry_tool("web", state)

    compose_draft_answer(state)
