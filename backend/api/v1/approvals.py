"""Approvals Inbox and decision endpoints enforcing four-eyes principle and single-use tokens."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, require_roles
from backend.core.audit import log_audit_event
from backend.models import (
    ApprovalDecision,
    Device,
    RequestStatus,
    User,
    UserRole,
    WipeRequest,
)
from backend.schemas.wipe import (
    ApprovalCreate,
    ApprovalResponse,
    ApprovalResultResponse,
    WipeRequestResponse,
)
from backend.services.approval_service import ApprovalService

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get("/inbox", response_model=List[WipeRequestResponse])
async def list_approvals_inbox(
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.APPROVER, UserRole.ADMIN, UserRole.AUDITOR])),
    session: AsyncSession = Depends(get_db),
):
    """Lists all pending wipe requests awaiting dual-custody approval."""
    stmt = (
        select(WipeRequest)
        .where(WipeRequest.status == RequestStatus.PENDING_APPROVAL)
        .order_by(WipeRequest.created_at.desc())
    )
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


@router.post("/{request_id}/approve", response_model=ApprovalResultResponse)
async def approve_wipe_request(
    request_id: uuid.UUID,
    req: ApprovalCreate,
    current_user: User = Depends(require_roles([UserRole.APPROVER, UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Approves a wipe request.

    Enforces:
    - Four-eyes principle: Requester can NEVER be the approver (returns 403).
    - Expiration & status validity (returns 409).
    - Cryptographic request fingerprint binding.
    - Single-use authorization token issuance.
    """
    wipe_req = await session.get(WipeRequest, request_id)
    if not wipe_req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wipe request not found")

    # Enforce four-eyes principle
    if wipe_req.requested_by == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Four-eyes rule violation: Requester cannot approve their own wipe request.",
        )

    if wipe_req.status not in (RequestStatus.PENDING_APPROVAL, RequestStatus.APPROVED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve request with current status '{wipe_req.status.value}'.",
        )

    try:
        approval, raw_token = await ApprovalService.create_approval(
            session=session,
            request=wipe_req,
            approver=current_user,
            decision=ApprovalDecision.APPROVED,
            comment=req.comment,
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ve))

    await log_audit_event(
        session=session,
        action="WIPE_REQUEST_APPROVED",
        entity_type="APPROVAL",
        entity_id=str(approval.id),
        actor_id=current_user.id,
        details={
            "request_id": str(wipe_req.id),
            "fingerprint": approval.request_fingerprint,
        },
    )
    await session.commit()
    await session.refresh(approval)

    appr_resp = ApprovalResponse.model_validate(approval)
    appr_resp.approver_name = current_user.name

    return ApprovalResultResponse(approval=appr_resp, raw_token=raw_token)


@router.post("/{request_id}/reject", response_model=ApprovalResponse)
async def reject_wipe_request(
    request_id: uuid.UUID,
    req: ApprovalCreate,
    current_user: User = Depends(require_roles([UserRole.APPROVER, UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Rejects a wipe request with mandatory explanation comment."""
    wipe_req = await session.get(WipeRequest, request_id)
    if not wipe_req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wipe request not found")

    if not req.comment or not req.comment.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A written comment is mandatory when rejecting a wipe request.",
        )

    try:
        approval, _ = await ApprovalService.create_approval(
            session=session,
            request=wipe_req,
            approver=current_user,
            decision=ApprovalDecision.REJECTED,
            comment=req.comment.strip(),
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    await log_audit_event(
        session=session,
        action="WIPE_REQUEST_REJECTED",
        entity_type="APPROVAL",
        entity_id=str(approval.id),
        actor_id=current_user.id,
        details={"request_id": str(wipe_req.id), "reason": req.comment},
    )
    await session.commit()
    await session.refresh(approval)

    appr_resp = ApprovalResponse.model_validate(approval)
    appr_resp.approver_name = current_user.name
    return appr_resp
