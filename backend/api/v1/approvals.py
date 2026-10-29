"""Approvals Inbox and decision endpoints enforcing four-eyes principle and single-use tokens.

Workflow: an Operator submits a certificate request, an Approver approves or rejects it.
On approval the simulated wipe job is queued automatically, and when it finishes the
signed certificate (PDF) becomes downloadable. No manual token hand-off is needed.
"""

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
    JobStatus,
    Notification,
    RequestStatus,
    User,
    UserRole,
    WipeJob,
    WipeRequest,
)
from backend.schemas.wipe import (
    ApprovalCreate,
    ApprovalResponse,
    ApprovalResultResponse,
    WipeRequestResponse,
)
from backend.services.approval_service import ApprovalService
from backend.services.request_view import build_request_views
from backend.ws.manager import ws_manager

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get("/inbox", response_model=List[WipeRequestResponse])
async def list_approvals_inbox(
    current_user: User = Depends(require_roles([UserRole.APPROVER, UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Lists all certificate requests awaiting an Approver's decision."""
    stmt = (
        select(WipeRequest)
        .where(WipeRequest.status == RequestStatus.PENDING_APPROVAL)
        .order_by(WipeRequest.created_at.desc())
    )
    res = await session.execute(stmt)
    return await build_request_views(session, res.scalars().all())


@router.post("/{request_id}/approve", response_model=ApprovalResultResponse)
async def approve_wipe_request(
    request_id: uuid.UUID,
    req: ApprovalCreate,
    current_user: User = Depends(require_roles([UserRole.APPROVER])),
    session: AsyncSession = Depends(get_db),
):
    """Approves a certificate request and queues the sanitization job.

    Enforces:
    - Four-eyes principle: Requester can NEVER be the approver (returns 403).
    - Expiration & status validity (returns 409).
    - Cryptographic request fingerprint binding.
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

    if wipe_req.status != RequestStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve request with current status '{getattr(wipe_req.status, 'value', wipe_req.status)}'.",
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

    # Final approval: queue the simulated wipe straight away. The worker re-validates
    # the approval and fingerprint, runs the passes and issues the signed certificate.
    job = None
    if wipe_req.status == RequestStatus.APPROVED:
        job = WipeJob(
            request_id=wipe_req.id,
            approval_id=approval.id,
            status=JobStatus.QUEUED,
            progress=0.0,
            current_pass=1,
            total_passes=1,
            mode="simulation",
        )
        session.add(job)
        await session.flush()
        wipe_req.status = RequestStatus.QUEUED
        await log_audit_event(
            session=session,
            action="WIPE_JOB_QUEUED",
            entity_type="WIPE_JOB",
            entity_id=str(job.id),
            actor_id=current_user.id,
            details={"approval_id": str(approval.id), "mode": "simulation", "auto_started": True},
        )

    device = await session.get(Device, wipe_req.device_id)
    session.add(
        Notification(
            user_id=wipe_req.requested_by,
            title="Certificate request approved",
            message=f"{current_user.name} approved the request for "
            f"{device.manufacturer if device else ''} {device.model if device else ''}. Sanitization has started.",
            link="/dashboard",
        )
    )

    await session.commit()
    await session.refresh(approval)

    await ws_manager.broadcast_global(
        {"type": "request.updated", "request_id": str(wipe_req.id), "status": getattr(wipe_req.status, "value", wipe_req.status)}
    )

    appr_resp = ApprovalResponse.model_validate(approval)
    appr_resp.approver_name = current_user.name

    return ApprovalResultResponse(approval=appr_resp, raw_token=raw_token, job_id=job.id if job else None)


@router.post("/{request_id}/reject", response_model=ApprovalResponse)
async def reject_wipe_request(
    request_id: uuid.UUID,
    req: ApprovalCreate,
    current_user: User = Depends(require_roles([UserRole.APPROVER])),
    session: AsyncSession = Depends(get_db),
):
    """Rejects a certificate request with mandatory explanation comment."""
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
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
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
    session.add(
        Notification(
            user_id=wipe_req.requested_by,
            title="Certificate request rejected",
            message=f"{current_user.name} rejected your request: {req.comment.strip()}",
            link="/dashboard",
        )
    )
    await session.commit()
    await session.refresh(approval)

    await ws_manager.broadcast_global(
        {"type": "request.updated", "request_id": str(wipe_req.id), "status": "REJECTED"}
    )

    appr_resp = ApprovalResponse.model_validate(approval)
    appr_resp.approver_name = current_user.name
    return appr_resp
