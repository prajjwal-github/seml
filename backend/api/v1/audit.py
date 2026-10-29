"""Audit log queries, cryptographic chain verification, and CSV export."""

import csv
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, require_roles
from backend.core.audit import verify_audit_chain
from backend.models import AuditLog, User, UserRole
from backend.schemas.audit import AuditChainVerifyResponse, AuditLogResponse

router = APIRouter(prefix="/audit", tags=["Audit Log"])


@router.get("", response_model=List[AuditLogResponse])
async def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by audit action"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.APPROVER])),
    session: AsyncSession = Depends(get_db),
):
    """Lists chronological audit log records with filtering and pagination."""
    stmt = select(AuditLog).order_by(AuditLog.seq.desc()).limit(limit).offset(offset)

    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)

    res = await session.execute(stmt)
    logs = res.scalars().all()

    responses = []
    for l in logs:
        actor = await session.get(User, l.actor_id) if l.actor_id else None
        resp = AuditLogResponse.model_validate(l)
        if actor:
            resp.actor_name = actor.name
        responses.append(resp)

    return responses


@router.get("/verify-chain", response_model=AuditChainVerifyResponse)
async def verify_chain_integrity(
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.APPROVER])),
    session: AsyncSession = Depends(get_db),
):
    """Cryptographically verifies the append-only SHA-256 hash chain from genesis to current entry."""
    is_valid, count, error = await verify_audit_chain(session)
    return AuditChainVerifyResponse(
        is_valid=is_valid,
        total_records=count,
        error=error,
    )


@router.get("/export.csv")
async def export_audit_logs_csv(
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.APPROVER])),
    session: AsyncSession = Depends(get_db),
):
    """Exports full hash-chained audit log records to CSV."""
    stmt = select(AuditLog).order_by(AuditLog.seq.asc())
    res = await session.execute(stmt)
    logs = res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Sequence",
        "Timestamp",
        "Actor ID",
        "Action",
        "Entity Type",
        "Entity ID",
        "IP Address",
        "Details JSON",
        "Previous Hash",
        "Current Hash",
    ])

    for l in logs:
        writer.writerow([
            l.seq,
            l.ts.isoformat(),
            str(l.actor_id) if l.actor_id else "",
            l.action,
            l.entity_type,
            l.entity_id,
            l.ip or "",
            str(l.details),
            l.prev_hash,
            l.hash,
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="securewipe_audit_log.csv"'},
    )
