"""Pydantic v2 schemas for wipe requests, approvals, jobs, and events."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.models.enums import (
    ApprovalDecision,
    JobStatus,
    NISTCategory,
    RequestStatus,
    RiskLevel,
    WipeMethod,
)


class WipeRequestCreate(BaseModel):
    device_id: uuid.UUID
    volume_ids: List[uuid.UUID]
    method: WipeMethod = WipeMethod.NIST_800_88_CLEAR
    reason: str
    confirm_serial: str  # Required confirmation typing serial
    idempotency_key: Optional[str] = None


class WipeRequestResponse(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    requested_by: uuid.UUID
    reason: str
    method: WipeMethod
    nist_category: NISTCategory
    volume_ids: List[uuid.UUID]
    risk_level: RiskLevel
    status: RequestStatus
    expires_at: datetime
    decided_at: Optional[datetime] = None
    created_at: datetime
    device_name: Optional[str] = None
    requester_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ApprovalCreate(BaseModel):
    decision: ApprovalDecision
    comment: Optional[str] = None


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    request_id: uuid.UUID
    approver_id: uuid.UUID
    approver_name: Optional[str] = None
    decision: ApprovalDecision
    comment: Optional[str] = None
    request_fingerprint: str
    token_hash: str
    expires_at: datetime
    used_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApprovalResultResponse(BaseModel):
    approval: ApprovalResponse
    raw_token: Optional[str] = None  # Single-use authorization token returned upon approval


class JobStartRequest(BaseModel):
    request_id: uuid.UUID
    token: str  # Single-use authorization token
    idempotency_key: Optional[str] = None


class WipeJobEventResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    event_type: str
    message: str
    pass_number: int
    progress: float
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WipeJobResponse(BaseModel):
    id: uuid.UUID
    request_id: uuid.UUID
    approval_id: uuid.UUID
    status: JobStatus
    progress: float
    current_pass: int
    total_passes: int
    mode: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    device_name: Optional[str] = None
    certificate_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
