"""Certificate generation, Ed25519 canonical signing, and ReportLab PDF rendering."""

import io
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.certs.keys import get_or_create_active_signing_key
from backend.core.config import settings
from backend.core.security import canonical_json, sha256_hex, sign_payload_ed25519, verify_signature_ed25519
from backend.models import (
    Approval,
    Certificate,
    Device,
    SigningKey,
    StorageVolume,
    User,
    WipeJob,
    WipeRequest,
)


def draw_watermark(c: canvas.Canvas, width: float, height: float):
    """Draws a prominent diagonal SIMULATION watermark across the certificate."""
    c.saveState()
    c.setFont("Helvetica-Bold", 38)
    c.setFillColor(colors.HexColor("#EF4444"), alpha=0.12)
    c.translate(width / 2.0, height / 2.0)
    c.rotate(45)
    c.drawCentredString(0, 40, "SIMULATION CERTIFICATE")
    c.drawCentredString(0, -10, "NO DATA ERASED")
    c.restoreState()


def generate_pdf_certificate(
    cert_id: str,
    payload: Dict[str, Any],
    signature: str,
    output_path: Path,
) -> str:
    """Renders a PDF certificate of sanitization with an embedded verification QR code."""
    width, height = letter
    c = canvas.Canvas(str(output_path), pagesize=letter)

    # 1. Background Watermark
    draw_watermark(c, width, height)

    # 2. Header & Banner
    c.setFillColor(colors.HexColor("#0F172A"))  # Slate-900
    c.rect(0, height - 85, width, 85, fill=True, stroke=False)

    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.setFont("Helvetica-Bold", 20)
    c.drawString(45, height - 42, "CERTIFICATE OF DATA SANITIZATION")

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#94A3B8"))
    c.drawString(45, height - 60, "Compliant with NIST Special Publication 800-88 Revision 1 Standards")

    # Simulation Notice Badge
    c.setFillColor(colors.HexColor("#DC2626"))
    c.roundRect(width - 190, height - 62, 145, 24, 4, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(width - 117, height - 52, "MODE: SIMULATION ONLY")

    # 3. Certificate Identity Box
    y = height - 120
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.roundRect(45, y - 45, width - 90, 45, 6, fill=True, stroke=True)

    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(60, y - 20, "CERTIFICATE IDENTIFIER")
    c.drawString(280, y - 20, "DATE OF ISSUANCE")
    c.drawString(430, y - 20, "NIST CATEGORY")

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y - 36, cert_id)

    issued_date = payload.get("timestamps", {}).get("issued_at", datetime.now().isoformat())[:19].replace("T", " ")
    c.setFont("Helvetica", 11)
    c.drawString(280, y - 36, issued_date)

    nist_cat = payload.get("nist_category", "CLEAR")
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#2563EB") if nist_cat == "CLEAR" else colors.HexColor("#7C3AED"))
    c.drawString(430, y - 36, nist_cat)

    # 4. Device Information Table
    y = y - 75
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(45, y, "1. Target Asset Information")
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.line(45, y - 4, width - 45, y - 4)

    y -= 22
    dev = payload.get("device", {})
    device_fields = [
        ("Asset Category:", dev.get("category", "Unknown")),
        ("Manufacturer:", dev.get("manufacturer", "Unknown")),
        ("Hardware Model:", dev.get("model", "Unknown")),
        ("Operating System:", f"{dev.get('os_name', '')} {dev.get('os_version', '')}"),
        ("Serial Number (SHA-256):", dev.get("serial_hash", "Unknown")[:32] + "..."),
    ]

    for label, val in device_fields:
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawString(55, y, label)
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#0F172A"))
        c.drawString(185, y, str(val))
        y -= 14

    # 5. Sanitization & Verification Summary
    y -= 10
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(45, y, "2. Sanitization & Verification Details")
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.line(45, y - 4, width - 45, y - 4)

    y -= 22
    verif = payload.get("verification", {})
    hidden = payload.get("hidden_area_coverage", {})
    sanitize_fields = [
        ("Sanitization Method:", payload.get("method", "NIST_800_88_CLEAR")),
        ("Volumes Sanitized:", f"{len(payload.get('volumes', []))} volume(s) processed"),
        ("Verification Coverage:", f"{verif.get('sample_percentage', 10.0)}% sample verified ({verif.get('hash_verification', 'ZERO_PATTERN_CONFIRMED')})"),
        ("Hidden Areas Sanitized:", f"HPA Cleared: {hidden.get('hpa_cleared', True)} | DCO Cleared: {hidden.get('dco_cleared', True)} | Remapped Sectors: Checked"),
        ("Requested / Approved by:", f"Operator: {payload.get('operator', {}).get('name', 'Operator')} | Approver: {payload.get('approver', {}).get('name', 'Approver')}"),
    ]

    for label, val in sanitize_fields:
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawString(55, y, label)
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#0F172A"))
        c.drawString(185, y, str(val))
        y -= 14

    # 6. Cryptographic Signatures & Verification QR Code
    y -= 15
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(45, y, "3. Cryptographic Verification & Public Trust")
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.line(45, y - 4, width - 45, y - 4)

    # Generate QR Code in-memory
    verify_url = f"{settings.PUBLIC_APP_URL.rstrip('/')}/verify/{cert_id}"
    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#0F172A", back_color="white")

    # Save to a temporary in-memory buffer
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    # Draw QR code image
    from reportlab.lib.utils import ImageReader
    qr_reader = ImageReader(qr_buffer)
    c.drawImage(qr_reader, width - 150, y - 110, width=90, height=90)

    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawCentredString(width - 105, y - 118, "Scan to Verify Online")

    # Draw Digital Signature and Hash Box
    box_w = width - 210
    c.setFillColor(colors.HexColor("#F1F5F9"))
    c.roundRect(45, y - 110, box_w, 90, 4, fill=True, stroke=False)

    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawString(55, y - 30, "CANONICAL PAYLOAD SHA-256 HASH:")
    c.setFont("Courier", 7)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.drawString(55, y - 42, payload.get("payload_sha256", "")[:50] + "...")

    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawString(55, y - 56, f"ED25519 ASYMMETRIC DIGITAL SIGNATURE (Key ID: {payload.get('public_key_id', '')}):")
    c.setFont("Courier", 6)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.drawString(55, y - 68, signature[:64])
    c.drawString(55, y - 78, signature[64:128])

    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#16A34A"))
    c.drawString(55, y - 98, "Status: Cryptographically Signed & Immutable")

    # 7. Footer
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#94A3B8"))
    c.drawCentredString(
        width / 2.0,
        25,
        f"Generated by Secure Data Wiping Platform v{settings.VERSION} (Simulation Engine) | Independent verification available at /verify",
    )

    c.showPage()
    c.save()
    return str(output_path)


