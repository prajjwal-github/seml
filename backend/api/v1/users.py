"""User management API endpoints (Admin only)."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, require_roles
from backend.core.audit import log_audit_event
from backend.core.security import hash_password
from backend.models import User, UserRole
from backend.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(require_roles([UserRole.ADMIN]))],
)


@router.get("", response_model=List[UserResponse])
async def list_users(session: AsyncSession = Depends(get_db)):
    """Lists all users across the system."""
    stmt = select(User).order_by(User.created_at.desc())
    res = await session.execute(stmt)
    return [UserResponse.model_validate(u) for u in res.scalars().all()]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    req: UserCreate,
    current_admin: User = Depends(require_roles([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Creates a new user account with specified role."""
    stmt = select(User).where(User.email == req.email.lower().strip())
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=req.email.lower().strip(),
        name=req.name,
        password_hash=hash_password(req.password),
        role=req.role,
        is_active=req.is_active,
        org_id=req.org_id,
    )
    session.add(user)
    await session.flush()

    await log_audit_event(
        session=session,
        action="USER_CREATED",
        entity_type="USER",
        entity_id=str(user.id),
        actor_id=current_admin.id,
        details={"email": user.email, "role": user.role.value},
    )
    await session.commit()
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    """Fetches details for a specific user."""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    req: UserUpdate,
    current_admin: User = Depends(require_roles([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Updates user information, role, or active status."""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if req.name is not None:
        user.name = req.name
    if req.role is not None:
        user.role = req.role
    if req.is_active is not None:
        user.is_active = req.is_active
    if req.password:
        user.password_hash = hash_password(req.password)

    await log_audit_event(
        session=session,
        action="USER_UPDATED",
        entity_type="USER",
        entity_id=str(user.id),
        actor_id=current_admin.id,
        details={"updated_fields": [k for k, v in req.model_dump().items() if v is not None]},
    )
    await session.commit()
    return UserResponse.model_validate(user)
