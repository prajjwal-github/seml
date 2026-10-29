"""FastAPI dependency injection utilities for authentication, RBAC, and agent authorization."""

import uuid
from typing import Callable, List, Optional
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import decode_token, sha256_hex
from backend.models import Agent, User, UserRole

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Validates JWT access token and returns the authenticated User."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed authorization credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        user_id = uuid.UUID(payload.get("sub"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account")

    return user


def require_roles(allowed_roles: List[UserRole]) -> Callable:
    """Dependency factory checking that current user has one of the required roles."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role_str = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        allowed_values = [r.value if hasattr(r, "value") else str(r) for r in allowed_roles]
        if user_role_str not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of roles: {allowed_values}. Current role: '{user_role_str}'",
            )
        return current_user

    return role_checker


async def get_agent_from_key(
    x_agent_key: Optional[str] = Header(None, alias="X-Agent-Key"),
    session: AsyncSession = Depends(get_db),
) -> Agent:
    """Validates X-Agent-Key header against registered agent API key hashes."""
    if not x_agent_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Agent-Key header",
        )

    key_hash = sha256_hex(x_agent_key)
    stmt = select(Agent).where(Agent.api_key_hash == key_hash, Agent.is_active == True)
    res = await session.execute(stmt)
    agent = res.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or deactivated agent key",
        )

    return agent
