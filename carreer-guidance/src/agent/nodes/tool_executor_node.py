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


def _looks_vietnamese(text: str) -> bool:
    normalized = str(text or "").lower()
    vi_markers = (
        "ă",
        "â",
        "đ",
        "ê",
        "ô",
        "ơ",
        "ư",
        "chào",
        "chao",
        "xin chao",
        "cảm ơn",
        "cam on",
        "nghề nghiệp",
        "tư vấn",
    )
    return any(marker in normalized for marker in vi_markers)


def _is_insufficient_rag(payload: dict[str, Any]) -> bool:
    if not payload.get("success"):
        return True

    answer = str(payload.get("answer") or "").strip().lower()
    sources = list(payload.get("sources") or [])
    snippets = list(payload.get("snippets") or [])
    weak_signals = (
        "no relevant data found",
        "context is insufficient",
        "does not contain",
        "cannot answer",
        "i don't have enough information",
        "khong tim thay",
        "không tìm thấy",
        "khong co thong tin",
        "không có thông tin",
    )

    if not answer:
        return True
    if any(signal in answer for signal in weak_signals):
        return True
    if not sources and not snippets:
        return True
    return False


def _is_insufficient_answer_text(text: str) -> bool:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return True
    weak_signals = (
        "provided context does not contain",
        "cannot answer your question",
        "no relevant data found",
        "context is insufficient",
        "i don't have enough information",
        "khong tim thay",
        "không tìm thấy",
        "khong co thong tin",
        "không có thông tin",
    )
    return any(signal in normalized for signal in weak_signals)


def _merge_parallel_answers(
    rag_payload: dict[str, Any], web_payload: dict[str, Any]
) -> str:
    rag_answer = str(rag_payload.get("answer") or "").strip()
    web_answer = str(web_payload.get("answer") or "").strip()
    rag_ok = bool(rag_payload.get("success")) and not _is_insufficient_answer_text(
        rag_answer
    )
    web_ok = bool(web_payload.get("success")) and not _is_insufficient_answer_text(
        web_answer
    )
    if rag_ok and web_ok:
        return (
            web_answer if _is_insufficient_answer_text(rag_answer) else rag_answer
        )
    if rag_ok:
        return rag_answer
    if web_ok:
        return web_answer
    if bool(rag_payload.get("success")) and rag_answer:
        return rag_answer
    if bool(web_payload.get("success")) and web_answer:
        return web_answer
    return ""


