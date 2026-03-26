"""Base primitives and shared error mapping for handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class DomainError(Exception):
    """Domain-level error that can be converted to API error payloads."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


@dataclass(slots=True)
class RequestContext:
    """Per-request metadata propagated through handlers."""

    trace_id: str
    user_id: str | None = None


def map_exception_to_domain_error(exc: Exception) -> DomainError:
    """Normalize unknown exceptions into DomainError for API layer."""

    if isinstance(exc, DomainError):
        return exc
    return DomainError(
        code="INTERNAL_ERROR",
        message="Unexpected error during request processing",
        details={"exception_type": exc.__class__.__name__},
    )
