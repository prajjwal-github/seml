# Architecture & Engineering Decisions Log (DECISIONS.md)

This log documents all non-trivial technical, architectural, security, and design decisions made throughout the development of the Secure Data Wiping and Certified IT Asset Recycling Platform.

---

## Decision 001: Strict Simulation Enforcement & Destructive Command Shield
- **Date**: 2026-10-19
- **Context**: The platform is built for certified IT asset wiping demonstrations, audit validation, and certification workflows. Any accidental invocation of destructive commands or block storage operations on development or test hardware is strictly prohibited.
- **Decision**:
  1. The platform will enforce `WIPE_MODE=simulation` as a non-negotiable configuration. The backend will refuse to start if set to any other value.
  2. The wiping execution engine will use an abstract `WipeAdapter` with only one implementation: `SimulatedWipeAdapter`.
  3. A dedicated safety scanner test (`backend/tests/test_no_destructive_commands.py`) will inspect all codebase files, scripts, and documentation (except `docs/FORBIDDEN_LIST.md`) for destructive command tokens enumerated in `docs/FORBIDDEN_LIST.md` and ensure no real block or filesystem operations exist.
  4. The frontend will render an immutable, prominent top banner: `"SIMULATION MODE - no data is erased"`.
  5. Every wipe job and certificate will carry `"mode": "simulation"` metadata.

---

## Decision 002: Dual-Deployment Database Strategy (Local PostgreSQL 18 + Docker Compose PostgreSQL 16)
- **Date**: 2026-10-19
- **Context**: The platform requires PostgreSQL triggers, PL/pgSQL functions, and CHECK constraints (precluding SQLite). While Docker Compose is provided for standard containerized deployments, local Windows development hosts may have Docker Desktop stopped while having PostgreSQL installed natively.
- **Decision**:
  1. Provide standard `docker-compose.yml` defining PostgreSQL 16 for Linux/CI/container environments.
  2. Support dedicated local PostgreSQL instance initialization (port 5434) using native `initdb` and `pg_ctl` to guarantee 100% test and runtime reliability on any host environment without depending on external daemon states.
  3. All SQL migrations, PL/pgSQL triggers, and constraints will remain identical across both environments.

---

## Decision 003: Three-Tier Approval Enforcing Four-Eyes Principle and Single-Use Tokens
- **Date**: 2026-10-19
- **Context**: Data wiping operations carry high irreversible operational risk. Rogue operators, compromised credentials, or unapproved actions must be impossible to execute.
- **Decision**:
  1. Enforcement at three distinct tiers:
     - **Database tier**: Check constraint `chk_no_self_approval` and trigger `trg_wipe_jobs_require_approval` forbidding job insertion without a valid, approved approval.
     - **Service tier**: `ApprovalService` verifies requester != approver, validates 24h expiration, verifies request fingerprint `SHA-256(device_id + sorted(volume_ids) + method + serial)`, and marks approval tokens as single-use.
     - **API tier**: Role-based access control (`require_roles([Role.APPROVER, Role.ADMIN])`).
  2. High-risk actions (operating system/boot volumes, batches > 5 devices, or Purge on production equipment) require two distinct approvers.
  3. Single-use token hash stored in the database; `used_at` timestamp stamped atomically when a job starts.

---

## Decision 004: Hash-Chained Append-Only Audit Log
- **Date**: 2026-10-19
- **Context**: Certified IT asset recycling requires non-repudiable audit logs that cannot be manipulated by operators or administrators.
- **Decision**:
  1. The `audit_logs` table features a PL/pgSQL trigger `trg_audit_logs_immutable` that unconditionally rejects `UPDATE` and `DELETE` queries.
  2. Each audit row stores `prev_hash` and `hash = SHA256(prev_hash + seq + ts + actor_id + action + entity_type + entity_id + details)`.
  3. An automated endpoint `GET /api/v1/audit/verify-chain` verifies cryptographically that the entire sequence remains unbroken from genesis to head.

---

## Decision 005: Ed25519 Cryptographic Certificates with ReportLab PDF and QR Codes
- **Date**: 2026-10-19
- **Context**: Certificates of sanitization must be tamper-evident, verifiable offline and online, and conformant to NIST SP 800-88 Rev. 1 reporting standards.
- **Decision**:
  1. Signing using high-speed, modern Ed25519 asymmetric cryptography.
  2. Certificate payload canonicalized via RFC 8785 (JSON Canonicalization Scheme) before SHA-256 hashing and signing.
  3. Public key published at standard `/.well-known/wipe-keys` with key rotation capabilities via `signing_keys` table.
  4. PDF generated with ReportLab containing embedded QR code pointing to `/verify/<cert_id>` and a clear `SIMULATION CERTIFICATE` diagonal watermark.
  5. Public verification endpoint supporting both JSON upload and PDF file upload.

---

## Decision 006: Read-Only Detection Architecture
- **Date**: 2026-10-19
- **Context**: Device inventory needs deep hardware categorization (chassis, volumes, bus, SMART, hidden areas) without risking state change.
- **Decision**:
  1. All OS query mechanisms (WMI on Windows, sysfs on Linux, system_profiler on macOS, ADB on Android) strictly invoke read-only queries and properties.
  2. Mapping chassis types from SMBIOS specifications (codes 8, 9, 10, 14 -> LAPTOP; 3, 4, 5, 6, 7 -> DESKTOP; 17, 23 -> SERVER; 30 -> TABLET; 13 -> ALL_IN_ONE).
  3. Android detection via read-only `adb devices -l`, `getprop`, and window manager metrics (`wm size`, `wm density`) to detect tablets (smallest width >= 600dp).
  4. Unit tests run completely offline using realistic recorded fixtures.
