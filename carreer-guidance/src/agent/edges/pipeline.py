from collections.abc import Callable
import logging
from time import perf_counter
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from src.agent.nodes.cache_node import try_cached_answer
from src.agent.nodes.draft_node import compose_draft_answer
from src.agent.nodes.evaluator_node import evaluate_draft
from src.agent.nodes.finalize_node import save_final_answer
from src.agent.nodes.fixer_node import run_fixer
from src.agent.nodes.guardrails_node import apply_guardrails
from src.agent.nodes.planner_node import choose_plan
from src.agent.nodes.prepare_node import prepare_request
from src.agent.nodes.query_decomposer_node import run_decompose_query
from src.agent.nodes.tool_executor_node import execute_tools
from src.agent.prompts.status_prompts import STATUS_MESSAGES
from src.agent.state.agent_state import AgentRuntimeState
from src.agent.state.user_store import UserStore

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PipelineContext(TypedDict):
    state: AgentRuntimeState
    store: UserStore
    status_callback: Callable[[str], None] | None
    passed: bool | None


def _run_step(
    step_name: str,
    state: AgentRuntimeState,
    operation: Callable[..., Any],
    *args: Any,
) -> Any:
    import asyncio
    if hasattr(state, "is_cancelled") and state.is_cancelled():
        logger.warning("[agent-pipeline] step=%s cancelled execution_id=%s", step_name, state.execution_id)
        raise asyncio.CancelledError("Pipeline execution cancelled by client disconnect")

    started_at = perf_counter()
    logger.info(
        "[agent-pipeline] step=%s started execution_id=%s",
        step_name,
        state.execution_id,
    )
    try:
        result = operation(*args)
    except Exception:
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.exception(
            "[agent-pipeline] step=%s failed execution_id=%s elapsed_ms=%.2f",
            step_name,
            state.execution_id,
            elapsed_ms,
        )
        raise

    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "[agent-pipeline] step=%s finished execution_id=%s elapsed_ms=%.2f",
        step_name,
        state.execution_id,
        elapsed_ms,
    )
    return result


def _push_status(
    state: AgentRuntimeState,
    store: UserStore,
    status_key: str,
    status_callback: Callable[[str], None] | None,
) -> None:
    text = STATUS_MESSAGES[status_key]
    logger.info(
        "[agent-pipeline] status=%s execution_id=%s",
        status_key,
        state.execution_id,
    )
    state.status_history.append(text)
    store.append_status(state.execution_id, text)
    if status_callback is not None:
        status_callback(text)


def _init_status(ctx: PipelineContext) -> dict[str, Any]:
    _push_status(ctx["state"], ctx["store"], "received", ctx.get("status_callback"))
    return {}


def _prepare(ctx: PipelineContext) -> dict[str, Any]:
    _run_step(
        "prepare_request", ctx["state"], prepare_request, ctx["state"], ctx["store"]
    )
    _push_status(
        ctx["state"],
        ctx["store"],
        "question_stored",
        ctx.get("status_callback"),
    )
    return {}


def _cache_check(ctx: PipelineContext) -> dict[str, Any]:
    _push_status(
        ctx["state"],
        ctx["store"],
        "cache_checking",
        ctx.get("status_callback"),
    )
    cached = _run_step(
        "try_cached_answer", ctx["state"], try_cached_answer, ctx["state"], ctx["store"]
    )
    if cached is not None:
        ctx["state"].cache_hit = True
        ctx["state"].answer = str(cached.get("answer") or "")
        ctx["state"].sources = list(cached.get("sources") or [])
        ctx["state"].image_urls = list(cached.get("image_urls") or [])
        logger.info(
            "[agent-pipeline] cache hit execution_id=%s answer_len=%d sources=%d images=%d",
            ctx["state"].execution_id,
            len(ctx["state"].answer),
            len(ctx["state"].sources),
            len(ctx["state"].image_urls),
        )
        _push_status(
            ctx["state"],
            ctx["store"],
            "cache_hit",
            ctx.get("status_callback"),
        )
    return {}


def _decompose(ctx: PipelineContext) -> dict[str, Any]:
    _push_status(
        ctx["state"],
        ctx["store"],
        "decompose_running",
        ctx.get("status_callback"),
    )
    _run_step("decompose_query", ctx["state"], run_decompose_query, ctx["state"])
    return {}


def _guardrails(ctx: PipelineContext) -> dict[str, Any]:
    _push_status(
        ctx["state"],
        ctx["store"],
        "guardrails_running",
        ctx.get("status_callback"),
    )
    _run_step("apply_guardrails", ctx["state"], apply_guardrails, ctx["state"])
    return {}


def _planner(ctx: PipelineContext) -> dict[str, Any]:
    _push_status(
        ctx["state"],
        ctx["store"],
        "planner_running",
        ctx.get("status_callback"),
    )
    _run_step("choose_plan", ctx["state"], choose_plan, ctx["state"])
    logger.info(
        "[agent-pipeline] planner selected execution_id=%s plan=%s",
        ctx["state"].execution_id,
        ctx["state"].plan,
    )
    return {}


def _tools(ctx: PipelineContext) -> dict[str, Any]:
    _push_status(
        ctx["state"],
        ctx["store"],
        "tools_running",
        ctx.get("status_callback"),
    )
    _run_step("execute_tools", ctx["state"], execute_tools, ctx["state"])
    logger.info(
        "[agent-pipeline] tools completed execution_id=%s tool_count=%d",
        ctx["state"].execution_id,
        len(ctx["state"].tool_results),
    )
    return {}