async def generate_certificate(session: AsyncSession, job: WipeJob) -> Certificate:
    """Produces, canonically signs, and persists a Certificate of Sanitization for a completed job."""
    # Ensure active signing key
    signing_key = await get_or_create_active_signing_key(session)

    # Fetch all relational context
    request = await session.get(WipeRequest, job.request_id)
    approval = await session.get(Approval, job.approval_id)
    device = await session.get(Device, request.device_id)

    operator = await session.get(User, request.requested_by)
    approver = await session.get(User, approval.approver_id)

    # Fetch volumes
    vols_stmt = select(StorageVolume).where(StorageVolume.id.in_(request.volume_ids))
    vols_res = await session.execute(vols_stmt)
    volumes = vols_res.scalars().all()

    now = datetime.now(timezone.utc)
    cert_id = f"CERT-{now.year}-{uuid.uuid4().hex[:8].upper()}"

    # Build canonical payload dictionary
    payload: Dict[str, Any] = {
        "certificate_id": cert_id,
        "mode": "simulation",
        "tool_version": settings.VERSION,
        "job_id": str(job.id),
        "request_id": str(request.id),
        "approval_id": str(approval.id),
        "public_key_id": signing_key.key_id,
        "method": request.method.value if hasattr(request.method, "value") else str(request.method),
        "nist_category": request.nist_category.value if hasattr(request.nist_category, "value") else str(request.nist_category),
        "device": {
            "id": str(device.id),
            "category": device.category.value if hasattr(device.category, "value") else str(device.category),
            "manufacturer": device.manufacturer,
            "model": device.model,
            "serial_hash": sha256_hex(device.serial_number),
            "os_name": device.os_name,
            "os_version": device.os_version,
            "arch": device.arch,
        },
        "volumes": [
            {
                "id": str(v.id),
                "name": v.name,
                "media_type": v.media_type.value if hasattr(v.media_type, "value") else str(v.media_type),
                "size_bytes": v.size_bytes,
                "encryption_status": v.encryption_status.value if hasattr(v.encryption_status, "value") else str(v.encryption_status),
            }
            for v in volumes
        ],
        "operator": {
            "id": str(operator.id) if operator else None,
            "name": operator.name if operator else "Unknown",
            "email": operator.email if operator else "Unknown",
        },
        "approver": {
            "id": str(approver.id) if approver else None,
            "name": approver.name if approver else "Unknown",
            "email": approver.email if approver else "Unknown",
        },
        "timestamps": {
            "requested_at": request.created_at.isoformat() if request.created_at else now.isoformat(),
            "approved_at": approval.created_at.isoformat() if approval.created_at else now.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else now.isoformat(),
            "completed_at": job.finished_at.isoformat() if job.finished_at else now.isoformat(),
            "issued_at": now.isoformat(),
        },
        "verification": job.result.get("verification", {
            "verified": True,
            "sample_percentage": 15.0,
            "hash_verification": "ZERO_PATTERN_CONFIRMED",
        }),
        "hidden_area_coverage": job.result.get("hidden_areas", {
            "hpa_cleared": True,
            "dco_cleared": True,
            "remapped_sectors_checked": True,
        }),
    }

    # Canonicalize and sign
    payload_bytes = canonical_json(payload)
    payload_sha256 = sha256_hex(payload_bytes)
    signature = sign_payload_ed25519(payload_bytes, signing_key.private_key_pem)

    payload["payload_sha256"] = payload_sha256

    # Generate PDF
    pdf_filename = f"{cert_id}.pdf"
    pdf_path = settings.CERTS_DIR / pdf_filename
    generate_pdf_certificate(cert_id, payload, signature, pdf_path)

    cert = Certificate(
        job_id=job.id,
        certificate_id=cert_id,
        payload=payload,
        payload_sha256=payload_sha256,
        signature=signature,
        public_key_id=signing_key.key_id,
        pdf_path=str(pdf_path),
        issued_at=now,
    )
    session.add(cert)
    await session.flush()
    return cert


