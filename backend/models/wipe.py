"""Wipe requests, approvals, jobs, job events, and certificates database models."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from backend.models.enums import (
    ApprovalDecision,
    JobStatus,
    NISTCategory,
    RequestStatus,
    RiskLevel,
    WipeMethod,
)


class WipeRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "wipe_requests"

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[WipeMethod] = mapped_column(String(50), nullable=False)
    nist_category: Mapped[NISTCategory] = mapped_column(String(50), nullable=False)
    volume_ids: Mapped[List[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(String(50), nullable=False, default=RiskLevel.LOW)
    status: Mapped[RequestStatus] = mapped_column(
        String(50), nullable=False, default=RequestStatus.PENDING_APPROVAL, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    device: Mapped["Device"] = relationship("Device", back_populates="wipe_requests")
    requester: Mapped["User"] = relationship("User", back_populates="wipe_requests", foreign_keys=[requested_by])
    approvals: Mapped[List["Approval"]] = relationship("Approval", back_populates="request", cascade="all, delete-orphan")
    job: Mapped[Optional["WipeJob"]] = relationship("WipeJob", back_populates="request", uselist=False)


class Approval(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "approvals"

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wipe_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    decision: Mapped[ApprovalDecision] = mapped_column(String(50), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    request: Mapped["WipeRequest"] = relationship("WipeRequest", back_populates="approvals")
    approver: Mapped["User"] = relationship("User", back_populates="approvals", foreign_keys=[approver_id])
    jobs: Mapped[List["WipeJob"]] = relationship("WipeJob", back_populates="approval")


class WipeJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "wipe_jobs"

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wipe_requests.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    approval_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approvals.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[JobStatus] = mapped_column(
        String(50), nullable=False, default=JobStatus.QUEUED, index=True
    )
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_pass: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    total_passes: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    mode: Mapped[str] = mapped_column(String(50), nullable=False, default="simulation")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    request: Mapped["WipeRequest"] = relationship("WipeRequest", back_populates="job")
    approval: Mapped["Approval"] = relationship("Approval", back_populates="jobs")
    events: Mapped[List["WipeJobEvent"]] = relationship(
        "WipeJobEvent",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="WipeJobEvent.created_at.asc()",
    )
    certificate: Mapped[Optional["Certificate"]] = relationship("Certificate", back_populates="job", uselist=False)


class WipeJobEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "wipe_job_events"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wipe_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    pass_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    job: Mapped["WipeJob"] = relationship("WipeJob", back_populates="events")


class Certificate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "certificates"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wipe_jobs.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    certificate_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    public_key_id: Mapped[str] = mapped_column(String(100), nullable=False)
    pdf_path: Mapped[str] = mapped_column(String(500), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    revoked_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    job: Mapped["WipeJob"] = relationship("WipeJob", back_populates="certificate")


class SigningKey(Base):
    __tablename__ = "signing_keys"

    key_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    public_key_pem: Mapped[str] = mapped_column(Text, nullable=False)
    private_key_pem: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
