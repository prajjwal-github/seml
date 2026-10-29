"""End-to-end API integration tests covering positive flows and all mandatory negative paths."""

import copy
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client):
    """Verifies that health check reports healthy in simulation mode."""
    res = await client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["mode"] == "simulation"


@pytest.mark.asyncio
async def test_full_lifecycle_and_negative_paths(client):
    """Verifies the complete dual-custody lifecycle and asserts all mandatory negative paths."""
    # 1. Login as Operator
    op_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "operator@securewipe.local", "password": "Operator123!"},
    )
    assert op_login.status_code == 200
    op_token = op_login.json()["access_token"]
    op_headers = {"Authorization": f"Bearer {op_token}"}

    # 2. Login as Approver
    appr_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "approver@securewipe.local", "password": "Approver123!"},
    )
    assert appr_login.status_code == 200
    appr_token = appr_login.json()["access_token"]
    appr_headers = {"Authorization": f"Bearer {appr_token}"}

    # 3. List devices
    dev_res = await client.get("/api/v1/devices", headers=op_headers)
    assert dev_res.status_code == 200
    devices = dev_res.json()
    assert len(devices) >= 16

    target_device = None
    volume_ids = []
    for d in devices:
        detail_res = await client.get(f"/api/v1/devices/{d['id']}", headers=op_headers)
        vols = detail_res.json().get("volumes", [])
        if vols:
            target_device = d
            volume_ids = [v["id"] for v in vols]
            break

    assert target_device is not None
    device_id = target_device["id"]
    serial_number = target_device["serial_number"]

    # 4. Operator submits wipe request
    req_res = await client.post(
        "/api/v1/wipe-requests",
        headers=op_headers,
        json={
            "device_id": device_id,
            "volume_ids": volume_ids,
            "method": "NIST_800_88_CLEAR",
            "reason": "Test Lifecycle Request",
            "confirm_serial": serial_number,
        },
    )
    assert req_res.status_code == 201
    wipe_req = req_res.json()
    request_id = wipe_req["id"]
    assert wipe_req["status"] == "PENDING_APPROVAL"

    # NEGATIVE PATH 1: Start job without approval -> 409 Conflict
    fake_token = "a" * 64
    unapproved_job_res = await client.post(
        "/api/v1/jobs/start",
        headers=op_headers,
        json={"request_id": request_id, "token": fake_token},
    )
    assert unapproved_job_res.status_code == 409

    # NEGATIVE PATH 2a: Operator attempts approval -> 403 Forbidden (RBAC)
    self_appr_res = await client.post(
        f"/api/v1/approvals/{request_id}/approve",
        headers=op_headers,
        json={"decision": "APPROVED", "comment": "Operator trying to approve"},
    )
    assert self_appr_res.status_code == 403

    # NEGATIVE PATH 2b: Admin creates request and attempts self-approval -> 403 (Four-Eyes Violation)
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@securewipe.local", "password": "Admin123!"},
    )
    assert admin_login.status_code == 200
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    admin_req = await client.post(
        "/api/v1/wipe-requests",
        headers=admin_headers,
        json={
            "device_id": device_id,
            "volume_ids": volume_ids,
            "method": "NIST_800_88_CLEAR",
            "reason": "Admin test request",
            "confirm_serial": serial_number,
        },
    )
    assert admin_req.status_code == 201
    admin_req_id = admin_req.json()["id"]

    admin_self_appr = await client.post(
        f"/api/v1/approvals/{admin_req_id}/approve",
        headers=admin_headers,
        json={"decision": "APPROVED", "comment": "Admin trying self-approval"},
    )
    assert admin_self_appr.status_code == 403
    assert "Four-eyes rule violation" in admin_self_appr.json()["message"]

    # 5. Distinct Approver views Approvals Inbox
    inbox_res = await client.get("/api/v1/approvals/inbox", headers=appr_headers)
    assert inbox_res.status_code == 200
    inbox_items = inbox_res.json()
    assert any(item["id"] == request_id for item in inbox_items)

    # 6. Approver approves the request -> returns single-use token
    appr_res = await client.post(
        f"/api/v1/approvals/{request_id}/approve",
        headers=appr_headers,
        json={"decision": "APPROVED", "comment": "Legitimate decommissioning approval"},
    )
    assert appr_res.status_code == 200
    appr_data = appr_res.json()
    single_use_token = appr_data["raw_token"]
    assert single_use_token is not None

    # NEGATIVE PATH 3: Approving already approved by same approver -> 409 Conflict
    re_appr_res = await client.post(
        f"/api/v1/approvals/{request_id}/approve",
        headers=appr_headers,
        json={"decision": "APPROVED", "comment": "Duplicate approval attempt"},
    )
    assert re_appr_res.status_code == 409

    # 6b. Second distinct approver (Admin) approves high-risk request to satisfy 2-approver threshold
    admin_appr_res = await client.post(
        f"/api/v1/approvals/{request_id}/approve",
        headers=admin_headers,
        json={"decision": "APPROVED", "comment": "Second distinct approver for high risk"},
    )
    assert admin_appr_res.status_code == 200
    if admin_appr_res.json().get("raw_token"):
        single_use_token = admin_appr_res.json()["raw_token"]

    # 7. Operator starts the wipe job using the single-use token
    start_job_res = await client.post(
        "/api/v1/jobs/start",
        headers=op_headers,
        json={"request_id": request_id, "token": single_use_token},
    )
    assert start_job_res.status_code == 201
    job_data = start_job_res.json()
    job_id = job_data["id"]
    assert job_data["status"] == "QUEUED"

    # NEGATIVE PATH 4: Reusing an already used token -> 409 Conflict
    reuse_token_res = await client.post(
        "/api/v1/jobs/start",
        headers=op_headers,
        json={"request_id": request_id, "token": single_use_token},
    )
    assert reuse_token_res.status_code == 409

    # 8. Verify audit log hash chain integrity
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@securewipe.local", "password": "Admin123!"},
    )
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    chain_res = await client.get("/api/v1/audit/verify-chain", headers=admin_headers)
    assert chain_res.status_code == 200
    chain_data = chain_res.json()
    assert chain_data["is_valid"] is True
    assert chain_data["total_records"] > 0

    # 9. Verify /.well-known/wipe-keys
    keys_res = await client.get("/.well-known/wipe-keys")
    assert keys_res.status_code == 200
    keys_data = keys_res.json()
    assert len(keys_data["keys"]) >= 1

    # 10. List certificates and test public verification
    certs_res = await client.get("/api/v1/certificates", headers=op_headers)
    assert certs_res.status_code == 200
    certs = certs_res.json()
    assert len(certs) >= 1

    sample_cert = certs[0]
    sample_cert_id = sample_cert["certificate_id"]

    # Public verify by ID (no auth)
    pub_verif_res = await client.get(f"/verify/{sample_cert_id}")
    assert pub_verif_res.status_code == 200
    pub_data = pub_verif_res.json()
    assert pub_data["status"] == "VALID"

    # Tampered public verify (modify one byte of payload)
    tampered_payload = copy.deepcopy(sample_cert["payload"])
    tampered_payload["device"]["model"] = "TAMPERED_HARDWARE_MODEL"

    tamper_res = await client.post(
        "/verify",
        json={
            "payload": tampered_payload,
            "signature": sample_cert["signature"],
            "public_key_id": sample_cert["public_key_id"],
        },
    )
    assert tamper_res.status_code == 200
    assert tamper_res.json()["status"] == "TAMPERED"
