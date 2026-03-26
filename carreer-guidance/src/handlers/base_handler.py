"""Common handler primitives for context and error mapping."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class RequestContext:
    """Request-scoped context shared across handler/module/service layers."""

    trace_id: str
    user_id: str | None = None


class DomainError(Exception):
    """Typed domain error used by handlers for response mapping."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def map_exception_to_domain_error(exc: Exception) -> DomainError:
    """Map unknown exceptions to a stable domain error contract."""

    if isinstance(exc, DomainError):
        return exc

    if isinstance(exc, ValueError):
        return DomainError(code="BAD_REQUEST", message=str(exc))

    return DomainError(code="INTERNAL_ERROR", message="Internal server error")
