"""Per-execution LLM token usage aggregation for request_cost_log."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class TokenUsageAccumulator:
    input_tokens: int = 0
    output_tokens: int = 0
    model_names: set[str] = field(default_factory=set)
    request_types: set[str] = field(default_factory=set)

    def add(
        self,
        *,
        request_type: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        self.input_tokens += max(0, int(input_tokens))
        self.output_tokens += max(0, int(output_tokens))
        if model_name.strip():
            self.model_names.add(model_name.strip())
        if request_type.strip():
            self.request_types.add(request_type.strip())

    def primary_model_name(self) -> str:
        if not self.model_names:
            return "unknown"
        if len(self.model_names) == 1:
            return next(iter(self.model_names))
        return "mixed"

    def primary_request_type(self) -> str:
        if not self.request_types:
            return "chat"
        if len(self.request_types) == 1:
            return next(iter(self.request_types))
        return "chat"


_token_usage_ctx: ContextVar[TokenUsageAccumulator | None] = ContextVar(
    "token_usage_accumulator",
    default=None,
)


def set_token_usage_accumulator(accumulator: TokenUsageAccumulator | None) -> None:
    _token_usage_ctx.set(accumulator)


def get_token_usage_snapshot() -> TokenUsageAccumulator | None:
    return _token_usage_ctx.get()


def clear_token_usage() -> None:
    _token_usage_ctx.set(None)


def record_token_usage(
    *,
    request_type: str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    acc = _token_usage_ctx.get()
    if acc is None:
        return
    acc.add(
        request_type=request_type,
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
