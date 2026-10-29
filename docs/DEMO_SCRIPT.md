# 5-Minute Evaluator Demo Script

Follow this step-by-step walkthrough to experience the complete SecureWipe platform lifecycle, including dual-custody enforcement, live streaming sanitization telemetry, cryptographic certificate signing, tamper detection, and hash-chain audit verification.

---

## Prerequisites & Default Personas

Ensure all services are running:
- **Backend**: `http://127.0.0.1:8001`
- **Frontend**: `http://127.0.0.1:5173`

The platform includes four pre-seeded demo personas with quick-switch controls in the top navigation bar:

| Persona | Email | Password | Role | Responsibilities |
| :--- | :--- | :--- | :--- | :--- |
| **Alex Vance** | `operator@securewipe.local` | `Operator123!` | `OPERATOR` | Asset inspection, wipe requests, starting approved jobs |
| **Sarah Connor** | `approver@securewipe.local` | `Approver123!` | `APPROVER` | Dual-custody review, four-eyes gate, single-use token issuance |
| **Marcus Wright** | `admin@securewipe.local` | `Admin123!` | `ADMIN` | Second approver for high risk, user CRUD, certificate revocation |
| **Elena Rostova** | `auditor@securewipe.local` | `Auditor123!` | `AUDITOR` | Compliance audit, public verifier inspection, hash chain checks |

---

## Step 1: Login & Dashboard Overview (0:00 - 0:45)
1. Navigate to `http://127.0.0.1:5173/login`.
2. Observe the permanent top warning: **`SIMULATION MODE - NO DATA IS ERASED`**.
3. Click the **OPERATOR** quick-switch button. You are logged in as `Alex Vance`.
4. On the **Security Operations Dashboard**, view:
   - Real-time KPI summary cards (Total Assets, Pending Approvals, Active Wipes, Issued Certificates).
   - Interactive Recharts fleet distribution and weekly sanitization trends.
   - Real-time audit activity stream.

---

## Step 2: Device Inventory & Hardware Telemetry (0:45 - 1:30)
1. Click **Devices** in the sidebar.
2. Review the 16 seeded assets across all 14 categories (Laptops, Desktops, Servers, Phones, Tablets, External Drives, SBCs).
3. Click **Add Device** to see:
   - **Browser Auto-Detect**: High-entropy browser user agent client hints with device model suggestion.
   - **Manual Registration**: Full hardware specification input.
   - **CSV Import**: Bulk enterprise import.
4. Close the modal and click on **Dell OptiPlex 7090 Micro** (or any available asset).
5. Review the hardware telemetry card: CPU architecture, BIOS/UEFI boot mode, storage volume tree, bus interfaces, partition tables, and encryption status (BitLocker / LUKS).

---

## Step 3: Four-Step Wipe Request Wizard (1:30 - 2:30)
1. Click the **Clear / Wipe Device** button to open the modal wizard.
2. **Step 1 (Volumes)**: Select target storage media (NVMe, SATA, or partition). Click **Next Step**.
3. **Step 2 (Sanitization Method)**: Select **NIST 800-88 Clear** (logical overwrite) or **NIST 800-88 Purge** (cryptographic erase). Click **Next Step**.
4. **Step 3 (Justification & Risk Assessment)**: Provide a business justification (e.g. `Decommissioning manifest #4891`). Notice the calculated Risk Level badge. Click **Next Step**.
5. **Step 4 (Serial Confirmation)**: To prevent accidental sanitization of unintended hardware, manually type the exact target serial number displayed on screen.
6. Click **Submit Wipe Request**.
7. Observe that **NO job is started**. The request enters `PENDING_APPROVAL` status with a dual-custody notification.

---

## Step 4: Dual-Custody Approval Gate & Four-Eyes Enforcement (2:30 - 3:30)
1. Navigate to **Approvals** in the sidebar.
2. Notice the warning on your submitted request:
   $$\text{"Four-eyes rule: You submitted this request and cannot approve it."}$$
   The **Approve Request** button is strictly disabled for your operator account.
3. In the top navigation bar, click the persona dropdown and switch to **APPROVER** (`Sarah Connor`).
4. In the Approvals Inbox, review the request details, justification, and calculated risk level.
5. Click **Approve Request**. Enter a review comment and click **Confirm Approval**.
6. Notice the issued **single-use authorization token** displayed on screen and automatically staged for operator initialization.

---

## Step 5: Live Sanitization Operations & Streaming Telemetry (3:30 - 4:15)
1. Switch back to the **OPERATOR** persona (`Alex Vance`).
2. Navigate to **Live Operations** (`/jobs`).
3. Under *Approved Requests Awaiting Operator Start*, locate the approved device.
4. Click **Start Wipe Job**.
5. Watch the real-time telemetry stream over FastAPI WebSocket `/ws`:
   - Pass progression counter (`Pass 1 of 1` or `Pass 1 of 3`).
   - Live percentage progress bar animating to 100%.
   - Real-time terminal log displaying sector passes, HPA/DCO hidden-area unmasking, and readback verification.
   - State transition: `QUEUED` $\to$ `RUNNING` $\to$ `VERIFYING` $\to$ `COMPLETED`.

---

## Step 6: Certificate of Sanitization & Cryptographic Tamper Detection (4:15 - 5:00)
1. Navigate to **Certificates** in the sidebar.
2. Locate the generated certificate for the completed job.
3. Click **PDF** to download the official ReportLab certificate featuring:
   - Sanitized asset serial hash, method, operator, and approver signatures.
   - Embedded QR code linking to `/verify/{id}`.
   - Diagonal `SIMULATION CERTIFICATE` watermark.
4. Click **Inspect** to review the canonical RFC 8785 JSON payload and Base64-encoded Ed25519 signature.
5. Click **Open Public Verifier** in the header (or navigate to `http://127.0.0.1:5173/verify`).
6. Notice this page is fully accessible **without authentication**.
7. Enter the certificate ID and click **Verify Certificate**. The badge displays **VALID** with active signing key confirmation.
8. Click **Test Tamper Detection**. The system simulates an attacker modifying a single byte in the payload. The status immediately turns to **TAMPERED**, demonstrating mathematical non-repudiation.
9. Navigate to **Audit Log** (`/audit`) and click **Verify Chain Integrity**. Confirm that the linear SHA-256 hash chain reports **INTACT & VALID**.
