import json
import logging
import os

from src.agent.state.agent_state import AgentRuntimeState
from src.services.llm_service.main import LLMService

PASS_THRESHOLD = 0.65
LLM_EVAL_DEFAULT = "true"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _build_eval_prompt(state: AgentRuntimeState) -> str:
    sources = list(state.sources or [])
    source_count = len(sources)

    source_excerpts = ""
    if sources:
        excerpts = []
        for i, src in enumerate(sources[:5], 1):
            title = str(src.get("title") or src.get("source") or "").strip()
            url = str(src.get("url") or "").strip()
            label = title or url or f"Source {i}"
            excerpts.append(f"  {i}. {label}")
        source_excerpts = "\n".join(excerpts)

    return (
        "You are a strict answer-quality evaluator for a career-guidance chatbot.\n\n"
        "SCORING RUBRIC (0.0 to 1.0):\n"
        "- 0.9-1.0: Accurate, complete, well-structured, grounded in sources, directly answers the question.\n"
        "- 0.7-0.89: Mostly correct with minor gaps or slight vagueness.\n"
        "- 0.5-0.69: Partially correct but missing key information or poorly structured.\n"
        "- 0.0-0.49: Incorrect, fabricated, off-topic, or empty.\n\n"
        "CRITERIA:\n"
        "1. Correctness — Are claims accurate and not fabricated?\n"
        "2. Completeness — Does the answer address all parts of the question?\n"
        "3. Groundedness — Is the answer supported by the provided sources?\n"
        "4. Clarity — Is the answer well-organized and easy to understand?\n"
        "5. Relevance — Does the answer stay on topic?\n\n"
        "RULES:\n"
        "- If the plan requires sources (rag_only, web_only, rag_web_parallel) but none are provided, cap score at 0.5.\n"
        "- If the answer is empty or under 20 characters, score 0.0.\n\n"
        'OUTPUT FORMAT — Return STRICT JSON only: {"score":0.0-1.0,"notes":["..."]}\n\n'
        f"Question:\n{state.question.strip()}\n\n"
        f"Plan: {state.plan}\n"
        f"Source count: {source_count}\n"
        + (f"Sources:\n{source_excerpts}\n\n" if source_excerpts else "\n")
        + f"Answer:\n{state.draft_answer.strip()}\n"
    )


def _try_llm_eval(state: AgentRuntimeState) -> tuple[float | None, list[str]]:
    enabled = (
        str(os.getenv("AGENT_LLM_EVAL", LLM_EVAL_DEFAULT)).strip().lower() == "true"
    )
    if not enabled:
        return None, []

    try:
        llm = LLMService(
            execution_id=state.execution_id,
            api_key_env_override="GEMINI_AGENT_API_KEY",
        )
        result = llm.generate_raw(
            prompt=_build_eval_prompt(state),
            max_tokens=180,
            temperature=0.0,
        )
        llm.unload()
    except Exception as exc:
        logger.warning(
            "LLM eval failed: execution_id=%s error=%s", state.execution_id, exc
        )
        return None, []

    raw = str(result.get("answer") or "").strip()
    if not raw:
        return None, []

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None, []

    score = payload.get("score")
    notes = payload.get("notes")
    if not isinstance(score, (int, float)):
        return None, []
    if score < 0:
        score = 0.0
    if score > 1:
        score = 1.0

    if not isinstance(notes, list):
        notes = []
    notes = [str(item) for item in notes if str(item).strip()]
    return float(score), notes


def evaluate_draft(state: AgentRuntimeState) -> bool:
    notes: list[str] = []
    score = 1.0

    draft = state.draft_answer.strip()
    if len(draft) < 30:
        score -= 0.30
        notes.append("draft answer is too short")

    if state.plan in {"rag_only", "rag_web_parallel"}:
        rag_ok = bool(state.tool_results.get("rag", {}).get("success"))
        if not rag_ok:
            score -= 0.35
            notes.append("rag tool failed")

    if state.plan in {"web_only", "rag_web_parallel"}:
        web_payload = state.tool_results.get("web", {})
        web_ok = bool(web_payload.get("success"))
        if not web_ok:
            score -= 0.35
            notes.append("web tool failed")
        elif not list(web_payload.get("sources") or []):
            score -= 0.15
            notes.append("web tool returned no sources")

    if not state.sources and state.plan != "direct_answer":
        score -= 0.10
        notes.append("no sources attached")

    if state.plan == "rag_web_parallel":
        rag_ok = bool(state.tool_results.get("rag", {}).get("success"))
        web_ok = bool(state.tool_results.get("web", {}).get("success"))
        if not rag_ok and not web_ok:
            score = 0.0
            notes.append("both rag and web failed")

    llm_score, llm_notes = _try_llm_eval(state)
    if llm_score is not None:
        score = min(score, llm_score)
        notes.extend(llm_notes)

    state.evaluation_score = max(0.0, score)
    state.evaluation_notes = notes

    passed = state.evaluation_score >= PASS_THRESHOLD
    if passed and draft:
        state.answer = draft
    return passed
