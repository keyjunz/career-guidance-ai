from concurrent.futures import ThreadPoolExecutor
import logging
from time import perf_counter
from typing import Any, Callable

from src.agent.nodes.rag_node import run_rag
from src.agent.nodes.web_node import run_web
from src.agent.state.agent_state import AgentRuntimeState

ToolCallable = Callable[[AgentRuntimeState], dict[str, Any]]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _safe_execute(
    state: AgentRuntimeState,
    tool_name: str,
    executor: ToolCallable,
) -> dict[str, Any]:
    started_at = perf_counter()
    logger.info(
        "[agent-tools] tool=%s started execution_id=%s",
        tool_name,
        state.execution_id,
    )
    try:
        payload = executor(state)
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
        if float(payload.get("latency_ms") or 0.0) <= 0.0:
            payload["latency_ms"] = (perf_counter() - started_at) * 1000
        logger.info(
            "[agent-tools] tool=%s finished execution_id=%s success=%s answer_len=%d source_count=%d image_count=%d latency_ms=%.2f",
            tool_name,
            state.execution_id,
            payload["success"],
            len(str(payload.get("answer") or "")),
            len(list(payload.get("sources") or [])),
            len(list(payload.get("images") or [])),
            float(payload.get("latency_ms") or 0.0),
        )
        return payload
    except Exception as exc:
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.exception(
            "[agent-tools] tool=%s failed execution_id=%s elapsed_ms=%.2f",
            tool_name,
            state.execution_id,
            elapsed_ms,
        )
        return {
            "tool_name": tool_name,
            "success": False,
            "answer": "",
            "sources": [],
            "images": [],
            "snippets": [],
            "latency_ms": elapsed_ms,
            "error": str(exc),
        }


def execute_tools(state: AgentRuntimeState) -> dict[str, dict[str, Any]]:
    logger.info(
        "[agent-tools] dispatch started execution_id=%s plan=%s",
        state.execution_id,
        state.plan,
    )
    if state.plan == "direct_answer":
        state.tool_results = {
            "direct": {
                "tool_name": "direct",
                "success": True,
                "answer": "Toi co the ho tro ban voi cau hoi nghe nghiep, ky nang, va thong tin tham khao tu web khi can.",
                "sources": [],
                "images": [],
                "snippets": [],
                "latency_ms": 0.0,
                "error": "",
            }
        }
        logger.info(
            "[agent-tools] dispatch direct answer execution_id=%s",
            state.execution_id,
        )
        return state.tool_results

    if state.plan == "rag_only":
        state.tool_results = {"rag": _safe_execute(state, "rag", run_rag)}
        logger.info(
            "[agent-tools] dispatch finished execution_id=%s tool_count=%d",
            state.execution_id,
            len(state.tool_results),
        )
        return state.tool_results

    if state.plan == "web_only":
        state.tool_results = {"web": _safe_execute(state, "web", run_web)}
        logger.info(
            "[agent-tools] dispatch finished execution_id=%s tool_count=%d",
            state.execution_id,
            len(state.tool_results),
        )
        return state.tool_results

    with ThreadPoolExecutor(max_workers=2) as pool:
        rag_future = pool.submit(_safe_execute, state, "rag", run_rag)
        web_future = pool.submit(_safe_execute, state, "web", run_web)
        state.tool_results = {
            "rag": rag_future.result(),
            "web": web_future.result(),
        }

    success_count = sum(
        1 for payload in state.tool_results.values() if payload.get("success")
    )
    logger.info(
        "[agent-tools] dispatch finished execution_id=%s tool_count=%d success_count=%d",
        state.execution_id,
        len(state.tool_results),
        success_count,
    )

    return state.tool_results
