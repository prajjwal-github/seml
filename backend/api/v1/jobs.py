"""Wipe job execution, streaming status, event logs, and cancellation endpoints."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user, get_db, require_roles
from backend.core.audit import log_audit_event
from backend.models import (
    Approval,
    Certificate,
    Device,
    JobStatus,
    RequestStatus,
    User,
    UserRole,
    WipeJob,
    WipeJobEvent,
    WipeRequest,
)
from backend.schemas.wipe import (
    JobStartRequest,
    WipeJobEventResponse,
    WipeJobResponse,
)
from backend.services.approval_service import ApprovalService
from backend.wipe.worker import wipe_worker
from backend.ws.manager import ws_manager

router = APIRouter(prefix="/jobs", tags=["Wipe Jobs"])


@router.post("/start", response_model=WipeJobResponse, status_code=status.HTTP_201_CREATED)
async def start_wipe_job(
    req: JobStartRequest,
    current_user: User = Depends(require_roles([UserRole.OPERATOR])),
    session: AsyncSession = Depends(get_db),
):
    """Starts a wipe job by validating the single-use token and matching approval.

    Negative paths enforced:
    - Start without valid approval -> 409 Conflict.
    - Reusing an already used approval token -> 409 Conflict.
    - Fingerprint mismatch from modified request -> 409 Conflict.
    """
    wipe_req = await session.get(WipeRequest, req.request_id)
    if not wipe_req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wipe request not found")

    # Check if job already created
    stmt = select(WipeJob).where(WipeJob.request_id == wipe_req.id)
    existing_job = (await session.execute(stmt)).scalar_one_or_none()
    if existing_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A wipe job already exists for this request",
        )

    # Validate approval, token, and fingerprint
    try:
        approval = await ApprovalService.validate_token_and_fingerprint(
            session=session,
            request=wipe_req,
            raw_token=req.token,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ve))

    # Create job in QUEUED status
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

    wipe_req.status = RequestStatus.QUEUED
    await log_audit_event(
        session=session,
        action="WIPE_JOB_QUEUED",
        entity_type="WIPE_JOB",
        entity_id=str(job.id),
        actor_id=current_user.id,
        details={"approval_id": str(approval.id), "mode": "simulation"},
    )

    await session.commit()
    await session.refresh(job)

    dev = await session.get(Device, wipe_req.device_id)
    resp = WipeJobResponse.model_validate(job)
    if dev:
        resp.device_name = f"{dev.manufacturer} {dev.model}"

    await ws_manager.broadcast_job_progress(
        job_id=str(job.id),
        progress=0.0,
        current_pass=1,
        total_passes=1,
        message="Job queued for simulated sanitization",
        status="QUEUED",
    )

    return resp


@router.get("", response_model=List[WipeJobResponse])
async def list_jobs(
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Lists all wipe jobs and their execution states."""
    stmt = select(WipeJob).order_by(WipeJob.created_at.desc())
    if current_user.role == UserRole.OPERATOR:
        stmt = stmt.join(WipeRequest, WipeRequest.id == WipeJob.request_id).where(
            WipeRequest.requested_by == current_user.id
        )
    if status_filter:
        stmt = stmt.where(WipeJob.status == status_filter)

    res = await session.execute(stmt)
    jobs = res.scalars().all()

    responses = []
    for j in jobs:
        req = await session.get(WipeRequest, j.request_id)
        dev = await session.get(Device, req.device_id) if req else None
        cert_stmt = select(Certificate).where(Certificate.job_id == j.id)
        cert = (await session.execute(cert_stmt)).scalar_one_or_none()

        resp = WipeJobResponse.model_validate(j)
        if dev:
            resp.device_name = f"{dev.manufacturer} {dev.model}"
        if cert:
            resp.certificate_id = cert.certificate_id
        responses.append(resp)

    return responses


@router.get("/{job_id}", response_model=WipeJobResponse)
async def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieves single job record with latest progress and execution result."""
    job = await session.get(WipeJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wipe job not found")

    req = await session.get(WipeRequest, job.request_id)
    dev = await session.get(Device, req.device_id) if req else None
    cert_stmt = select(Certificate).where(Certificate.job_id == job.id)
    cert = (await session.execute(cert_stmt)).scalar_one_or_none()

    resp = WipeJobResponse.model_validate(job)
    if dev:
        resp.device_name = f"{dev.manufacturer} {dev.model}"
    if cert:
        resp.certificate_id = cert.certificate_id
    return resp


@router.get("/{job_id}/events", response_model=List[WipeJobEventResponse])
async def get_job_events(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Returns streaming log events and pass history for console display."""
    stmt = (
        select(WipeJobEvent)
        .where(WipeJobEvent.job_id == job_id)
        .order_by(WipeJobEvent.created_at.asc())
    )
    res = await session.execute(stmt)
    events = res.scalars().all()
    return [WipeJobEventResponse.model_validate(e) for e in events]


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: uuid.UUID,
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Cancels a running or queued job."""
    job = await session.get(WipeJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wipe job not found")

    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job has already concluded")

    cancelled = wipe_worker.cancel_job(job_id)
    if not cancelled:
        job.status = JobStatus.CANCELLED
        req = await session.get(WipeRequest, job.request_id)
        if req:
            req.status = RequestStatus.CANCELLED
        await session.commit()

    await log_audit_event(
        session=session,
        action="WIPE_JOB_CANCELLED",
        entity_type="WIPE_JOB",
        entity_id=str(job.id),
        actor_id=current_user.id,
    )
    await session.commit()
    return {"status": "success", "message": "Job cancellation initiated"}
