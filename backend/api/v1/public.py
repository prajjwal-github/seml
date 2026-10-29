"""Public, unauthenticated verification endpoints and public key discovery."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.certs.generator import verify_certificate_payload
from backend.certs.keys import get_public_keys
from backend.core.database import get_db
from backend.models import Certificate, Device, WipeJob, WipeRequest
from backend.schemas.cert import CertificateResponse, CertificateVerifyResponse

router = APIRouter(tags=["Public Verification"])


@router.get("/verify/{cert_id}", response_model=CertificateVerifyResponse)
async def public_verify_by_id(cert_id: str, session: AsyncSession = Depends(get_db)):
    """Public verification of a certificate by certificate identifier (no authentication required)."""
    stmt = select(Certificate).where(Certificate.certificate_id == cert_id)
    res = await session.execute(stmt)
    cert = res.scalar_one_or_none()

    if not cert:
        return CertificateVerifyResponse(
            status="NOT_FOUND",
            message=f"Certificate '{cert_id}' was not found in the registry.",
        )

    verif_status, reason = await verify_certificate_payload(
        session=session,
        payload=cert.payload,
        signature=cert.signature,
        public_key_id=cert.public_key_id,
    )

    cert_resp = CertificateResponse.model_validate(cert)
    return CertificateVerifyResponse(
        status=verif_status,
        message=reason or "Certificate verified",
        certificate=cert_resp,
        payload=cert.payload,
        signature=cert.signature,
        public_key_id=cert.public_key_id,
        verified_at=datetime.now(timezone.utc),
    )


class VerifyPayloadRequest(BaseModel):
    payload: Dict[str, Any]
    signature: str
    public_key_id: Optional[str] = None


@router.post("/verify", response_model=CertificateVerifyResponse)
async def public_verify_payload_or_file(
    data: Optional[VerifyPayloadRequest] = None,
    session: AsyncSession = Depends(get_db),
):
    """Verifies arbitrary certificate JSON payload and cryptographic Ed25519 signature."""
    if not data or not data.payload or not data.signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload and Ed25519 signature are required for cryptographic verification",
        )

    verif_status, reason = await verify_certificate_payload(
        session=session,
        payload=data.payload,
        signature=data.signature,
        public_key_id=data.public_key_id,
    )

    # Check if certificate exists in database for enrichment
    cert_id = data.payload.get("certificate_id")
    cert_resp = None
    if cert_id:
        stmt = select(Certificate).where(Certificate.certificate_id == cert_id)
        c = (await session.execute(stmt)).scalar_one_or_none()
        if c:
            cert_resp = CertificateResponse.model_validate(c)

    return CertificateVerifyResponse(
        status=verif_status,
        message=reason or "Verification complete",
        certificate=cert_resp,
        payload=data.payload,
        signature=data.signature,
        public_key_id=data.public_key_id or data.payload.get("public_key_id"),
        verified_at=datetime.now(timezone.utc),
    )


@router.get("/.well-known/wipe-keys")
async def well_known_signing_keys(session: AsyncSession = Depends(get_db)):
    """Standard public key discovery endpoint for independent offline verification."""
    keys = await get_public_keys(session)
    return {
        "format": "ed25519",
        "keys": keys,
        "mode": "simulation",
    }
