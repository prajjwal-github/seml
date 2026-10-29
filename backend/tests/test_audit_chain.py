"""Unit and integration tests for cryptographic audit log hash chaining."""

import uuid
import pytest
from backend.core.audit import compute_audit_hash, log_audit_event, verify_audit_chain
from backend.core.database import AsyncSessionLocal
from backend.models.audit import AuditLog


@pytest.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_audit_hash_chain_creation_and_verification(db_session):
    """Verifies that multiple audit log entries form an unbroken cryptographic chain."""
    actor_id = uuid.uuid4()

    # Log 3 events
    log1 = await log_audit_event(
        session=db_session,
        action="DEVICE_REGISTERED",
        entity_type="DEVICE",
        entity_id="DEV-001",
        actor_id=actor_id,
        details={"model": "ThinkPad"},
    )
    await db_session.commit()

    log2 = await log_audit_event(
        session=db_session,
        action="REQUEST_SUBMITTED",
        entity_type="WIPE_REQUEST",
        entity_id="REQ-001",
        actor_id=actor_id,
        details={"method": "CLEAR"},
    )
    await db_session.commit()

    log3 = await log_audit_event(
        session=db_session,
        action="REQUEST_APPROVED",
        entity_type="APPROVAL",
        entity_id="APP-001",
        actor_id=actor_id,
        details={"decision": "APPROVED"},
    )
    await db_session.commit()

    # Verify link: log2.prev_hash == log1.hash, log3.prev_hash == log2.hash
    assert log2.prev_hash == log1.hash
    assert log3.prev_hash == log2.hash

    # Verify chain integrity function
    is_valid, count, error = await verify_audit_chain(db_session)
    assert is_valid is True
    assert count >= 3
    assert error is None
