"""Pydantic v2 schemas for certificates and verification."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class CertificateResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    certificate_id: str
    payload: Dict[str, Any]
    payload_sha256: str
    signature: str
    public_key_id: str
    issued_at: datetime
    revoked_at: Optional[datetime] = None
    revoke_reason: Optional[str] = None
    device_model: Optional[str] = None
    method: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CertificateVerifyResponse(BaseModel):
    status: str  # VALID, TAMPERED, REVOKED, NOT_FOUND
    message: str
    certificate: Optional[CertificateResponse] = None
    payload: Optional[Dict[str, Any]] = None
    signature: Optional[str] = None
    public_key_id: Optional[str] = None
    verified_at: datetime = Field(default_factory=datetime.utcnow)


class CertificateRevokeRequest(BaseModel):
    reason: str
