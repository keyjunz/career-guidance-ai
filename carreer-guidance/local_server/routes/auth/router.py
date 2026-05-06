import logging
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, status

from src.config.database import session_scope
from src.database.models import Role, User
from src.repositories.user_repository import UserRepository
from src.request_body.auth_request_body import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from src.services.auth_service.dependencies import get_current_user
from src.services.auth_service.jwt_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from src.services.auth_service.password import hash_password, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

ROLE_CLIENT_ID = UUID("00000000-0000-0000-0000-000000000003")


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        user_name=user.user_name,
        email=user.email,
        phone=user.phone,
        is_active=user.is_active,
        role=user.role.role,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post(
    "/register",
    summary="Register a new user",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_endpoint(payload: RegisterRequest):
    with session_scope() as session:
        repo = UserRepository(session)
        if repo.get_by_email(payload.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        user = repo.create(
            {
                "user_name": payload.user_name,
                "email": payload.email,
                "password": hash_password(payload.password),
                "phone": payload.phone,
                "role_id": ROLE_CLIENT_ID,
            }
        )
        # Load the role relationship before leaving the session
        _ = user.role.role
        session.expunge(user)

    logger.info("User registered: id=%s email=%s", user.id, user.email)
    return _user_to_response(user)


@router.post(
    "/login",
    summary="Login and obtain tokens",
    response_model=TokenResponse,
)
def login_endpoint(payload: LoginRequest):
    with session_scope() as session:
        repo = UserRepository(session)
        user = repo.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )
        role_name = user.role.role
        session.expunge(user)

    access_token = create_access_token(user.id, role_name)
    refresh_token = create_refresh_token(user.id)

    logger.info("User logged in: id=%s email=%s", user.id, user.email)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_user_to_response(user),
    )


@router.post(
    "/refresh",
    summary="Refresh access token",
)
def refresh_endpoint(payload: RefreshRequest):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )
    try:
        token_data = decode_token(payload.refresh_token)
        if token_data.get("type") != "refresh":
            raise credentials_exception
        user_id = UUID(token_data["sub"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError, ValueError):
        raise credentials_exception

    with session_scope() as session:
        repo = UserRepository(session)
        user = repo.get_by_id(user_id)
        if user is None or not user.is_active:
            raise credentials_exception
        role_name = user.role.role

    access_token = create_access_token(user_id, role_name)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get(
    "/me",
    summary="Get current user info",
    response_model=UserResponse,
)
def me_endpoint(current_user: User = Depends(get_current_user)):
    return _user_to_response(current_user)
