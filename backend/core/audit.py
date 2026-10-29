"""Append-only, hash-chained audit logging service and chain verification."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import canonical_json, sha256_hex
from backend.models.audit import AuditLog

GENESIS_PREV_HASH = "0" * 64


def compute_audit_hash(
    prev_hash: str,
    seq: int,
    ts: datetime,
    actor_id: Optional[uuid.UUID],
    action: str,
    entity_type: str,
    entity_id: str,
    details: Dict[str, Any],
) -> str:
    """Computes deterministic SHA-256 hash for an audit log entry."""
    actor_str = str(actor_id) if actor_id else ""
    ts_str = ts.isoformat()
    details_bytes = canonical_json(details or {})
    raw = f"{prev_hash}|{seq}|{ts_str}|{actor_str}|{action}|{entity_type}|{entity_id}|{details_bytes.decode('utf-8')}"
    return sha256_hex(raw)


async def log_audit_event(
    session: AsyncSession,
    action: str,
    entity_type: str,
    entity_id: str,
    actor_id: Optional[uuid.UUID] = None,
    ip: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """Creates and persists a cryptographically linked, append-only audit log entry."""
    details = details or {}
    ts = datetime.now(timezone.utc)

    # Fetch previous entry to obtain prev_hash and determine next sequence number
    stmt = select(AuditLog).order_by(AuditLog.seq.desc()).limit(1)
    result = await session.execute(stmt)
    last_log = result.scalar_one_or_none()

    if last_log is None:
        prev_hash = GENESIS_PREV_HASH
        seq = 1
    else:
        prev_hash = last_log.hash
        seq = last_log.seq + 1

    entry_hash = compute_audit_hash(
        prev_hash=prev_hash,
        seq=seq,
        ts=ts,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details,
    )

    log_entry = AuditLog(
        seq=seq,
        ts=ts,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        ip=ip,
        details=details,
        prev_hash=prev_hash,
        hash=entry_hash,
    )

    session.add(log_entry)
    await session.flush()
    return log_entry


async def verify_audit_chain(session: AsyncSession) -> Tuple[bool, int, Optional[str]]:
    """Verifies cryptographic integrity of the entire audit log hash chain."""
    stmt = select(AuditLog).order_by(AuditLog.seq.asc())
    result = await session.execute(stmt)
    entries = result.scalars().all()

    if not entries:
        return True, 0, None

    expected_prev_hash = GENESIS_PREV_HASH

    for idx, entry in enumerate(entries, start=1):
        if entry.seq != idx:
            return False, entry.seq, f"Sequence gap or alteration at sequence {entry.seq} (expected {idx})"

        if entry.prev_hash != expected_prev_hash:
            return (
                False,
                entry.seq,
                f"Broken prev_hash link at sequence {entry.seq}: expected {expected_prev_hash}, got {entry.prev_hash}",
            )

        expected_hash = compute_audit_hash(
            prev_hash=entry.prev_hash,
            seq=entry.seq,
            ts=entry.ts,
            actor_id=entry.actor_id,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            details=entry.details,
        )

        if entry.hash != expected_hash:
            return (
                False,
                entry.seq,
                f"Hash mismatch at sequence {entry.seq}: computed {expected_hash}, stored {entry.hash}",
            )

        expected_prev_hash = entry.hash

    return True, len(entries), None
