# Security Architecture & STRIDE Threat Model

SecureWipe is designed with a defense-in-depth security posture suitable for enterprise asset disposal and regulatory compliance under NIST SP 800-88 Rev. 1.

---

## 1. STRIDE Threat Model

| Threat Category | Potential Attack Vector | Platform Mitigations & Controls |
| :--- | :--- | :--- |
| **Spoofing** | Adversary attempts to impersonate an authorized approver or rogue agent. | - Password hashing with Argon2id ($m=65536, t=3, p=4$).<br/>- Short-lived JWT access tokens (15 min) + rotating refresh tokens.<br/>- Agent communication authenticated via high-entropy `X-Agent-Key` stored as SHA-256 hashes.<br/>- Digital certificates signed with Ed25519 private keys stored securely and published via `/.well-known/wipe-keys`. |
| **Tampering** | Rogue actor alters an approved wipe request, edits audit logs, or forges a certificate. | - **Request Fingerprint**: Any change to volume selection, method, or serial number invalidates $\text{SHA-256}(\text{device} + \text{volumes} + \text{method} + \text{serial})$.<br/>- **Database Trigger**: `trg_audit_logs_immutable` unconditionally aborts any `UPDATE` or `DELETE` statement on `audit_logs`.<br/>- **Hash-Chained Audit**: Any modification breaks the sequential SHA-256 chain verified by `GET /api/v1/audit/verify-chain`.<br/>- **RFC 8785 Canonicalization**: Certificates are canonicalized before signing; tampering with 1 byte invalidates the Ed25519 signature. |
| **Repudiation** | Operator or approver denies authorizing or executing a sanitization operation. | - Every request, approval, rejection, pass progression, and certificate generation writes an immutable audit record.<br/>- Every record captures actor ID, IP address, timestamp, and entity metadata.<br/>- Certificates embed the full identity, email, and cryptographic signature of approving officers. |
| **Information Disclosure** | Unauthorized party intercepts customer data from storage media or certificates. | - **Strict Simulation**: Under `WIPE_MODE=simulation`, the engine never touches real storage media or user data.<br/>- **Device Serials Hashed**: Public certificates store `device_serial_hash = SHA-256(serial)` to protect enterprise asset tracking information from public disclosure.<br/>- Strict RBAC ensures non-administrative users cannot view other organizations' devices. |
| **Denial of Service** | Flooding approval endpoints or brute-forcing tokens. | - Rate limiting on auth endpoints (`/auth/login`, `/auth/refresh`) and public verifiers.<br/>- Approvals require human justification and enforce four-eyes checks.<br/>- Single-use authorization tokens are 256-bit cryptographically secure random values ($2^{256}$ search space). |
| **Elevation of Privilege** | Operator attempts to approve their own request or start a job without approval. | - **Four-Eyes Enforcement**: Database CHECK constraint `chk_no_self_approval` and service layer block self-approval with 403.<br/>- **Job Gate Trigger**: Database trigger `trg_wipe_jobs_require_approval` refuses SQL inserts into `wipe_jobs` unless an unexpired, matching approval in status `APPROVED` exists.<br/>- **Single-Use Token**: Token hash marked `used_at` upon first use; token replay returns 409 Conflict. |

---

## 2. Cryptographic Architecture

### 2.1 Password Hashing & Secret Storage
- **Algorithm**: Argon2id via `pwdlib` / `passlib`.
- **Parameters**: 64MB memory cost ($m=65536$), 3 time iterations ($t=3$), 4 parallelism lanes ($p=4$).
- **API Keys**: Agent authentication keys are issued once in raw format (`wipe_ag_...`); only their SHA-256 digest is persisted in PostgreSQL.

### 2.2 Ed25519 Certificate Signatures
- **Algorithm**: Ed25519 (PureEdDSA over Curve25519) conforming to RFC 8032.
- **Canonicalization**: All certificate payloads are serialized into JSON canonical form per RFC 8785 before hashing:
  $$\text{Digest} = \text{SHA-256}(\text{JCS}(\text{Payload}))$$
  $$\text{Signature} = \text{Sign}_{\text{Ed25519}}(\text{Digest})$$
- **Verification**: Can be performed completely offline by any third-party auditor using standard Ed25519 tools and the public key exported from `/.well-known/wipe-keys`.

### 2.3 Immutable Audit Hash Chain
The `audit_logs` table forms a cryptographic Merkle-like linear chain:
- Row $i=1$ (Genesis):
  $$\text{prev\_hash}_1 = \text{"0"}\times 64$$
  $$\text{hash}_1 = \text{SHA-256}(\text{prev\_hash}_1 \parallel \text{seq}_1 \parallel \text{ts}_1 \parallel \text{actor}_1 \parallel \text{action}_1 \parallel \text{entity}_1 \parallel \text{details}_1)$$
- Row $i=n$:
  $$\text{prev\_hash}_n = \text{hash}_{n-1}$$
  $$\text{hash}_n = \text{SHA-256}(\text{prev\_hash}_n \parallel \text{seq}_n \parallel \text{ts}_n \parallel \text{actor}_n \parallel \text{action}_n \parallel \text{entity}_n \parallel \text{details}_n)$$

If an attacker with database root access modifies any column in row $k$, the hash chain $\text{hash}_k \ne \text{prev\_hash}_{k+1}$ becomes invalid. The integrity verification endpoint `GET /api/v1/audit/verify-chain` detects the tamper location immediately.

---

## 3. Strict Simulation Governance

To prevent accidental data loss across development and evaluation environments, the platform implements strict safety mechanisms:
1. **Application Refusal on Non-Simulation**: `WIPE_MODE=simulation` is verified during backend startup lifespan. If set to any other value, the application logs a fatal error and terminates with exit code 1.
2. **Abstract Adapter Isolation**: The wipe execution engine uses `WipeAdapter` with only one concrete implementation: `SimulatedWipeAdapter`.
3. **Automated Destructive Command Scanner**: `backend/tests/test_no_destructive_commands.py` runs during test suites and CI, scanning all source code files, scripts, and documentation for destructive command tokens (defined in `docs/FORBIDDEN_LIST.md`). Any occurrence fails the test suite.
4. **Permanent UI Banner**: Every page renders an immutable warning: `"SIMULATION MODE - no data is erased"`.
