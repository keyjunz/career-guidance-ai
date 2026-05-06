import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.config.database import session_scope
from src.database.models import Role, User
from src.repositories.user_repository import UserRepository
from src.request_body.auth_request_body import UserResponse
from src.services.auth_service.dependencies import require_roles
from src.services.auth_service.password import hash_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

_admin_guard = require_roles("admin")


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


@router.get(
    "/users",
    summary="List all users",
    response_model=list[UserResponse],
)
def list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(_admin_guard),
):
    with session_scope() as session:
        repo = UserRepository(session)
        users = repo.get_many(limit=limit, offset=offset)
        for u in users:
            _ = u.role.role
        session.expunge_all()
    return [_user_to_response(u) for u in users]


@router.get(
    "/users/{user_id}",
    summary="Get user detail",
    response_model=UserResponse,
)
def get_user(
    user_id: UUID,
    _admin: User = Depends(_admin_guard),
):
    with session_scope() as session:
        repo = UserRepository(session)
        user = repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        _ = user.role.role
        session.expunge(user)
    return _user_to_response(user)


@router.put(
    "/users/{user_id}",
    summary="Update user (role, is_active, etc.)",
    response_model=UserResponse,
)
def update_user(
    user_id: UUID,
    payload: dict,
    _admin: User = Depends(_admin_guard),
):
    allowed_fields = {"user_name", "email", "phone", "is_active", "role_id", "password"}
    update_data = {k: v for k, v in payload.items() if k in allowed_fields}

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No valid fields to update. Allowed: {', '.join(sorted(allowed_fields))}",
        )

    if "password" in update_data:
        update_data["password"] = hash_password(str(update_data["password"]))

    if "role_id" in update_data:
        try:
            update_data["role_id"] = UUID(str(update_data["role_id"]))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role_id format",
            )

    with session_scope() as session:
        repo = UserRepository(session)
        user = repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        user = repo.update(user, update_data)
        _ = user.role.role
        session.expunge(user)

    logger.info("Admin updated user: id=%s fields=%s", user_id, list(update_data.keys()))
    return _user_to_response(user)


@router.delete(
    "/users/{user_id}",
    summary="Delete user",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user(
    user_id: UUID,
    _admin: User = Depends(_admin_guard),
):
    with session_scope() as session:
        repo = UserRepository(session)
        deleted = repo.delete_by_id(user_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

    logger.info("Admin deleted user: id=%s", user_id)
    return None