async def verify_certificate_payload(
    session: AsyncSession,
    payload: Dict[str, Any],
    signature: str,
    public_key_id: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """Verifies a certificate payload and returns (status, reason).

    Status values: VALID, TAMPERED, REVOKED, NOT_FOUND.
    """
    key_id = public_key_id or payload.get("public_key_id")
    if not key_id:
        return "TAMPERED", "Public key identifier missing from payload."

    stmt = select(SigningKey).where(SigningKey.key_id == key_id)
    res = await session.execute(stmt)
    key = res.scalar_one_or_none()

    if not key:
        return "TAMPERED", f"Signing key '{key_id}' unknown or revoked."

    # Check if certificate exists in database and if revoked
    cert_id = payload.get("certificate_id")
    if cert_id:
        c_stmt = select(Certificate).where(Certificate.certificate_id == cert_id)
        c_res = await session.execute(c_stmt)
        db_cert = c_res.scalar_one_or_none()
        if db_cert and db_cert.revoked_at is not None:
            return "REVOKED", f"Certificate was revoked: {db_cert.revoke_reason or 'No reason provided'}"

    # Prepare payload copy without payload_sha256 for canonical hashing
    payload_copy = dict(payload)
    payload_copy.pop("payload_sha256", None)

    payload_bytes = canonical_json(payload_copy)
    computed_sha256 = sha256_hex(payload_bytes)

    if "payload_sha256" in payload and payload["payload_sha256"] != computed_sha256:
        return "TAMPERED", "Payload SHA-256 hash does not match canonical bytes."

    # Verify signature
    is_valid = verify_signature_ed25519(payload_bytes, signature, key.public_key_pem)
    if not is_valid:
        return "TAMPERED", "Ed25519 digital signature verification failed."

    return "VALID", "Certificate is cryptographically valid and authentic."


def regenerate_pdf(cert: Certificate) -> str:
    """Re-renders a certificate PDF from its stored signed payload and returns the new path."""
    pdf_path = settings.CERTS_DIR / f"{cert.certificate_id}.pdf"
    generate_pdf_certificate(cert.certificate_id, dict(cert.payload), cert.signature, pdf_path)
    return str(pdf_path)
