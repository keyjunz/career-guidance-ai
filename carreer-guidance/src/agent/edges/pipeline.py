from collections.abc import Callable
import logging
from time import perf_counter
from typing import Any

from src.agent.nodes.cache_node import try_cached_answer
from src.agent.nodes.draft_node import compose_draft_answer
from src.agent.nodes.evaluator_node import evaluate_draft
from src.agent.nodes.finalize_node import save_final_answer
from src.agent.nodes.fixer_node import run_fixer
from src.agent.nodes.guardrails_node import apply_guardrails
from src.agent.nodes.planner_node import choose_plan
from src.agent.nodes.prepare_node import prepare_request
from src.agent.nodes.tool_executor_node import execute_tools
from src.agent.prompts.status_prompts import STATUS_MESSAGES
from src.agent.state.agent_state import AgentRuntimeState
from src.agent.state.user_store import UserStore

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _run_step(
    step_name: str,
    state: AgentRuntimeState,
    operation: Callable[..., Any],
    *args: Any,
) -> Any:
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


def run_pipeline(
    state: AgentRuntimeState,
    store: UserStore,
    *,
    status_callback: Callable[[str], None] | None = None,
) -> AgentRuntimeState:
    pipeline_started_at = perf_counter()
    logger.info(
        "[agent-pipeline] run started execution_id=%s user_id=%s",
        state.execution_id,
        state.user_id,
    )
    _push_status(state, store, "received", status_callback)

    _run_step("prepare_request", state, prepare_request, state, store)
    _push_status(state, store, "question_stored", status_callback)

    _push_status(state, store, "cache_checking", status_callback)
    cached = _run_step("try_cached_answer", state, try_cached_answer, state, store)
    if cached is not None:
        state.cache_hit = True
        state.answer = str(cached.get("answer") or "")
        state.sources = list(cached.get("sources") or [])
        state.image_urls = list(cached.get("image_urls") or [])
        logger.info(
            "[agent-pipeline] cache hit execution_id=%s answer_len=%d sources=%d images=%d",
            state.execution_id,
            len(state.answer),
            len(state.sources),
            len(state.image_urls),
        )
        _push_status(state, store, "cache_hit", status_callback)
    else:
        _push_status(state, store, "guardrails_running", status_callback)
        _run_step("apply_guardrails", state, apply_guardrails, state)

        _push_status(state, store, "planner_running", status_callback)
        _run_step("choose_plan", state, choose_plan, state)
        logger.info(
            "[agent-pipeline] planner selected execution_id=%s plan=%s",
            state.execution_id,
            state.plan,
        )

        _push_status(state, store, "tools_running", status_callback)
        _run_step("execute_tools", state, execute_tools, state)
        logger.info(
            "[agent-pipeline] tools completed execution_id=%s tool_count=%d",
            state.execution_id,
            len(state.tool_results),
        )

        _push_status(state, store, "draft_running", status_callback)
        _run_step("compose_draft_answer", state, compose_draft_answer, state)

        _push_status(state, store, "evaluator_running", status_callback)
        passed = _run_step("evaluate_draft", state, evaluate_draft, state)
        logger.info(
            "[agent-pipeline] evaluator result execution_id=%s passed=%s score=%.4f retry_count=%d",
            state.execution_id,
            passed,
            state.evaluation_score,
            state.retry_count,
        )

        while not passed and state.retry_count < state.max_retry_count:
            logger.info(
                "[agent-pipeline] retry round execution_id=%s retry_count=%d max_retry=%d",
                state.execution_id,
                state.retry_count,
                state.max_retry_count,
            )
            _push_status(state, store, "fixer_running", status_callback)
            _run_step("run_fixer", state, run_fixer, state)

            _push_status(state, store, "evaluator_running", status_callback)
            passed = _run_step("evaluate_draft", state, evaluate_draft, state)
            logger.info(
                "[agent-pipeline] evaluator retry result execution_id=%s passed=%s score=%.4f retry_count=%d",
                state.execution_id,
                passed,
                state.evaluation_score,
                state.retry_count,
            )

        if not state.answer.strip():
            state.answer = state.draft_answer.strip()
            logger.info(
                "[agent-pipeline] fallback draft answer execution_id=%s answer_len=%d",
                state.execution_id,
                len(state.answer),
            )

    _run_step("save_final_answer", state, save_final_answer, state, store)
    _push_status(state, store, "answer_stored", status_callback)
    _push_status(state, store, "done", status_callback)
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
