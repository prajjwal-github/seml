# SecureWipe REST & WebSocket API Specification

The SecureWipe backend exposes a fully typed REST API under `/api/v1` and a real-time WebSocket telemetry gateway under `/ws`.

The complete machine-readable OpenAPI 3.1 specification is maintained at `/docs/openapi.json`. Interactive documentation is available via Swagger UI at `/docs` and ReDoc at `/redoc`.

---

## 1. Authentication & Security Headers

### 1.1 Authentication Schemes
- **User JWT Bearer**: Standard header `Authorization: Bearer <jwt_access_token>`.
  - Access Token Expiration: **15 minutes**.
  - Refresh Token Expiration: **7 days** (rotating with revocation).
- **Agent API Key**: Header `X-Agent-Key: <secret_key>`. Stored in the database as a SHA-256 hash.

### 1.2 User Roles & Access Matrix

| Role | Description | Permissions |
| :--- | :--- | :--- |
| **`OPERATOR`** | IT Asset Technician | Inventory access, submit wipe requests, start approved wipe jobs. Cannot approve requests. |
| **`APPROVER`** | Security Officer / Team Lead | Approvals inbox review, approve/reject wipe requests, inspect verification telemetry. |
| **`ADMIN`** | Platform Administrator | Full platform permissions, user CRUD, revoke certificates, emergency cancellations. |
| **`AUDITOR`** | Compliance Inspector | Read-only access across all records, public key discovery, audit chain verification. |

### 1.3 Error Response Schema
All HTTP errors follow the structured standard:
```json
{
  "code": 403,
  "message": "Four-eyes rule violation: Requester cannot approve their own wipe request.",
  "details": null
}
```

---

## 2. API Endpoints Summary

### 2.1 Authentication & Profile
- `POST /api/v1/auth/login`: Authenticate with email/password; returns user, access token, and refresh token.
- `POST /api/v1/auth/refresh`: Submit refresh token; returns rotated access and refresh tokens.
- `GET /api/v1/auth/me`: Returns profile and active role of authenticated user.
- `POST /api/v1/auth/logout`: Revokes active refresh token.

### 2.2 Users & Administration (Admin Only)
- `GET /api/v1/users`: List all platform users and roles.
- `POST /api/v1/users`: Create a new user account with designated role.

### 2.3 Device Inventory & Telemetry
- `GET /api/v1/devices`: List all registered IT assets with category, OS, status, and search filters.
- `GET /api/v1/devices/{device_id}`: Retrieve full hardware specifications, partition table, and volumes.
- `POST /api/v1/devices`: Manually register a new device to inventory.
- `POST /api/v1/devices/import-csv`: Bulk import multiple IT devices via CSV manifest.

### 2.4 Device Detection Agent
- `POST /api/v1/agent/register`: Register a new agent instance and receive an `X-Agent-Key`.
- `POST /api/v1/agent/report`: Ingest read-only hardware telemetry and storage volume mapping.
- `POST /api/v1/agent/heartbeat`: Periodic heartbeat maintaining agent `ONLINE` / `STALE` / `OFFLINE` status.

### 2.5 Wipe Requests
- `POST /api/v1/wipe-requests`: Submit a wipe request in `PENDING_APPROVAL` status (enforces typed serial confirmation).
- `GET /api/v1/wipe-requests`: List all wipe requests with status and device filters.
- `GET /api/v1/wipe-requests/{request_id}`: Get detailed request status and required approver count.
- `POST /api/v1/wipe-requests/{request_id}/cancel`: Cancel a pending request before job initialization.

### 2.6 Dual-Custody Approvals
- `GET /api/v1/approvals/inbox`: View all requests awaiting authorization (flags four-eyes self-approval conflicts).
- `POST /api/v1/approvals/{request_id}/approve`: Record approval, generate request fingerprint, and issue single-use authorization token.
- `POST /api/v1/approvals/{request_id}/reject`: Reject request (mandatory written rationale).

### 2.7 Wipe Jobs & Execution
- `POST /api/v1/jobs/start`: Start approved wipe job using single-use authorization token. Enforces token validity, unexpired status, and fingerprint match.
- `GET /api/v1/jobs`: List wipe jobs with status and progress.
- `GET /api/v1/jobs/{job_id}`: Get single job state, current pass, and verification results.
- `GET /api/v1/jobs/{job_id}/events`: Retrieve chronological execution event stream.
- `POST /api/v1/jobs/{job_id}/cancel`: Cancel a running or queued job.

### 2.8 Certificates & Verification
- `GET /api/v1/certificates`: List generated certificates of sanitization.
- `GET /api/v1/certificates/{cert_id}`: Inspect canonical JSON payload, signature, and public key ID.
- `GET /api/v1/certificates/{cert_id}/pdf`: Download signed ReportLab PDF certificate with QR code and simulation watermark.
- `POST /api/v1/certificates/{cert_id}/revoke`: Admin-only certificate revocation with mandatory reason.
- `GET /api/v1/verify/{cert_id}`: Public unauthenticated certificate lookup and cryptographic verification.
- `POST /api/v1/verify`: Public unauthenticated cryptographic signature verification for uploaded JSON/payload.
- `GET /.well-known/wipe-keys`: Public key discovery endpoint (RFC 8032 Ed25519 public keys).

### 2.9 Hash-Chained Audit Trail
- `GET /api/v1/audit`: Filterable append-only audit trail logs.
- `GET /api/v1/audit/verify-chain`: Verify sequential cryptographic hash chain integrity from genesis to head.
- `GET /api/v1/audit/export.csv`: Download full audit trail as an authenticated CSV manifest.

### 2.10 Executive Reporting
- `GET /api/v1/reports/summary`: Aggregate analytics: total devices, completed wipes, category distribution, method breakdowns, and average approval turnaround time.

---

## 3. Real-Time WebSocket Telemetry (`/ws`)

### 3.1 Connection Handshake
Clients connect to `/ws?token=<jwt_access_token>&channel=global`.

### 3.2 Broadcast Event Payloads
- **Job Progress (`job.progress`)**:
  ```json
  {
    "event": "job.progress",
    "job_id": "e105780e-6833-4028-ae54-2ae21c6086e8",
    "progress": 37.5,
    "current_pass": 1,
    "total_passes": 3,
    "status": "RUNNING",
    "message": "Pass 1/3: 37.5% complete (Logical 0x00 pattern)",
    "details": { "volume_name": "Micron NVMe 1TB", "sectors_processed": 782000 }
  }
  ```
- **Job State Transition (`job.status`)**:
  ```json
  {
    "event": "job.status",
    "job_id": "e105780e-6833-4028-ae54-2ae21c6086e8",
    "status": "COMPLETED",
    "message": "Cryptographic verification passed. Certificate issued."
  }
  ```
- **Dual-Custody Notification (`notification`)**:
  ```json
  {
    "event": "notification",
    "title": "New High-Risk Wipe Request",
    "message": "Operator submitted purge request for ProLiant DL380. 2 approvers required."
  }
  ```
