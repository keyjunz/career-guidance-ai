"""Decompose multi-intent questions into sub-queries with per-intent tool hints."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from src.agent.nodes.planner_node import is_direct_answer_question
from src.agent.state.agent_state import AgentRuntimeState
from src.prompts.query_prompts import MAX_SUB_QUERIES, build_query_decomposition_prompt
from src.services.llm_service.main import LLMService

logger = logging.getLogger(__name__)

_VALID_TOOLS = frozenset({"rag", "web", "both"})


def _heuristic_multi_clause(question: str) -> bool:
    q = str(question or "").strip()
    if len(q) < 24:
        return False
    if q.count("?") >= 2:
        return True
    if re.search(r"\?\s+.+\?", q):
        return True
    for sep in (";", "；", "\n"):
        if sep in q and len(q.split(sep)) >= 2:
            return True
    for conj in (" và ", " với ", " đồng thời ", " còn ", " plus ", " and also "):
        if conj in q.lower():
            return True
    return False


def _normalize_sub_queries(raw: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw or []):
        if not isinstance(item, dict):
            continue
        q = str(item.get("query") or "").strip()
        if not q:
            continue
        tool = str(item.get("suggested_tool") or "rag").strip().lower()
        if tool not in _VALID_TOOLS:
            tool = "rag"
        intent_id = str(item.get("intent_id") or f"intent_{i + 1}").strip()
        section_title = str(item.get("section_title") or "").strip() or f"Ý {len(out) + 1}"
        try:
            conf = float(item.get("confidence") or 0.5)
        except (TypeError, ValueError):
            conf = 0.5
        out.append(
            {
                "intent_id": intent_id,
                "query": q,
                "intent_type": str(item.get("intent_type") or "general").strip(),
                "confidence": max(0.0, min(1.0, conf)),
                "suggested_tool": tool,
                "section_title": section_title,
            }
        )
        if len(out) >= MAX_SUB_QUERIES:
            break
    return out


def run_decompose_query(state: AgentRuntimeState) -> None:
    """Populate state.multi_intent + state.sub_queries when decomposition applies."""
    state.multi_intent = False
    state.sub_queries = []

    if state.plan_override:
        return

    if is_direct_answer_question(state.question):
        return

    enabled = os.getenv("AGENT_MULTI_INTENT", "true").strip().lower() == "true"
    if not enabled:
        return

    if not _heuristic_multi_clause(state.question):
        return

    prompt = build_query_decomposition_prompt(state.question)
    try:
        llm = LLMService(
            execution_id=state.execution_id,
            api_key_env_override="GEMINI_AGENT_API_KEY",
        )
        result = llm.generate_raw(prompt=prompt, max_tokens=700, temperature=0.0)
        llm.unload()
        raw = str(result.get("answer") or "").strip()
    except Exception:
        logger.exception(
            "[agent-decompose] llm failed execution_id=%s", state.execution_id
        )
        return

    if not raw:
        return

    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw).strip()
        raw = re.sub(r"\s*```$", "", raw).strip()

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(
            "[agent-decompose] invalid json execution_id=%s preview=%s",
            state.execution_id,
            raw[:200],
        )
        return

    needs = bool(payload.get("needs_decomposition"))
    subs = _normalize_sub_queries(list(payload.get("sub_queries") or []))
    if not subs:
        return

    if needs and len(subs) >= 2:
        state.multi_intent = True
        state.sub_queries = subs
        logger.info(
            "[agent-decompose] multi_intent execution_id=%s intents=%d",
            state.execution_id,
            len(subs),
        )
        return

    if not needs and len(subs) == 1:
        return

    if len(subs) >= 2:
        state.multi_intent = True
        state.sub_queries = subs
        logger.info(
            "[agent-decompose] forced multi from subs execution_id=%s intents=%d",
            state.execution_id,
            len(subs),
        )
