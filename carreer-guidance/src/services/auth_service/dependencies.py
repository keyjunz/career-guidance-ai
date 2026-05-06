from collections.abc import Callable
import json
import time
from pathlib import Path
from typing import Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config.database import session_scope
from src.database.models import User
from src.repositories.user_repository import UserRepository
from src.services.auth_service.jwt_service import decode_token

bearer_scheme = HTTPBearer(auto_error=True)

# #region agent log
DEBUG_LOG_PATH = Path("debug-8bc2e9.log")


def _agent_append(payload: dict[str, Any]) -> None:
    payload.setdefault("sessionId", "8bc2e9")
    payload.setdefault("runId", "pre-fix")
    payload.setdefault("timestamp", int(time.time() * 1000))
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


# #endregion

def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    """Extract JWT, validate, and return the User ORM object."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = decode_token(token)
        _agent_append(
            {
                "hypothesisId": "H1,H2",
                "location": "auth/dependencies.py:get_current_user:decoded",
                "message": "token decoded",
                "data": {
                    "path": request.url.path,
                    "token_type": payload.get("type"),
                    "sub": payload.get("sub"),
                },
            }
        )
        if payload.get("type") != "access":
            raise credentials_exception
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = UUID(user_id_str)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValueError) as exc:
        _agent_append(
            {
                "hypothesisId": "H1,H2",
                "location": "auth/dependencies.py:get_current_user:decode_failed",
                "message": "token decode/parse failed",
                "data": {
                    "path": request.url.path,
                    "exc_type": type(exc).__name__,
                    "exc": str(exc),
                },
            }
        )
        raise credentials_exception

    with session_scope() as session:
        repo = UserRepository(session)
        user = repo.get_by_id(user_id)
        _agent_append(
            {
                "hypothesisId": "H3,H4",
                "location": "auth/dependencies.py:get_current_user:db_lookup",
                "message": "user lookup completed",
                "data": {
                    "path": request.url.path,
                    "user_found": user is not None,
                    "is_active": (bool(user.is_active) if user is not None else None),
                    "role": (user.role.role if user is not None and user.role else None),
                },
            }
        )
        if user is None or not user.is_active:
            raise credentials_exception
        # Eagerly load role name so it's accessible outside the session
        _ = user.role.role
        # Expunge to detach from session while keeping loaded attributes
        session.expunge(user)
    return user


def require_roles(*allowed_roles: str) -> Callable[..., User]:
    """Factory that returns a dependency verifying the user has one of the allowed roles."""

    def _check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _check_role