def _intent_bundle_from_rag(
    sub: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    return {
        "intent_id": sub["intent_id"],
        "mode": "rag",
        "success": bool(payload.get("success")),
        "answer": str(payload.get("answer") or ""),
        "sources": list(payload.get("sources") or []),
        "images": list(payload.get("images") or []),
        "snippets": list(payload.get("snippets") or []),
        "latency_ms": float(payload.get("latency_ms") or 0.0),
        "error": str(payload.get("error") or ""),
        "retrieval_cache_hit": bool(payload.get("retrieval_cache_hit")),
    }


def _intent_bundle_from_web(
    sub: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    return {
        "intent_id": sub["intent_id"],
        "mode": "web",
        "success": bool(payload.get("success")),
        "answer": str(payload.get("answer") or ""),
        "sources": list(payload.get("sources") or []),
        "images": list(payload.get("images") or []),
        "snippets": list(payload.get("snippets") or []),
        "latency_ms": float(payload.get("latency_ms") or 0.0),
        "error": str(payload.get("error") or ""),
        "retrieval_cache_hit": False,
    }


def _intent_bundle_from_both(
    sub: dict[str, Any], rag_payload: dict[str, Any], web_payload: dict[str, Any]
) -> dict[str, Any]:
    merged = _merge_parallel_answers(rag_payload, web_payload)
    rag_sources = list(rag_payload.get("sources") or [])
    web_sources = list(web_payload.get("sources") or [])
    merged_sources = rag_sources + web_sources
    rag_images = list(rag_payload.get("images") or [])
    web_images = list(web_payload.get("images") or [])
    success = bool(rag_payload.get("success") or web_payload.get("success"))
    return {
        "intent_id": sub["intent_id"],
        "mode": "both",
        "success": success,
        "answer": merged,
        "sources": merged_sources,
        "images": rag_images or web_images,
        "snippets": list(rag_payload.get("snippets") or [])
        + list(web_payload.get("snippets") or []),
        "latency_ms": float(rag_payload.get("latency_ms") or 0.0)
        + float(web_payload.get("latency_ms") or 0.0),
        "error": "",
        "rag": rag_payload,
        "web": web_payload,
        "retrieval_cache_hit": bool(rag_payload.get("retrieval_cache_hit")),
    }


def _run_single_intent(
    state: AgentRuntimeState, sub: dict[str, Any]
) -> dict[str, Any]:
    q = str(sub.get("query") or "").strip()
    mode = str(sub.get("suggested_tool") or "rag").strip().lower()

    if mode == "rag":
        payload = _safe_execute(
            state,
            "rag",
            lambda st, qq=q: run_rag(st, qq),
        )
        return _intent_bundle_from_rag(sub, payload)

    if mode == "web":
        payload = _safe_execute(
            state,
            "web",
            lambda st, qq=q: run_web(st, qq),
        )
        return _intent_bundle_from_web(sub, payload)

    rag_payload = _safe_execute(
        state,
        "rag",
        lambda st, qq=q: run_rag(st, qq),
    )
    web_payload = _safe_execute(
        state,
        "web",
        lambda st, qq=q: run_web(st, qq),
    )
    return _intent_bundle_from_both(sub, rag_payload, web_payload)


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
        payload.setdefault("retrieval_cache_hit", False)
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
            "retrieval_cache_hit": False,
        }


def _execute_multi_intent(state: AgentRuntimeState) -> dict[str, dict[str, Any]]:
    state.tool_results_by_intent = {}
    subs = list(state.sub_queries or [])
    workers = min(4, max(1, len(subs)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures: dict[str, Any] = {}
        for sub in subs:
            iid = str(sub.get("intent_id") or "").strip()
            if not iid:
                continue
            futures[iid] = pool.submit(_run_single_intent, state, sub)
        for iid, fut in futures.items():
            state.tool_results_by_intent[iid] = fut.result()

    ok_count = sum(
        1 for b in state.tool_results_by_intent.values() if b.get("success")
    )
    state.tool_results = {
        "multi_intent": {
            "tool_name": "multi_intent",
            "success": ok_count == len(state.tool_results_by_intent)
            and len(state.tool_results_by_intent) > 0,
            "answer": "",
            "sources": [],
            "images": [],
            "snippets": [],
            "latency_ms": 0.0,
            "error": "",
        }
    }
    return state.tool_results


def execute_tools(state: AgentRuntimeState) -> dict[str, dict[str, Any]]:
    logger.info(
        "[agent-tools] dispatch started execution_id=%s plan=%s",
        state.execution_id,
        state.plan,
    )
    if state.plan == "direct_answer":
        direct_answer = (
            "Tôi có thể hỗ trợ bạn về định hướng nghề nghiệp, phát triển kỹ năng và thông tin tham khảo từ web khi cần."
            if _looks_vietnamese(state.question)
            else "I can help you with career guidance, skills development, and web-sourced references when needed."
        )
        state.tool_results = {
            "direct": {
                "tool_name": "direct",
                "success": True,
                "answer": direct_answer,
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

    if state.plan == "multi_intent":
        _execute_multi_intent(state)
        logger.info(
            "[agent-tools] multi_intent finished execution_id=%s intents=%d",
            state.execution_id,
            len(state.tool_results_by_intent),
        )
        return state.tool_results

    if state.plan == "rag_only":
        rag_payload = _safe_execute(state, "rag", run_rag)
        state.tool_results = {"rag": rag_payload}
        if _is_insufficient_rag(rag_payload):
            logger.info(
                "[agent-tools] rag_only mode keeps internal retrieval only execution_id=%s",
                state.execution_id,
            )
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
