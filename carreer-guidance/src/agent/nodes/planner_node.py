import json
import logging

from src.agent.state.agent_state import AgentRuntimeState
from src.services.llm_service.main import LLMService

VALID_PLANS = {"direct_answer", "rag_only", "web_only", "rag_web_parallel"}
DEFAULT_PLAN = "rag_web_parallel"

logger = logging.getLogger(__name__)


def _build_router_prompt(question: str) -> str:
    return f"""You are a tool router in a LangGraph pipeline.
Choose exactly one plan for the user question.

Available plans:
- direct_answer: greeting, thanks, or small-talk that needs no retrieval
- rag_only: answer should come from internal knowledge base/documents
- web_only: answer needs fresh/public web information
- rag_web_parallel: needs both internal docs and web, or uncertainty exists

Routing rules:
1) Prefer precision over speed.
2) If uncertain between choices, return rag_web_parallel.
3) Return STRICT JSON only: {{"plan":"<one_of_valid_plans>","confidence":0.0-1.0,"reason":"short"}}

User question:
{question}
"""


def _parse_plan(raw_answer: str) -> str | None:
    payload = str(raw_answer or "").strip()
    if not payload:
        return None

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None

    plan = str(parsed.get("plan") or "").strip()
    if plan in VALID_PLANS:
        return plan
    return None


def choose_plan(state: AgentRuntimeState) -> str:
    prompt = _build_router_prompt(state.question.strip())

    try:
        llm = LLMService(execution_id=state.execution_id)
        result = llm.generate_raw(prompt=prompt, max_tokens=120, temperature=0.0)
        routed_plan = _parse_plan(result.get("answer", ""))
        llm.unload()
    except Exception:
        logger.exception(
            "[agent-planner] llm routing failed execution_id=%s", state.execution_id
        )
        routed_plan = None

    if routed_plan is None:
        state.plan = DEFAULT_PLAN
        logger.warning(
            "[agent-planner] fallback plan execution_id=%s plan=%s",
            state.execution_id,
            state.plan,
        )
        return state.plan

    state.plan = routed_plan
    logger.info(
        "[agent-planner] routed execution_id=%s plan=%s", state.execution_id, state.plan
    )
    return state.plan
