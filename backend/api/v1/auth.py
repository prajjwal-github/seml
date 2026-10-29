"""Authentication API endpoints (login, refresh, logout, me)."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user, get_db
from backend.core.audit import log_audit_event
from backend.core.config import settings
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from backend.models import User
from backend.schemas.user import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, session: AsyncSession = Depends(get_db)):
    """Authenticates credentials using Argon2id and returns access & rotating refresh tokens."""
    stmt = select(User).where(User.email == req.email.lower().strip())
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    user.last_login = datetime.now(timezone.utc)
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    access_token = create_access_token(user.id, role_str, user.org_id)
    refresh_token, _ = create_refresh_token(user.id)

    await log_audit_event(
        session=session,
        action="USER_LOGIN",
        entity_type="USER",
        entity_id=str(user.id),
        actor_id=user.id,
        details={"email": user.email, "role": role_str},
    )
    await session.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(req: RefreshRequest, session: AsyncSession = Depends(get_db)):
    """Validates refresh token and issues a new access token and rotated refresh token."""
    try:
        payload = decode_token(req.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        import uuid
        user_id = uuid.UUID(payload.get("sub"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = await session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    access_token = create_access_token(user.id, role_str, user.org_id)
    new_refresh_token, _ = create_refresh_token(user.id)
    await session.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Logs out the current session and records audit event."""
    await log_audit_event(
        session=session,
        action="USER_LOGOUT",
        entity_type="USER",
        entity_id=str(current_user.id),
        actor_id=current_user.id,
    )
    await session.commit()
    return {"status": "success", "message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns profile for currently authenticated user."""
    return UserResponse.model_validate(current_user)
