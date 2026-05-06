from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from src.config.settings_models import get_settings


def _get_auth_config():
    return get_settings().auth


def create_access_token(user_id: UUID, role: str) -> str:
    cfg = _get_auth_config()
    expire = datetime.now(timezone.utc) + timedelta(minutes=cfg.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, cfg.jwt_secret_key, algorithm=cfg.jwt_algorithm)


def create_refresh_token(user_id: UUID) -> str:
    cfg = _get_auth_config()
    expire = datetime.now(timezone.utc) + timedelta(days=cfg.refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, cfg.jwt_secret_key, algorithm=cfg.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token. Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError."""
    cfg = _get_auth_config()
    return jwt.decode(token, cfg.jwt_secret_key, algorithms=[cfg.jwt_algorithm])
