"""Reports summary, KPI metrics, and analytics endpoints."""

from typing import Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user, get_db
from backend.models import (
    AuditLog,
    Certificate,
    Device,
    JobStatus,
    RequestStatus,
    User,
    WipeJob,
    WipeRequest,
)
from backend.schemas.audit import AuditLogResponse, ReportSummaryResponse

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/summary", response_model=ReportSummaryResponse)
async def get_reports_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Computes high-level KPIs, sanitization counts, turnaround times, and recent activity."""
    # Counts
    wiped_stmt = select(func.count(WipeJob.id)).where(WipeJob.status == JobStatus.COMPLETED)
    total_wiped = (await session.execute(wiped_stmt)).scalar() or 0

    running_stmt = select(func.count(WipeJob.id)).where(WipeJob.status.in_([JobStatus.RUNNING, JobStatus.VERIFYING]))
    wiping_now = (await session.execute(running_stmt)).scalar() or 0

    pending_stmt = select(func.count(WipeRequest.id)).where(WipeRequest.status == RequestStatus.PENDING_APPROVAL)
    pending_approvals = (await session.execute(pending_stmt)).scalar() or 0

    cert_stmt = select(func.count(Certificate.id))
    certs_count = (await session.execute(cert_stmt)).scalar() or 0

    # Categorization
    cat_stmt = (
        select(Device.category, func.count(WipeJob.id))
        .join(WipeRequest, WipeRequest.device_id == Device.id)
        .join(WipeJob, WipeJob.request_id == WipeRequest.id)
        .where(WipeJob.status == JobStatus.COMPLETED)
        .group_by(Device.category)
    )
    cat_res = await session.execute(cat_stmt)
    by_category = {row[0].value if hasattr(row[0], "value") else str(row[0]): row[1] for row in cat_res.all()}

    # Method
    method_stmt = (
        select(WipeRequest.method, func.count(WipeJob.id))
        .join(WipeJob, WipeJob.request_id == WipeRequest.id)
        .where(WipeJob.status == JobStatus.COMPLETED)
        .group_by(WipeRequest.method)
    )
    method_res = await session.execute(method_stmt)
    by_method = {row[0].value if hasattr(row[0], "value") else str(row[0]): row[1] for row in method_res.all()}

    # Average turnaround time
    decided_reqs = (
        await session.execute(
            select(WipeRequest).where(WipeRequest.decided_at.is_not(None))
        )
    ).scalars().all()

    turnaround_minutes = 0.0
    if decided_reqs:
        total_seconds = sum(
            (r.decided_at - r.created_at).total_seconds() for r in decided_reqs if r.decided_at and r.created_at
        )
        turnaround_minutes = round((total_seconds / len(decided_reqs)) / 60.0, 1)

    # Recent activity
    recent_stmt = select(AuditLog).order_by(AuditLog.seq.desc()).limit(10)
    recent_logs = (await session.execute(recent_stmt)).scalars().all()

    activity = []
    for l in recent_logs:
        actor = await session.get(User, l.actor_id) if l.actor_id else None
        resp = AuditLogResponse.model_validate(l)
        if actor:
            resp.actor_name = actor.name
        activity.append(resp)

    return ReportSummaryResponse(
        total_wiped=total_wiped,
        wiping_now=wiping_now,
        pending_approvals=pending_approvals,
        certificates_count=certs_count,
        by_category=by_category,
        by_method=by_method,
        average_turnaround_minutes=turnaround_minutes,
        recent_activity=activity,
    )


@router.get("/pdf")
@router.get("/project-report.pdf")
async def download_project_report_pdf():
    """Returns the official 15-page project technical report and SRS in PDF format."""
    from pathlib import Path
    from fastapi.responses import FileResponse

    pdf_path = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "SecureWipe_Project_Report.pdf"
    if not pdf_path.exists():
        from scripts.generate_report_pdf import generate_project_report
        generate_project_report(pdf_path)

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename="SecureWipe_Project_Report.pdf",
        headers={"Cache-Control": "no-cache"},
    )

