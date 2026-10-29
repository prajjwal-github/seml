# Project Task List - Secure Data Wiping Platform

- [x] **Phase 1: Project Scaffolding & Safety Governance**
  - [x] 1.1 Create directory structure (`backend`, `agent`, `frontend`, `docs`, `e2e`)
  - [x] 1.2 Write `docs/FORBIDDEN_LIST.md` documenting strictly forbidden commands
  - [x] 1.3 Write `backend/tests/test_no_destructive_commands.py` AST/string scanner test
  - [x] 1.4 Write initial `docs/DECISIONS.md`
  - [x] 1.5 Create dedicated local PostgreSQL cluster on port 5434 & configure `docker-compose.yml`, `Makefile`, `.env.example`
  - [x] 1.6 Set up backend environment & virtual environment

- [x] **Phase 2: Database Models, Migrations, Triggers & Hash-Chained Audit**
  - [x] 2.1 Define SQLAlchemy 2.0 async models for all tables (UUID PKs, JSONB fields)
  - [x] 2.2 Write Alembic migrations including PL/pgSQL triggers (`trg_audit_logs_immutable`, `trg_wipe_jobs_require_approval`, `trg_wipe_requests_state_transition`, `chk_no_self_approval`)
  - [x] 2.3 Implement cryptographic hash chaining on `audit_logs`
  - [x] 2.4 Verify database triggers with automated tests

- [x] **Phase 3: Core Backend Services & Simulation Engine**
  - [x] 3.1 Implement `WIPE_MODE=simulation` hard check in application lifecycle
  - [x] 3.2 Implement `WipeAdapter` ABC and `SimulatedWipeAdapter`
  - [x] 3.3 Implement NIST SP 800-88 Rev. 1 `WipePlanner` (Clear vs Purge, hidden areas, verification)
  - [x] 3.4 Implement `RequestStateMachine` (enforcing all legal & illegal state transitions)
  - [x] 3.5 Implement `ApprovalService` (fingerprints, single-use tokens, dual approvers for high-risk)
  - [x] 3.6 Implement Asyncio Wipe Worker & WebSocket event dispatcher
  - [x] 3.7 Implement Ed25519 Certificate Generator & ReportLab PDF with QR & watermark
  - [x] 3.8 Implement Public Verification endpoints & key rotation

- [x] **Phase 4: API Layer & Contract Synchronization**
  - [x] 4.1 Implement Auth (Argon2id, JWT access + rotating refresh, RBAC)
  - [x] 4.2 Implement Device Inventory endpoints (CRUD, stats, CSV import)
  - [x] 4.3 Implement Wipe Request & Approval endpoints (inbox, approve, reject, cancel)
  - [x] 4.4 Implement Job execution endpoints (start, progress, events, cancel)
  - [x] 4.5 Implement Certificate endpoints (list, get, PDF download, revoke)
  - [x] 4.6 Implement Audit & Reporting endpoints (chain verify, CSV export, analytics)
  - [x] 4.7 Implement WebSocket endpoint `/ws`
  - [x] 4.8 Export schema to `docs/openapi.json`

- [x] **Phase 5: Read-Only Device Detection Agent**
  - [x] 5.1 Implement cross-platform detection engine (Windows WMI, Linux sysfs, macOS sysctl, Android ADB)
  - [x] 5.2 Implement SMBIOS chassis mapping & confidence scoring
  - [x] 5.3 Implement storage inventory & encryption check
  - [x] 5.4 Implement CLI commands (`detect`, `register`, `run`) & agent transport
  - [x] 5.5 Write unit tests with recorded fixtures for all operating systems

- [x] **Phase 6: Seed Data & Browser Detection**
  - [x] 6.1 Create database seed script with 16 realistic devices across 14 categories
  - [x] 6.2 Seed 4 standard user accounts (Operator, Approver, Admin, Auditor)
  - [x] 6.3 Browser-side `navigator.userAgentData` device detection utility

- [x] **Phase 7: Frontend Web Application**
  - [x] 7.1 Initialize Vite React 18 TypeScript application with Tailwind and Lucide
  - [x] 7.2 Implement Design System, Themes (dark/light), and permanent SIMULATION banner
  - [x] 7.3 Implement API client and Zustand auth store with JWT auto-refresh
  - [x] 7.4 Build Login page with role-switch shortcuts
  - [x] 7.5 Build Dashboard with KPIs, Recharts graphs, and live activity ticker
  - [x] 7.6 Build Devices list (table & grid) and Add Device modal (Browser detect, manual, CSV)
  - [x] 7.7 Build Device Detail page (specs, volumes, history, request button)
  - [x] 7.8 Build 4-Step Wipe Request Wizard
  - [x] 7.9 Build Approvals Inbox with risk scores & dual-approver tracker
  - [x] 7.10 Build Live Jobs screen with progress bar, pass counter, and WebSocket console
  - [x] 7.11 Build Certificates page (PDF viewer, JSON download, revoke action)
  - [x] 7.12 Build Public Verification page (`/verify` drag & drop)
  - [x] 7.13 Build Audit Log with chain verification & CSV export
  - [x] 7.14 Build Admin settings page

- [x] **Phase 8: Comprehensive Verification & Walkthrough**
  - [x] 8.1 Run safety scanner `test_no_destructive_commands.py` (Passed)
  - [x] 8.2 Run all backend unit & integration tests (23/23 Passed)
  - [x] 8.3 Run Playwright E2E full flow in browser subagent & capture screenshots (15/15 Captured)
  - [x] 8.4 Write comprehensive `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/SECURITY.md`, `docs/DEMO_SCRIPT.md`
  - [x] 8.5 Publish final Walkthrough artifact
