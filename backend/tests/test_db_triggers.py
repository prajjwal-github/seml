"""Tests directly verifying PostgreSQL database triggers and constraints."""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import DBAPIError, ProgrammingError
from backend.core.database import AsyncSessionLocal
from backend.core.security import compute_request_fingerprint, sha256_hex
from backend.models import (
    Approval,
    ApprovalDecision,
    AuditLog,
    Device,
    DeviceCategory,
    DeviceStatus,
    JobStatus,
    NISTCategory,
    Organization,
    RequestStatus,
    RiskLevel,
    User,
    UserRole,
    WipeJob,
    WipeMethod,
    WipeRequest,
)


@pytest.fixture
async def db_session():
    """Provides a transactional database session for trigger testing."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_audit_logs_immutable_trigger_blocks_update_and_delete(db_session):
    """Verifies that trg_audit_logs_immutable blocks both UPDATE and DELETE on audit_logs."""
    from backend.core.audit import log_audit_event

    entry = await log_audit_event(
        session=db_session,
        action="TEST_ACTION",
        entity_type="SYSTEM",
        entity_id="test-123",
        details={"note": "immutability test"},
    )
    await db_session.commit()
    test_seq = entry.seq

    # Attempt UPDATE -> must raise exception from trigger
    with pytest.raises(DBAPIError) as exc_update:
        await db_session.execute(
            update(AuditLog).where(AuditLog.seq == test_seq).values(action="TAMPERED_ACTION")
        )
        await db_session.commit()
    await db_session.rollback()
    assert "audit_logs is append-only" in str(exc_update.value)

    # Attempt DELETE -> must raise exception from trigger
    with pytest.raises(DBAPIError) as exc_delete:
        await db_session.execute(
            delete(AuditLog).where(AuditLog.seq == test_seq)
        )
        await db_session.commit()
    await db_session.rollback()
    assert "audit_logs is append-only" in str(exc_delete.value)


@pytest.mark.asyncio
async def test_four_eyes_trigger_blocks_self_approval(db_session):
    """Verifies that trg_approvals_four_eyes raises exception if requester attempts self-approval."""
    # Create test user
    user = User(
        email=f"operator-{uuid.uuid4().hex[:6]}@test.local",
        name="Test Operator",
        password_hash="argon2id$mock",
        role=UserRole.OPERATOR,
    )
    db_session.add(user)
    await db_session.flush()

    # Create test device
    device = Device(
        category=DeviceCategory.LAPTOP,
        manufacturer="Lenovo",
        model="ThinkPad T14",
        serial_number=f"SN-{uuid.uuid4().hex[:8]}",
        status=DeviceStatus.ONLINE,
    )
    db_session.add(device)
    await db_session.flush()

    # Create wipe request requested by user
    req = WipeRequest(
        device_id=device.id,
        requested_by=user.id,
        reason="Decommissioning",
        method=WipeMethod.NIST_800_88_CLEAR,
        nist_category=NISTCategory.CLEAR,
        volume_ids=[],
        status=RequestStatus.PENDING_APPROVAL,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db_session.add(req)
    await db_session.flush()

    # Attempt to insert an approval where approver_id == requested_by
    approval = Approval(
        request_id=req.id,
        approver_id=user.id,  # SAME USER -> FOUR-EYES VIOLATION
        decision=ApprovalDecision.APPROVED,
        request_fingerprint="mock_fp",
        token_hash=sha256_hex("mock_token"),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db_session.add(approval)

    with pytest.raises(DBAPIError) as exc:
        await db_session.flush()
    await db_session.rollback()
    assert "Four-eyes rule violation" in str(exc.value)


@pytest.mark.asyncio
async def test_wipe_job_trigger_requires_valid_approval(db_session):
    """Verifies that trg_wipe_jobs_valid_approval rejects direct wipe_jobs insert without approved approval."""
    # Create test user & device & request
    user = User(
        email=f"user-{uuid.uuid4().hex[:6]}@test.local",
        name="Test Requester",
        password_hash="mock",
        role=UserRole.OPERATOR,
    )
    db_session.add(user)
    await db_session.flush()

    device = Device(
        category=DeviceCategory.DESKTOP,
        manufacturer="Dell",
        model="OptiPlex 7090",
        serial_number=f"SN-{uuid.uuid4().hex[:8]}",
        status=DeviceStatus.ONLINE,
    )
    db_session.add(device)
    await db_session.flush()

    req = WipeRequest(
        device_id=device.id,
        requested_by=user.id,
        reason="Sanitization",
        method=WipeMethod.NIST_800_88_CLEAR,
        nist_category=NISTCategory.CLEAR,
        volume_ids=[],
        status=RequestStatus.APPROVED,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db_session.add(req)
    await db_session.flush()

    # Create dummy random approval_id that does not exist
    fake_approval_id = uuid.uuid4()

    job = WipeJob(
        request_id=req.id,
        approval_id=fake_approval_id,
        status=JobStatus.QUEUED,
        mode="simulation",
    )
    db_session.add(job)

    with pytest.raises(DBAPIError) as exc:
        await db_session.flush()
    await db_session.rollback()
    assert "Job validation error" in str(exc.value)


@pytest.mark.asyncio
async def test_wipe_request_state_machine_trigger(db_session):
    """Verifies that trg_wipe_requests_transition blocks illegal status transitions."""
    user = User(
        email=f"user-{uuid.uuid4().hex[:6]}@test.local",
        name="Test Requester",
        password_hash="mock",
        role=UserRole.OPERATOR,
    )
    device = Device(
        category=DeviceCategory.SERVER,
        manufacturer="HP",
        model="ProLiant DL380",
        serial_number=f"SN-{uuid.uuid4().hex[:8]}",
        status=DeviceStatus.ONLINE,
    )
    db_session.add_all([user, device])
    await db_session.flush()

    req = WipeRequest(
        device_id=device.id,
        requested_by=user.id,
        reason="Testing state machine",
        method=WipeMethod.NIST_800_88_PURGE,
        nist_category=NISTCategory.PURGE,
        volume_ids=[],
        status=RequestStatus.DRAFT,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db_session.add(req)
    await db_session.commit()

    # Attempt illegal transition: DRAFT directly to COMPLETED
    req.status = RequestStatus.COMPLETED
    with pytest.raises(DBAPIError) as exc:
        await db_session.commit()
    await db_session.rollback()
    assert "Illegal wipe request transition" in str(exc.value)