def _draft(ctx: PipelineContext) -> dict[str, Any]:
    _push_status(
        ctx["state"],
        ctx["store"],
        "draft_running",
        ctx.get("status_callback"),
    )
    _run_step("compose_draft_answer", ctx["state"], compose_draft_answer, ctx["state"])
    return {}


def _evaluate(ctx: PipelineContext) -> dict[str, Any]:
    _push_status(
        ctx["state"],
        ctx["store"],
        "evaluator_running",
        ctx.get("status_callback"),
    )
    passed = _run_step("evaluate_draft", ctx["state"], evaluate_draft, ctx["state"])
    logger.info(
        "[agent-pipeline] evaluator result execution_id=%s passed=%s score=%.4f retry_count=%d",
        ctx["state"].execution_id,
        passed,
        ctx["state"].evaluation_score,
        ctx["state"].retry_count,
    )
    return {"passed": bool(passed)}


def _fixer(ctx: PipelineContext) -> dict[str, Any]:
    _push_status(
        ctx["state"],
        ctx["store"],
        "fixer_running",
        ctx.get("status_callback"),
    )
    _run_step("run_fixer", ctx["state"], run_fixer, ctx["state"])
    return {}


def _ensure_answer(ctx: PipelineContext) -> dict[str, Any]:
    if not ctx["state"].answer.strip():
        ctx["state"].answer = ctx["state"].draft_answer.strip()
        logger.info(
            "[agent-pipeline] fallback draft answer execution_id=%s answer_len=%d",
            ctx["state"].execution_id,
            len(ctx["state"].answer),
        )
    return {}


def _finalize(ctx: PipelineContext) -> dict[str, Any]:
    _run_step(
        "save_final_answer", ctx["state"], save_final_answer, ctx["state"], ctx["store"]
    )
    _push_status(
        ctx["state"],
        ctx["store"],
        "answer_stored",
        ctx.get("status_callback"),
    )
    _push_status(
        ctx["state"],
        ctx["store"],
        "done",
        ctx.get("status_callback"),
    )
    return {}


def _route_after_cache(ctx: PipelineContext) -> str:
    return "finalize" if ctx["state"].cache_hit else "guardrails"


def _route_after_guardrails(ctx: PipelineContext) -> str:
    return "tools" if ctx["state"].plan_override else "decompose"


def _route_after_evaluate(ctx: PipelineContext) -> str:
    if ctx.get("passed"):
        return "ensure_answer"
    if ctx["state"].retry_count < ctx["state"].max_retry_count:
        return "fixer"
    return "ensure_answer"


def run_pipeline(
    state: AgentRuntimeState,
    store: UserStore,
    *,
    status_callback: Callable[[str], None] | None = None,
) -> AgentRuntimeState:
    from src.services.cost_tracking.token_usage import (
        TokenUsageAccumulator,
        set_token_usage_accumulator,
    )

    usage_acc = TokenUsageAccumulator()
    set_token_usage_accumulator(usage_acc)
    pipeline_started_at = perf_counter()
    logger.info(
        "[agent-pipeline] run started execution_id=%s user_id=%s",
        state.execution_id,
        state.user_id,
    )

    graph = StateGraph(PipelineContext)
    graph.add_node("init_status", _init_status)
    graph.add_node("prepare", _prepare)
    graph.add_node("cache_check", _cache_check)
    graph.add_node("guardrails", _guardrails)
    graph.add_node("decompose", _decompose)
    graph.add_node("planner", _planner)
    graph.add_node("tools", _tools)
    graph.add_node("draft", _draft)
    graph.add_node("evaluator", _evaluate)
    graph.add_node("fixer", _fixer)
    graph.add_node("ensure_answer", _ensure_answer)
    graph.add_node("finalize", _finalize)

    graph.set_entry_point("init_status")
    graph.add_edge("init_status", "prepare")
    graph.add_edge("prepare", "cache_check")
    graph.add_conditional_edges(
        "cache_check",
        _route_after_cache,
        {
            "guardrails": "guardrails",
            "finalize": "finalize",
        },
    )
    graph.add_conditional_edges(
        "guardrails",
        _route_after_guardrails,
        {
            "decompose": "decompose",
            "tools": "tools",
        },
    )
    graph.add_edge("decompose", "planner")
    graph.add_edge("planner", "tools")
    graph.add_edge("tools", "draft")
    graph.add_edge("draft", "evaluator")
    graph.add_conditional_edges(
        "evaluator",
        _route_after_evaluate,
        {
            "fixer": "fixer",
            "ensure_answer": "ensure_answer",
        },
    )
    graph.add_edge("fixer", "evaluator")
    graph.add_edge("ensure_answer", "finalize")
    graph.add_edge("finalize", END)

    compiled = graph.compile()
    compiled.invoke(
        {
            "state": state,
            "store": store,
            "status_callback": status_callback,
            "passed": None,
        }
    )
    state.token_usage = usage_acc

    total_elapsed_ms = (perf_counter() - pipeline_started_at) * 1000
    logger.info(
        "[agent-pipeline] run finished execution_id=%s cache_hit=%s status_count=%d source_count=%d image_count=%d elapsed_ms=%.2f",
        state.execution_id,
        state.cache_hit,
        len(state.status_history),
        len(state.sources),
        len(state.image_urls),
        total_elapsed_ms,
    )
    return state
