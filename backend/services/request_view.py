"""Builds enriched wipe request views (device, requester, decision, job, certificate) in bulk."""

import uuid
from typing import Dict, List, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Approval, Certificate, Device, User, WipeJob, WipeRequest
from backend.schemas.wipe import WipeRequestResponse


async def build_request_views(
    session: AsyncSession, requests: Sequence[WipeRequest]
) -> List[WipeRequestResponse]:
    """Returns WipeRequestResponse objects with all lifecycle details filled in."""
    if not requests:
        return []

    req_ids = [r.id for r in requests]
    device_ids = {r.device_id for r in requests}

    devices: Dict[uuid.UUID, Device] = {
        d.id: d
        for d in (await session.execute(select(Device).where(Device.id.in_(device_ids)))).scalars().all()
    }

    approvals = (
        await session.execute(
            select(Approval).where(Approval.request_id.in_(req_ids)).order_by(Approval.created_at.asc())
        )
    ).scalars().all()
    latest_approval: Dict[uuid.UUID, Approval] = {}
    for a in approvals:
        latest_approval[a.request_id] = a

    user_ids = {r.requested_by for r in requests} | {a.approver_id for a in approvals}
    users: Dict[uuid.UUID, User] = {
        u.id: u for u in (await session.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
    }

    jobs: Dict[uuid.UUID, WipeJob] = {
        j.request_id: j
        for j in (await session.execute(select(WipeJob).where(WipeJob.request_id.in_(req_ids)))).scalars().all()
    }
    certs: Dict[uuid.UUID, Certificate] = {}
    if jobs:
        job_ids = [j.id for j in jobs.values()]
        certs = {
            c.job_id: c
            for c in (await session.execute(select(Certificate).where(Certificate.job_id.in_(job_ids)))).scalars().all()
        }

    views: List[WipeRequestResponse] = []
    for r in requests:
        resp = WipeRequestResponse.model_validate(r)
        dev = devices.get(r.device_id)
        if dev:
            resp.device_name = f"{dev.manufacturer} {dev.model}"
            resp.device_serial = dev.serial_number
            resp.device_category = dev.category.value if hasattr(dev.category, "value") else str(dev.category)
        requester = users.get(r.requested_by)
        if requester:
            resp.requester_name = requester.name
        appr = latest_approval.get(r.id)
        if appr:
            approver = users.get(appr.approver_id)
            resp.approver_name = approver.name if approver else None
            resp.decision_comment = appr.comment
        job = jobs.get(r.id)
        if job:
            resp.job_id = job.id
            resp.job_status = job.status.value if hasattr(job.status, "value") else str(job.status)
            resp.job_progress = job.progress
            cert = certs.get(job.id)
            if cert:
                resp.certificate_id = cert.certificate_id
        views.append(resp)
    return views


async def build_request_view(session: AsyncSession, request: WipeRequest) -> WipeRequestResponse:
    return (await build_request_views(session, [request]))[0]
