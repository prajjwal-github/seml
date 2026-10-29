"""Pydantic v2 schemas for audit logs and reporting analytics."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    seq: int
    ts: datetime
    actor_id: Optional[uuid.UUID] = None
    actor_name: Optional[str] = None
    action: str
    entity_type: str
    entity_id: str
    ip: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    prev_hash: str
    hash: str

    model_config = ConfigDict(from_attributes=True)


class AuditChainVerifyResponse(BaseModel):
    is_valid: bool
    total_records: int
    error: Optional[str] = None
    verified_at: datetime = Field(default_factory=datetime.utcnow)


class ReportSummaryResponse(BaseModel):
    total_wiped: int
    wiping_now: int
    pending_approvals: int
    certificates_count: int
    by_category: Dict[str, int]
    by_method: Dict[str, int]
    average_turnaround_minutes: float
    recent_activity: List[AuditLogResponse]
