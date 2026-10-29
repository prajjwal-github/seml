"""Certificates listing, PDF downloads, and revocation endpoints."""

import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user, get_db, require_roles
from backend.core.audit import log_audit_event
from backend.models import Certificate, Device, User, UserRole, WipeJob, WipeRequest
from backend.schemas.cert import CertificateResponse, CertificateRevokeRequest

router = APIRouter(prefix="/certificates", tags=["Certificates"])


@router.get("", response_model=List[CertificateResponse])
async def list_certificates(
    search: Optional[str] = Query(None, description="Search certificate ID or device model"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Lists all issued certificates of sanitization."""
    stmt = select(Certificate).order_by(Certificate.issued_at.desc())
    res = await session.execute(stmt)
    certs = res.scalars().all()

    responses = []
    for c in certs:
        job = await session.get(WipeJob, c.job_id)
        req = await session.get(WipeRequest, job.request_id) if job else None
        dev = await session.get(Device, req.device_id) if req else None

        resp = CertificateResponse.model_validate(c)
        if dev:
            resp.device_model = f"{dev.manufacturer} {dev.model}"
        if req:
            resp.method = req.method.value if hasattr(req.method, "value") else str(req.method)

        if search:
            term = search.lower()
            if (
                term not in c.certificate_id.lower()
                and term not in (resp.device_model or "").lower()
            ):
                continue

        responses.append(resp)

    return responses


@router.get("/{cert_id}", response_model=CertificateResponse)
async def get_certificate(
    cert_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieves single certificate record and payload."""
    stmt = select(Certificate).where(
        (Certificate.certificate_id == cert_id)
        | (Certificate.id == uuid.UUID(cert_id) if len(cert_id) == 36 else False)
    )
    res = await session.execute(stmt)
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    job = await session.get(WipeJob, c.job_id)
    req = await session.get(WipeRequest, job.request_id) if job else None
    dev = await session.get(Device, req.device_id) if req else None

    resp = CertificateResponse.model_validate(c)
    if dev:
        resp.device_model = f"{dev.manufacturer} {dev.model}"
    if req:
        resp.method = req.method.value if hasattr(req.method, "value") else str(req.method)
    return resp


@router.get("/{cert_id}/pdf")
async def download_certificate_pdf(
    cert_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Downloads the official signed ReportLab PDF certificate with verification QR code."""
    stmt = select(Certificate).where(
        (Certificate.certificate_id == cert_id)
        | (Certificate.id == uuid.UUID(cert_id) if len(cert_id) == 36 else False)
    )
    res = await session.execute(stmt)
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    if not os.path.exists(c.pdf_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF file not found on server")

    return FileResponse(
        c.pdf_path,
        media_type="application/pdf",
        filename=f"{c.certificate_id}.pdf",
    )


@router.post("/{cert_id}/revoke", response_model=CertificateResponse)
async def revoke_certificate(
    cert_id: str,
    req: CertificateRevokeRequest,
    current_admin: User = Depends(require_roles([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Revokes a certificate of sanitization with mandatory explanation (Admin only)."""
    stmt = select(Certificate).where(
        (Certificate.certificate_id == cert_id)
        | (Certificate.id == uuid.UUID(cert_id) if len(cert_id) == 36 else False)
    )
    res = await session.execute(stmt)
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    if c.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Certificate is already revoked")

    c.revoked_at = datetime.now(timezone.utc)
    c.revoke_reason = req.reason.strip()
    c.revoked_by = current_admin.id

    await log_audit_event(
        session=session,
        action="CERTIFICATE_REVOKED",
        entity_type="CERTIFICATE",
        entity_id=c.certificate_id,
        actor_id=current_admin.id,
        details={"reason": req.reason},
    )
    await session.commit()
    await session.refresh(c)
    return CertificateResponse.model_validate(c)
