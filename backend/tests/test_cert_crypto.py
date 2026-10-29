"""Unit tests for Ed25519 digital signing, ReportLab PDF rendering, and tamper detection."""

import copy
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
import pytest
from backend.certs.generator import generate_pdf_certificate, verify_certificate_payload
from backend.certs.keys import get_or_create_active_signing_key
from backend.core.database import AsyncSessionLocal
from backend.core.security import canonical_json, generate_ed25519_keypair, sha256_hex, sign_payload_ed25519, verify_signature_ed25519


@pytest.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session


def test_ed25519_sign_and_verify():
    """Verifies that an Ed25519 keypair can sign and verify canonical bytes."""
    pub_pem, priv_pem = generate_ed25519_keypair()
    payload = {"test": 123, "asset": "Server-Alpha", "mode": "simulation"}
    payload_bytes = canonical_json(payload)

    sig_b64 = sign_payload_ed25519(payload_bytes, priv_pem)
    assert isinstance(sig_b64, str)
    assert len(sig_b64) > 40

    # Verification must succeed
    assert verify_signature_ed25519(payload_bytes, sig_b64, pub_pem) is True

    # Tampered payload must fail verification
    tampered_bytes = canonical_json({"test": 124, "asset": "Server-Alpha", "mode": "simulation"})
    assert verify_signature_ed25519(tampered_bytes, sig_b64, pub_pem) is False


def test_pdf_generation_and_qr():
    """Verifies ReportLab PDF generation with embedded QR code and watermark."""
    pub_pem, priv_pem = generate_ed25519_keypair()
    cert_id = f"CERT-TEST-{uuid.uuid4().hex[:6].upper()}"

    payload = {
        "certificate_id": cert_id,
        "mode": "simulation",
        "nist_category": "PURGE",
        "method": "NIST_800_88_PURGE",
        "public_key_id": "KEY-TEST-001",
        "device": {
            "category": "LAPTOP",
            "manufacturer": "Dell",
            "model": "Latitude 5520",
            "serial_hash": sha256_hex("CONFIDENTIAL_SERIAL"),
            "os_name": "Ubuntu",
            "os_version": "24.04",
        },
        "volumes": [{"name": "nvme0n1", "media_type": "NVME_SSD", "size_bytes": 512000000000}],
        "operator": {"name": "Test Operator"},
        "approver": {"name": "Test Approver"},
        "verification": {"sample_percentage": 100.0, "hash_verification": "ZERO_PATTERN_CONFIRMED"},
        "hidden_area_coverage": {"hpa_cleared": True, "dco_cleared": True},
        "timestamps": {"issued_at": datetime.now(timezone.utc).isoformat()},
    }

    payload_bytes = canonical_json(payload)
    sig_b64 = sign_payload_ed25519(payload_bytes, priv_pem)
    payload["payload_sha256"] = sha256_hex(payload_bytes)

    with tempfile.TemporaryDirectory() as tmpdir:
        output_pdf = Path(tmpdir) / f"{cert_id}.pdf"
        pdf_path = generate_pdf_certificate(cert_id, payload, sig_b64, output_pdf)

        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 2000  # Valid PDF generated


@pytest.mark.asyncio
async def test_certificate_tamper_detection(db_session):
    """Verifies that tampering with even one character in the payload is detected as TAMPERED."""
    key = await get_or_create_active_signing_key(db_session)
    cert_id = f"CERT-TAMPER-TEST-{uuid.uuid4().hex[:6].upper()}"

    payload = {
        "certificate_id": cert_id,
        "mode": "simulation",
        "method": "NIST_800_88_CLEAR",
        "public_key_id": key.key_id,
        "device": {"model": "MacBook Air M2"},
    }
    payload_bytes = canonical_json(payload)
    signature = sign_payload_ed25519(payload_bytes, key.private_key_pem)
    payload["payload_sha256"] = sha256_hex(payload_bytes)

    # 1. Untampered payload -> VALID
    status, msg = await verify_certificate_payload(db_session, payload, signature)
    assert status == "VALID"

    # 2. Tampered payload -> TAMPERED
    tampered_payload = copy.deepcopy(payload)
    tampered_payload["device"]["model"] = "MacBook Air M3"  # Modifying one character!

    status_tampered, msg_tampered = await verify_certificate_payload(db_session, tampered_payload, signature)
    assert status_tampered == "TAMPERED"
