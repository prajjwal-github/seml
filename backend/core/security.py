"""Security, Argon2id hashing, JWT generation, Ed25519 signing, and fingerprinting utilities."""

import base64
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
import jwt

from backend.core.config import settings

# Initialize Argon2id password hasher with secure parameters
pwd_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2id."""
    return pwd_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a password against an Argon2id hash."""
    try:
        return pwd_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def create_access_token(
    user_id: uuid.UUID,
    role: str,
    org_id: Optional[uuid.UUID] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generates a signed JWT access token (default 15 minutes)."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": str(user_id),
        "role": role,
        "org_id": str(org_id) if org_id else None,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: uuid.UUID,
    expires_delta: Optional[timedelta] = None,
) -> Tuple[str, str]:
    """Generates a rotating JWT refresh token with unique jti (default 7 days)."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def decode_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT token."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


# --- Canonical JSON & Cryptographic Fingerprinting ---

def canonical_json(data: Any) -> bytes:
    """Produces RFC 8785 canonical JSON bytes (deterministic ordering, compact)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: Union[str, bytes]) -> str:
    """Calculates SHA-256 hexadecimal digest."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def compute_request_fingerprint(
    device_id: Union[uuid.UUID, str],
    volume_ids: List[Union[uuid.UUID, str]],
    method: str,
    serial_number: str,
) -> str:
    """Computes deterministic request fingerprint SHA-256(device_id + sorted(volume_ids) + method + serial)."""
    sorted_vols = sorted(str(v) for v in volume_ids)
    raw = f"{str(device_id)}|{','.join(sorted_vols)}|{method}|{serial_number.strip()}"
    return sha256_hex(raw)


# --- Ed25519 Asymmetric Key Management & Signing ---

def generate_ed25519_keypair() -> Tuple[str, str]:
    """Generates a new Ed25519 keypair and returns (public_pem, private_pem)."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return public_pem, private_pem


def sign_payload_ed25519(payload_bytes: bytes, private_pem: str) -> str:
    """Signs bytes using Ed25519 and returns Base64-encoded signature."""
    private_key = serialization.load_pem_private_key(
        private_pem.encode("utf-8"),
        password=None,
    )
    if not isinstance(private_key, ed25519.Ed25519PrivateKey):
        raise ValueError("Invalid key type for Ed25519 signing")
    signature = private_key.sign(payload_bytes)
    return base64.b64encode(signature).decode("utf-8")


def verify_signature_ed25519(payload_bytes: bytes, signature_b64: str, public_pem: str) -> bool:
    """Verifies Ed25519 signature against payload bytes."""
    try:
        public_key = serialization.load_pem_public_key(public_pem.encode("utf-8"))
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            return False
        signature = base64.b64decode(signature_b64)
        public_key.verify(signature, payload_bytes)
        return True
    except (InvalidSignature, Exception):
        return False
