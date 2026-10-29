"""Ed25519 signing key lifecycle, active key discovery, and key rotation."""

import uuid
from datetime import datetime, timezone
from typing import Dict, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.security import generate_ed25519_keypair
from backend.models.wipe import SigningKey


async def get_or_create_active_signing_key(session: AsyncSession) -> SigningKey:
    """Returns the currently active Ed25519 signing key or generates one on first boot."""
    stmt = select(SigningKey).where(SigningKey.is_active == True).limit(1)
    res = await session.execute(stmt)
    key = res.scalar_one_or_none()

    if key is not None:
        return key

    # Generate new keypair on first initialization
    public_pem, private_pem = generate_ed25519_keypair()
    key_id = f"KEY-ED25519-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:8].upper()}"

    new_key = SigningKey(
        key_id=key_id,
        public_key_pem=public_pem,
        private_key_pem=private_pem,
        is_active=True,
    )
    session.add(new_key)
    await session.commit()
    return new_key


async def rotate_signing_key(session: AsyncSession) -> SigningKey:
    """Deactivates current signing keys and initializes a new active Ed25519 key."""
    await session.execute(update(SigningKey).values(is_active=False))

    public_pem, private_pem = generate_ed25519_keypair()
    key_id = f"KEY-ED25519-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:8].upper()}"

    new_key = SigningKey(
        key_id=key_id,
        public_key_pem=public_pem,
        private_key_pem=private_pem,
        is_active=True,
    )
    session.add(new_key)
    await session.commit()
    return new_key


async def get_public_keys(session: AsyncSession) -> List[Dict[str, str]]:
    """Lists public keys for the standard /.well-known/wipe-keys endpoint."""
    stmt = select(SigningKey).order_by(SigningKey.created_at.desc())
    res = await session.execute(stmt)
    keys = res.scalars().all()
    return [
        {
            "key_id": k.key_id,
            "public_key_pem": k.public_key_pem,
            "is_active": k.is_active,
            "created_at": k.created_at.isoformat(),
        }
        for k in keys
    ]
