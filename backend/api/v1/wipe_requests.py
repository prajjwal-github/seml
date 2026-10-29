"""Wipe requests creation, listing, details, and cancellation endpoints."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user, get_db, require_roles
from backend.core.audit import log_audit_event
from backend.core.config import settings
from backend.models import (
    Device,
    NISTCategory,
    Notification,
    RequestStatus,
    StorageVolume,
    User,
    UserRole,
    WipeMethod,
    WipeRequest,
)
from backend.schemas.wipe import WipeRequestCreate, WipeRequestResponse
from backend.services.approval_service import ApprovalService
from backend.ws.manager import ws_manager

router = APIRouter(prefix="/wipe-requests", tags=["Wipe Requests"])


@router.post("", response_model=WipeRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_wipe_request(
    req: WipeRequestCreate,
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Submits a new wipe request requiring dual-custody approval.

    NO job is created and nothing runs at this stage. UI shows 'Waiting for approval'.
    """
    device = await session.get(Device, req.device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target device not found")

    # Critical confirmation: verify typed device serial number
    if req.confirm_serial.strip().lower() != device.serial_number.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Typed serial number '{req.confirm_serial}' does not match device serial number '{device.serial_number}'",
        )

    # Fetch volumes
    v_stmt = select(StorageVolume).where(StorageVolume.id.in_(req.volume_ids))
    vols = (await session.execute(v_stmt)).scalars().all()
    if not vols:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one valid volume must be selected")

    # Evaluate risk & approver count
    dev_status = device.status.value if hasattr(device.status, "value") else str(device.status)
    risk_level, required_approvers = ApprovalService.evaluate_risk(
        volumes=vols,
        method=req.method,
        is_production=(dev_status == "ONLINE"),
    )

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=settings.APPROVAL_EXPIRY_HOURS)
    nist_cat = NISTCategory.PURGE if req.method == WipeMethod.NIST_800_88_PURGE else NISTCategory.CLEAR

    wipe_req = WipeRequest(
        device_id=device.id,
        requested_by=current_user.id,
        reason=req.reason.strip(),
        method=req.method,
        nist_category=nist_cat,
        volume_ids=req.volume_ids,
        risk_level=risk_level,
        status=RequestStatus.PENDING_APPROVAL,
        expires_at=expires_at,
    )
    session.add(wipe_req)
    await session.flush()

    # Log audit entry
    await log_audit_event(
        session=session,
        action="WIPE_REQUEST_CREATED",
        entity_type="WIPE_REQUEST",
        entity_id=str(wipe_req.id),
        actor_id=current_user.id,
        details={
            "device_id": str(device.id),
            "method": req.method.value if hasattr(req.method, "value") else str(req.method),
            "risk_level": risk_level.value if hasattr(risk_level, "value") else str(risk_level),
            "required_approvers": required_approvers,
        },
    )

    # Notify all approvers & admins
    approvers_stmt = select(User).where(User.role.in_([UserRole.APPROVER, UserRole.ADMIN]))
    approvers = (await session.execute(approvers_stmt)).scalars().all()

    method_str = req.method.value if hasattr(req.method, "value") else str(req.method)
    for approver in approvers:
        if approver.id != current_user.id:
            notif = Notification(
                user_id=approver.id,
                title="Wipe Approval Required",
                message=f"Operator {current_user.name} requested {method_str} on {device.manufacturer} {device.model}",
                link="/approvals",
            )
            session.add(notif)

    await session.commit()
    await session.refresh(wipe_req)

    # Broadcast real-time alert over WebSocket
    await ws_manager.broadcast_approval_alert(
        request_id=str(wipe_req.id),
        device_name=f"{device.manufacturer} {device.model}",
        requester_name=current_user.name,
        risk_level=risk_level.value,
    )

    resp = WipeRequestResponse.model_validate(wipe_req)
    resp.device_name = f"{device.manufacturer} {device.model}"
    resp.requester_name = current_user.name
    return resp


@router.get("", response_model=List[WipeRequestResponse])
async def list_wipe_requests(
    status_filter: Optional[RequestStatus] = Query(None, alias="status"),
    device_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Lists wipe requests with status and device filters."""
    stmt = select(WipeRequest).order_by(WipeRequest.created_at.desc())

    if status_filter:
        stmt = stmt.where(WipeRequest.status == status_filter)
    if device_id:
        stmt = stmt.where(WipeRequest.device_id == device_id)

    res = await session.execute(stmt)
    requests = res.scalars().all()

    responses = []
    for r in requests:
        dev = await session.get(Device, r.device_id)
        req_user = await session.get(User, r.requested_by)
        resp = WipeRequestResponse.model_validate(r)
        if dev:
            resp.device_name = f"{dev.manufacturer} {dev.model}"
        if req_user:
            resp.requester_name = req_user.name
        responses.append(resp)

    return responses


@router.get("/{request_id}", response_model=WipeRequestResponse)
async def get_wipe_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieves single wipe request record."""
    r = await session.get(WipeRequest, request_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wipe request not found")

    dev = await session.get(Device, r.device_id)
    req_user = await session.get(User, r.requested_by)
    resp = WipeRequestResponse.model_validate(r)
    if dev:
        resp.device_name = f"{dev.manufacturer} {dev.model}"
    if req_user:
        resp.requester_name = req_user.name
    return resp


@router.post("/{request_id}/cancel", response_model=WipeRequestResponse)
async def cancel_wipe_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Cancels a wipe request before execution has started."""
    r = await session.get(WipeRequest, request_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wipe request not found")

    if r.status in (RequestStatus.RUNNING, RequestStatus.VERIFYING, RequestStatus.COMPLETED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel request in status '{r.status.value}'",
        )

    r.status = RequestStatus.CANCELLED
    await log_audit_event(
        session=session,
        action="WIPE_REQUEST_CANCELLED",
        entity_type="WIPE_REQUEST",
        entity_id=str(r.id),
        actor_id=current_user.id,
    )
    await session.commit()
    await session.refresh(r)
    return WipeRequestResponse.model_validate(r)
