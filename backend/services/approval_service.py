"""Approval service managing dual-custody workflows, risk assessment, and single-use tokens."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.security import compute_request_fingerprint, sha256_hex
from backend.models import (
    Approval,
    ApprovalDecision,
    Device,
    RequestStatus,
    RiskLevel,
    StorageVolume,
    User,
    UserRole,
    WipeMethod,
    WipeRequest,
)


class ApprovalService:
    """Handles wipe request risk evaluation, four-eyes enforcement, and token issuance."""

    @classmethod
    def evaluate_risk(
        cls,
        volumes: List[StorageVolume],
        method: WipeMethod,
        is_production: bool = False,
        batch_size: int = 1,
    ) -> Tuple[RiskLevel, int]:
        """Calculates risk level and required number of distinct approvers (1 or 2)."""
        has_boot_or_system = any(v.is_boot or v.is_system for v in volumes)
        is_purge = method == WipeMethod.NIST_800_88_PURGE
        is_large_batch = batch_size > 5

        if has_boot_or_system or (is_purge and is_production) or is_large_batch:
            return RiskLevel.HIGH, 2

        if is_purge or len(volumes) > 2:
            return RiskLevel.MEDIUM, 1

        return RiskLevel.LOW, 1

    @classmethod
    async def create_approval(
        cls,
        session: AsyncSession,
        request: WipeRequest,
        approver: User,
        decision: ApprovalDecision,
        comment: Optional[str] = None,
    ) -> Tuple[Approval, str]:
        """Validates approval rules, calculates fingerprint, and issues single-use token."""
        # 1. Four-eyes enforcement
        if request.requested_by == approver.id:
            raise PermissionError("Four-eyes violation: Requester cannot approve their own wipe request.")

        # 2. Check if request is in valid state for approval
        req_status = request.status.value if hasattr(request.status, "value") else str(request.status)
        if req_status != RequestStatus.PENDING_APPROVAL.value and req_status != "PENDING_APPROVAL":
            raise ValueError(f"Cannot approve request with status '{req_status}'. Request is not pending approval.")

        # Check existing approvals for this request
        stmt = select(Approval).where(Approval.request_id == request.id)
        res = await session.execute(stmt)
        existing_approvals = res.scalars().all()

        # Cannot submit multiple decisions by the same approver
        for prev in existing_approvals:
            if prev.approver_id == approver.id:
                raise ValueError("You have already submitted an approval decision for this request.")

        req_risk = request.risk_level.value if hasattr(request.risk_level, "value") else str(request.risk_level)
        required_approvers = 2 if req_risk in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value, "HIGH", "CRITICAL") else 1
        approved_count = sum(
            1 for a in existing_approvals 
            if (a.decision.value if hasattr(a.decision, "value") else str(a.decision)) in (ApprovalDecision.APPROVED.value, "APPROVED")
        )
        if approved_count >= required_approvers:
            raise ValueError("Wipe request is already fully approved.")

        # 3. Check if request has expired
        now = datetime.now(timezone.utc)
        if request.expires_at < now:
            request.status = RequestStatus.EXPIRED
            await session.commit()
            raise ValueError("Wipe request has expired and cannot be approved.")

        # 4. Mandatory comment on rejection
        if decision == ApprovalDecision.REJECTED and not comment:
            raise ValueError("A comment explaining rejection is mandatory.")

        # Fetch device to get serial number for fingerprint
        device = await session.get(Device, request.device_id)
        if not device:
            raise ValueError("Target device not found.")

        # Compute tamper-evident request fingerprint
        method_str = request.method.value if hasattr(request.method, "value") else str(request.method)
        fingerprint = compute_request_fingerprint(
            device_id=request.device_id,
            volume_ids=request.volume_ids,
            method=method_str,
            serial_number=device.serial_number,
        )

        # Generate cryptographically secure single-use token
        raw_token = secrets.token_hex(32)
        token_hash = sha256_hex(raw_token)
        expiry = now + timedelta(hours=settings.APPROVAL_EXPIRY_HOURS)

        approval = Approval(
            request_id=request.id,
            approver_id=approver.id,
            decision=decision,
            comment=comment,
            request_fingerprint=fingerprint,
            token_hash=token_hash,
            expires_at=expiry,
            used_at=None,
        )
        session.add(approval)

        if decision == ApprovalDecision.REJECTED:
            request.status = RequestStatus.REJECTED
            request.decided_at = now
        else:
            # Check how many approvals exist for this request
            stmt = select(Approval).where(
                Approval.request_id == request.id,
                Approval.decision == ApprovalDecision.APPROVED,
            )
            res = await session.execute(stmt)
            existing_approvals = res.scalars().all()
            total_approvals = len(existing_approvals) + 1  # including this one

            req_risk = request.risk_level.value if hasattr(request.risk_level, "value") else str(request.risk_level)
            required_approvers = 2 if req_risk in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value, "HIGH", "CRITICAL") else 1
            if total_approvals >= required_approvers:
                request.status = RequestStatus.APPROVED
                request.decided_at = now

        await session.flush()
        return approval, raw_token

    @classmethod
    async def validate_token_and_fingerprint(
        cls,
        session: AsyncSession,
        request: WipeRequest,
        raw_token: str,
    ) -> Approval:
        """Validates approval token, single-use state, and matching request fingerprint."""
        token_hash = sha256_hex(raw_token)
        stmt = select(Approval).where(
            Approval.request_id == request.id,
            Approval.token_hash == token_hash,
        )
        res = await session.execute(stmt)
        approval = res.scalar_one_or_none()

        if not approval:
            raise ValueError("Invalid approval token provided.")

        appr_decision = approval.decision.value if hasattr(approval.decision, "value") else str(approval.decision)
        if appr_decision not in (ApprovalDecision.APPROVED.value, "APPROVED"):
            raise ValueError("Approval was not granted for this request.")

        now = datetime.now(timezone.utc)
        if approval.expires_at < now:
            raise ValueError("Approval has expired.")

        if approval.used_at is not None:
            raise ValueError("Approval token has already been used.")

        # Recompute fingerprint against current device and volumes to catch any tampering/edits
        device = await session.get(Device, request.device_id)
        if not device:
            raise ValueError("Associated device not found.")

        method_str = request.method.value if hasattr(request.method, "value") else str(request.method)
        current_fingerprint = compute_request_fingerprint(
            device_id=request.device_id,
            volume_ids=request.volume_ids,
            method=method_str,
            serial_number=device.serial_number,
        )

        if current_fingerprint != approval.request_fingerprint:
            raise ValueError("Request fingerprint mismatch! Request or device was modified after approval.")

        return approval
