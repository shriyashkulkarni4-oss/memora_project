"""Registration and revocable token-session endpoints."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models import RefreshToken, User, UserRole
from app.schemas.auth import (
    ChangePasswordRequest,
    LogoutRequest,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.schemas.common import ErrorResponse

router = APIRouter()
settings = get_settings()

AUTH_ERRORS = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


async def _issue_token_pair(db: DbSession, user: User) -> TokenPair:
    raw_refresh_token = create_refresh_token()
    now = datetime.now(timezone.utc)
    db.add(
        RefreshToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token_hash=hash_token(raw_refresh_token),
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    return TokenPair(
        access_token=create_access_token(
            {"sub": user.id, "session_version": user.session_version}
        ),
        refresh_token=raw_refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses=AUTH_ERRORS,
)
async def register(user_data: UserCreate, db: DbSession) -> User:
    email = user_data.email.lower()
    if await db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email already registered")

    existing_users = await db.scalar(select(func.count()).select_from(User))
    bootstrap_emails = {value.lower() for value in settings.admin_bootstrap_emails}
    role = (
        UserRole.ADMIN.value
        if email in bootstrap_emails or (settings.is_development and not existing_users)
        else UserRole.USER.value
    )
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password=hash_password(user_data.password),
        name=user_data.name,
        role=role,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered") from exc
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair, responses=AUTH_ERRORS)
async def login(user_data: UserLogin, db: DbSession) -> TokenPair:
    user = await db.scalar(select(User).where(User.email == user_data.email.lower()))
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is disabled")

    tokens = await _issue_token_pair(db, user)
    await db.commit()
    return tokens


@router.post("/refresh", response_model=TokenPair, responses=AUTH_ERRORS)
async def refresh_session(data: RefreshRequest, db: DbSession) -> TokenPair:
    token = await db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(data.refresh_token)
        )
    )
    now = datetime.now(timezone.utc)
    if (
        token is None
        or token.revoked_at is not None
        or _as_utc(token.expires_at) <= now
    ):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    user = await db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is disabled")

    token.revoked_at = now
    tokens = await _issue_token_pair(db, user)
    await db.commit()
    return tokens


@router.post("/logout", status_code=204, responses=AUTH_ERRORS)
async def logout(data: LogoutRequest, db: DbSession) -> None:
    token = await db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(data.refresh_token)
        )
    )
    if token and token.revoked_at is None:
        token.revoked_at = datetime.now(timezone.utc)
        await db.commit()


@router.post("/logout-all", status_code=204, responses=AUTH_ERRORS)
async def logout_all(current_user: CurrentUser, db: DbSession) -> None:
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()


@router.post("/change-password", status_code=204, responses=AUTH_ERRORS)
async def change_password(
    data: ChangePasswordRequest, current_user: CurrentUser, db: DbSession
) -> None:
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if verify_password(data.new_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="New password must be different")

    now = datetime.now(timezone.utc)
    current_user.hashed_password = hash_password(data.new_password)
    current_user.session_version += 1
    current_user.password_changed_at = now
    current_user.updated_at = now
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    await db.commit()


@router.get("/me", response_model=UserResponse, responses=AUTH_ERRORS)
async def get_me(current_user: CurrentUser) -> User:
    return current_user
