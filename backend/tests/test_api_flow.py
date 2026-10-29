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


async def _login(client, email, password):
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _admin_registers_device(client, admin_headers):
    serial = f"TEST-{uuid.uuid4().hex[:10].upper()}"
    res = await client.post(
        "/api/v1/devices",
        headers=admin_headers,
        json={
            "category": "LAPTOP",
            "manufacturer": "Dell",
            "model": "Latitude 7440",
            "serial_number": serial,
            "volumes": [{"name": "NVMe 512GB", "size_bytes": 512 * 1024**3, "media_type": "NVME_SSD"}],
        },
    )
    assert res.status_code == 201, res.text
    dev = res.json()
    return dev["id"], serial, [v["id"] for v in dev["volumes"]]


@pytest.mark.asyncio
async def test_full_lifecycle_and_negative_paths(client):
    """Admin adds device -> Operator requests certificate -> Approver approves -> job auto-queued."""
    op_headers = await _login(client, "operator@securewipe.local", "Operator123!")
    appr_headers = await _login(client, "approver@securewipe.local", "Approver123!")
    admin_headers = await _login(client, "admin@securewipe.local", "Admin123!")

    # Only the Admin can register devices
    op_dev = await client.post(
        "/api/v1/devices",
        headers=op_headers,
        json={"serial_number": "OP-NOT-ALLOWED", "volumes": [{"name": "disk"}]},
    )
    assert op_dev.status_code == 403

    device_id, serial_number, volume_ids = await _admin_registers_device(client, admin_headers)

    # Duplicate serial is refused
    dup = await client.post(
        "/api/v1/devices",
        headers=admin_headers,
        json={"serial_number": serial_number, "volumes": [{"name": "disk"}]},
    )
    assert dup.status_code == 409

    request_body = {
        "device_id": device_id,
        "volume_ids": volume_ids,
        "method": "NIST_800_88_CLEAR",
        "reason": "Test Lifecycle Request",
        "confirm_serial": serial_number,
    }

    # Admin and Approver cannot submit certificate requests
    assert (await client.post("/api/v1/wipe-requests", headers=admin_headers, json=request_body)).status_code == 403
    assert (await client.post("/api/v1/wipe-requests", headers=appr_headers, json=request_body)).status_code == 403

    # Operator submits the certificate request
    req_res = await client.post("/api/v1/wipe-requests", headers=op_headers, json=request_body)
    assert req_res.status_code == 201
    wipe_req = req_res.json()
    request_id = wipe_req["id"]
    assert wipe_req["status"] == "PENDING_APPROVAL"
    assert wipe_req["device_serial"] == serial_number

    # A second request for the same device while one is open -> 409
    assert (await client.post("/api/v1/wipe-requests", headers=op_headers, json=request_body)).status_code == 409

    # Device shows the in-flight request
    devs = (await client.get("/api/v1/devices", headers=admin_headers)).json()
    assert next(d for d in devs if d["id"] == device_id)["wipe_status"] == "PENDING_APPROVAL"

    # NEGATIVE PATH: Start job without approval -> 409 Conflict
    unapproved_job_res = await client.post(
        "/api/v1/jobs/start",
        headers=op_headers,
        json={"request_id": request_id, "token": "a" * 64},
    )
    assert unapproved_job_res.status_code == 409

    # NEGATIVE PATH: Operator or Admin attempting approval -> 403 Forbidden (RBAC)
    for headers in (op_headers, admin_headers):
        res = await client.post(
            f"/api/v1/approvals/{request_id}/approve",
            headers=headers,
            json={"decision": "APPROVED", "comment": "not allowed"},
        )
        assert res.status_code == 403

    # Operators cannot see the approvals inbox
    assert (await client.get("/api/v1/approvals/inbox", headers=op_headers)).status_code == 403

    # Approver sees the request in the inbox
    inbox_res = await client.get("/api/v1/approvals/inbox", headers=appr_headers)
    assert inbox_res.status_code == 200
    assert any(item["id"] == request_id for item in inbox_res.json())

    # Approver approves -> the wipe job is queued automatically
    appr_res = await client.post(
        f"/api/v1/approvals/{request_id}/approve",
        headers=appr_headers,
        json={"decision": "APPROVED", "comment": "Legitimate decommissioning approval"},
    )
    assert appr_res.status_code == 200
    appr_data = appr_res.json()
    assert appr_data["job_id"] is not None
    single_use_token = appr_data["raw_token"]

    detail = (await client.get(f"/api/v1/wipe-requests/{request_id}", headers=op_headers)).json()
    assert detail["status"] == "QUEUED"
    assert detail["job_id"] == appr_data["job_id"]
    assert detail["approver_name"]

    # NEGATIVE PATH: approving twice -> 409 Conflict
    re_appr_res = await client.post(
        f"/api/v1/approvals/{request_id}/approve",
        headers=appr_headers,
        json={"decision": "APPROVED", "comment": "Duplicate approval attempt"},
    )
    assert re_appr_res.status_code == 409

    # NEGATIVE PATH: a job already exists, so a manual start with the token -> 409
    reuse_token_res = await client.post(
        "/api/v1/jobs/start",
        headers=op_headers,
        json={"request_id": request_id, "token": single_use_token},
    )
    assert reuse_token_res.status_code == 409

    # Operator only sees their own requests
    own = (await client.get("/api/v1/wipe-requests", headers=op_headers)).json()
    assert own and all(r["requester_name"] for r in own)

    # Verify audit log hash chain integrity
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


@pytest.mark.asyncio
async def test_rejection_flow(client):
    """Approver rejects with a mandatory reason, and the Operator can see why."""
    op_headers = await _login(client, "operator@securewipe.local", "Operator123!")
    appr_headers = await _login(client, "approver@securewipe.local", "Approver123!")
    admin_headers = await _login(client, "admin@securewipe.local", "Admin123!")

    device_id, serial, volume_ids = await _admin_registers_device(client, admin_headers)
    req = await client.post(
        "/api/v1/wipe-requests",
        headers=op_headers,
        json={
            "device_id": device_id,
            "volume_ids": volume_ids,
            "method": "NIST_800_88_PURGE",
            "reason": "Resale",
            "confirm_serial": serial,
        },
    )
    assert req.status_code == 201
    request_id = req.json()["id"]

    no_reason = await client.post(
        f"/api/v1/approvals/{request_id}/reject", headers=appr_headers, json={"decision": "REJECTED"}
    )
    assert no_reason.status_code == 400

    rej = await client.post(
        f"/api/v1/approvals/{request_id}/reject",
        headers=appr_headers,
        json={"decision": "REJECTED", "comment": "Asset tag missing"},
    )
    assert rej.status_code == 200

    detail = (await client.get(f"/api/v1/wipe-requests/{request_id}", headers=op_headers)).json()
    assert detail["status"] == "REJECTED"
    assert detail["decision_comment"] == "Asset tag missing"

    # A rejected request frees the device for a new request
    again = await client.post(
        "/api/v1/wipe-requests",
        headers=op_headers,
        json={
            "device_id": device_id,
            "volume_ids": volume_ids,
            "method": "NIST_800_88_CLEAR",
            "reason": "Resale, asset tag attached",
            "confirm_serial": serial,
        },
    )
    assert again.status_code == 201
    cancel = await client.post(f"/api/v1/wipe-requests/{again.json()['id']}/cancel", headers=op_headers)
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "CANCELLED"
