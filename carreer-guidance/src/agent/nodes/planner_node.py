import json
import logging

from src.agent.state.agent_state import AgentRuntimeState
from src.services.llm_service.main import LLMService

VALID_PLANS = {
    "direct_answer",
    "rag_only",
    "web_only",
    "rag_web_parallel",
    "multi_intent",
}
DEFAULT_PLAN = "rag_web_parallel"

logger = logging.getLogger(__name__)


def is_direct_answer_question(question: str) -> bool:
    normalized = " ".join(str(question or "").strip().lower().split())
    if not normalized:
        return False

    direct_phrases = {
        "hi",
        "hi",
        "hello",
        "hey",
        "thanks",
        "thank you",
        "chào",
        "xin chào",
        "chao",
        "xin chao",
        "cảm ơn",
        "cam on",
        "cám ơn",
    }
    if normalized in direct_phrases:
        return True

    if len(normalized) <= 20 and any(
        phrase in normalized
        for phrase in ("chào", "xin chao", "xin chào", "hello", "hi")
    ):
        return True

    return False


def _build_router_prompt(question: str) -> str:
    return f"""You are a tool router in a LangGraph-based career-guidance chatbot pipeline.
Your job is to choose exactly ONE plan for the user question.

DOMAIN CONTEXT:
This chatbot assists students and professionals with AI/Computer Science career guidance,
university programs, course recommendations, and technical skill development.
The internal knowledge base contains academic documents, curricula, research papers, and career resources.

AVAILABLE PLANS:
- direct_answer : greeting, thanks, small-talk, or meta-questions about the bot itself — NO retrieval needed.
- rag_only      : question is about internal knowledge (courses, curricula, university info, academic content, career paths already covered by documents).
- web_only      : question needs fresh, public, or real-time web information (job market trends, latest tools, external company info).
- rag_web_parallel : question likely needs both internal docs AND web info, or you are uncertain which single source is sufficient.

ROUTING RULES:
1. Questions about university-specific programs, internal documents, or academic curricula → rag_only.
2. Questions about current industry trends, salary data, external companies, or breaking news → web_only.
3. Questions mixing internal academic content with external context → rag_web_parallel.
4. If the question is in Vietnamese, still route correctly — language does not affect plan choice.
5. If internal coverage is uncertain or likely incomplete, prefer rag_web_parallel to allow a web fallback.
6. When uncertain, default to rag_web_parallel.

OUTPUT FORMAT — Return STRICT JSON only, no extra text:
{{"plan":"<one_of_valid_plans>","confidence":0.0-1.0,"reason":"short explanation"}}

EXAMPLES:
- "Chương trình học AI của trường gồm những môn gì?" → rag_only (university curriculum)
- "Mức lương trung bình của AI engineer năm 2025?" → web_only (real-time salary data)
- "So sánh chương trình CMU với xu hướng ngành hiện tại" → rag_web_parallel (internal + external)
- "Xin chào" → direct_answer (greeting)

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
    question = state.question.strip()
    if is_direct_answer_question(question):
        state.plan = "direct_answer"
        logger.info(
            "[agent-planner] heuristic direct answer execution_id=%s",
            state.execution_id,
        )
        return state.plan

    if getattr(state, "multi_intent", False) and state.sub_queries:
        state.plan = "multi_intent"
        logger.info(
            "[agent-planner] multi_intent plan execution_id=%s intents=%d",
            state.execution_id,
            len(state.sub_queries),
        )
        return state.plan

    prompt = _build_router_prompt(question)

    try:
        llm = LLMService(
            execution_id=state.execution_id,
        )
        state._active_llm = llm
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
