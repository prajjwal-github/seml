# Test Plan: Assignment 11 Python Unit Testing (JUnit Equivalents)

## 1. Overview
This test plan specifies the unit, validation, boundary, error-handling, and mocking test cases designed for the **SecureWipe** platform as part of Assignment 11. All tests are implemented using Python's built-in `unittest` framework and execute without modifying original project files, schemas, or databases.

## 2. Test Execution Environment
- **Operating System:** Windows 11 (64-bit)
- **Interpreter:** Python 3.14.7 (`.venv\Scripts\python.exe`)
- **Testing Framework:** Python Standard Library `unittest`
- **Execution Target:** `testing_assignment_11/run_tests.py` & `unittest discover`
- **Isolation Level:** Strict In-Memory Simulation (Zero database connections, zero external API calls)

---

## 3. Comprehensive Test Case Matrix

| Test ID | Functionality Under Test | Test Scenario | Input Data | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-UT-SM-01** | `RequestStateMachine` | Legal transition from `DRAFT` to `PENDING_APPROVAL` | `current=DRAFT`, `target=PENDING_APPROVAL` | `can_transition()` returns `True`; returns target state | Validated `True`; returned `PENDING_APPROVAL` | **PASS** |
| **TC-UT-SM-02** | `RequestStateMachine` | Legal transition from `PENDING_APPROVAL` to `APPROVED` | `current=PENDING_APPROVAL`, `target=APPROVED` | `can_transition()` returns `True`; returns `APPROVED` | Validated `True`; returned `APPROVED` | **PASS** |
| **TC-UT-SM-03** | `RequestStateMachine` | Reflexive transition to the identical state | `status == target_status` across all enum values | Reflexive transition is a valid no-op (`True`) | Returned `True` for all 10 enum values | **PASS** |
| **TC-UT-SM-04** | `RequestStateMachine` | Terminal states have no outbound legal transitions | Terminal states: `COMPLETED`, `REJECTED`, `EXPIRED`, `FAILED`, `CANCELLED` | Outbound transitions set length equals 0 | Evaluated length = 0 for all terminal states | **PASS** |
| **TC-UT-CRYPTO-01** | `security.hash_password` & `verify_password` | Argon2id password hashing and plaintext verification | Plaintext: `"SecureWipeP@ssw0rd2026!"` | Hash begins with `$argon2id$`; correct password returns `True`; wrong returns `False` | Hash verified; matched `True`; wrong password `False` | **PASS** |
| **TC-UT-CRYPTO-02** | `security.canonical_json` | RFC 8785 deterministic JSON key serialization | Two dictionaries with identical keys in different insertion orders | Serialized bytes are identical and keys are sorted alphabetically | Byte sequences identical (`b'{"alpha":1,"beta":2,"gamma":[3,4]}'`) | **PASS** |
| **TC-UT-CRYPTO-03** | `security.sha256_hex` | SHA-256 cryptographic hexadecimal hashing | String: `"SecureWipe-Audit-Genesis-2026"` | 64-character hex string matching known SHA-256 digest | Digest matched `9b1441c58cecb20...` (length 64) | **PASS** |
| **TC-UT-CRYPTO-04** | `security.sign_payload_ed25519` | Ed25519 asymmetric signature generation and verification | Canonical JSON payload bytes + ephemeral private PEM | Signature generated; public key verification returns `True` | Signature generated (Base64); verified `True` | **PASS** |
| **TC-UT-CRYPTO-05** | `security.create_access_token` & `decode_token` | JWT access token creation and claims decoding | `user_id=UUID`, `role="OPERATOR"` | Decoded token contains matching `sub`, `role`, `type="access"`, and timestamps | Claims decoded and matched exactly | **PASS** |
| **TC-UT-CRYPTO-06** | `security.compute_request_fingerprint` | Deterministic request fingerprint calculation | Device UUID, volume UUID list in different orders, method, serial | Fingerprint hash identical regardless of input volume ordering | Generated identical 64-char SHA-256 fingerprint | **PASS** |
| **TC-VAL-NIST-01** | `WipePlanner.create_plan` | Magnetic HDD NIST Clear policy planning | `media_type=HDD`, `method=NIST_800_88_CLEAR` | Single-pass zero overwrite (`OVERWRITE_ZERO`), 15% sample rate, hidden area check `True` | Single pass assigned, 15% sample rate verified | **PASS** |
| **TC-VAL-NIST-02** | `WipePlanner.create_plan` | Boundary testing: HDD Clear custom pass count overrides | Pass count overrides: `passes_override=3` and `passes_override=7` | Generated plan contains exactly 3 and 7 passes with sequential pass numbers | Pass sequences 1..3 and 1..7 confirmed | **PASS** |
| **TC-VAL-NIST-03** | `WipePlanner.create_plan` | Magnetic HDD NIST Purge policy planning | `media_type=HDD`, `method=NIST_800_88_PURGE` | `ATA_SECURE_ERASE_SIMULATED` pass; 100% verification sampling | Single ATA erase pass, 100.0% sample rate | **PASS** |
| **TC-VAL-NIST-04** | `WipePlanner.create_plan` | SATA SSD Purge cryptographic sanitize sequence | `media_type=SATA_SSD`, `method=NIST_800_88_PURGE` | 2 passes (`CRYPTO_ERASE` + `BLOCK_SANITIZE`); 100% verification | 2-pass sequence verified; 100% sample rate | **PASS** |
| **TC-VAL-NIST-05** | `WipePlanner.create_plan` | NVMe SSD Purge sanitization structure | `media_type=NVME_SSD`, `method=NIST_800_88_PURGE` | 2-pass sequence including cryptographic erase; 100% verification | 2 passes verified; 100% sample rate | **PASS** |
| **TC-VAL-NIST-06** | `WipePlanner.create_plan` | Boundary testing: Removable flash media verification percentage | `media_type=USB_FLASH` and `media_type=SD_CARD` | 25% verification sample percentage assigned to removable media | Verified 25.0% sample rate for both media types | **PASS** |
| **TC-VAL-NIST-07** | `WipePlan.to_dict` | Serialization schema and mandatory simulation mode check | Serialized `WipePlan` dictionary | Dictionary contains all 9 schema keys and `mode == "simulation"` | All keys present; `mode="simulation"` asserted | **PASS** |
| **TC-VAL-CHAS-01** | `chassis.classify_from_smbios_chassis` | Desktop SMBIOS chassis codes mapping | Chassis integer codes: 3, 4, 5, 6, 7 | Returns `("DESKTOP", 0.95)` | Returned `("DESKTOP", 0.95)` for all desktop codes | **PASS** |
| **TC-VAL-CHAS-02** | `chassis.classify_from_smbios_chassis` | Laptop SMBIOS chassis codes mapping | Chassis integer codes: 8, 9, 10, 14, 31, 32 | Returns `("LAPTOP", 0.95)` | Returned `("LAPTOP", 0.95)` for all laptop codes | **PASS** |
| **TC-VAL-CHAS-03** | `chassis.classify_from_smbios_chassis` | Server enclosure SMBIOS codes mapping | Chassis integer codes: 17, 23, 28 | Returns `("SERVER", 0.95)` | Returned `("SERVER", 0.95)` for all server codes | **PASS** |
| **TC-VAL-CHAS-04** | `chassis.classify_from_smbios_chassis` | Boundary test for `None` and unmapped chassis codes | Inputs: `None`, `9999` | `None` &rarr; `("OTHER", 0.3)`; `9999` &rarr; `("OTHER", 0.4)` | Returned expected fallback tuples | **PASS** |
| **TC-VAL-CHAS-05** | `chassis.classify_with_fallbacks` | Model keyword heuristic overrides | Model strings: "Dell Precision", "ThinkStation", "Raspberry Pi" | Precision+battery &rarr; `LAPTOP`; ThinkStation &rarr; `WORKSTATION`; SBC &rarr; `SINGLE_BOARD_COMPUTER` | Heuristics mapped correctly with high confidence | **PASS** |
| **TC-ERR-SM-01** | `RequestStateMachine.transition` | Illegal state jump raises exception | `current=DRAFT`, `target=COMPLETED` | Raises `InvalidStateTransitionError` with current and target status attributes | Exception raised; attributes matched | **PASS** |
| **TC-ERR-SM-02** | `RequestStateMachine.transition` | Unapproved execution jump raises exception | `current=PENDING_APPROVAL`, `target=RUNNING` | Raises `InvalidStateTransitionError` | Exception raised with descriptive error message | **PASS** |
| **TC-ERR-SM-03** | `RequestStateMachine.transition` | Transition attempt from terminal `COMPLETED` | `current=COMPLETED`, `target=RUNNING` | Raises `InvalidStateTransitionError` | Exception raised; terminal state protected | **PASS** |
| **TC-ERR-SM-04** | `RequestStateMachine.transition` | Transition attempt from terminal `REJECTED` | `current=REJECTED`, `target=APPROVED` | Raises `InvalidStateTransitionError` | Exception raised; terminal state protected | **PASS** |
| **TC-ERR-CRYPTO-01** | `security.verify_signature_ed25519` | Tampered payload bit-flip detection | Altered canonical JSON payload (e.g. `passes: 2` &rarr; `1`) | Signature verification returns `False` without unhandled crash | Tamper detected; returned `False` | **PASS** |
| **TC-ERR-CRYPTO-02** | `security.verify_signature_ed25519` | Corrupted signature string detection | Corrupted Base64 signature string | Signature verification returns `False` safely | Verification failed safely; returned `False` | **PASS** |
| **TC-ERR-CRYPTO-03** | `security.verify_signature_ed25519` | Signature verified with wrong public key | Payload signed with Keypair A; verified with Public Key B | Verification returns `False` | Returned `False` | **PASS** |
| **TC-ERR-CRYPTO-04** | `security.decode_token` | Tampered JWT access token signature | Valid JWT with altered signature segment | Raises `jwt.exceptions.InvalidSignatureError` | Exception raised; token rejected | **PASS** |
| **TC-ERR-CRYPTO-05** | `security.decode_token` | Expired JWT access token rejection | JWT generated with negative expiration delta (`-60s`) | Raises `jwt.exceptions.ExpiredSignatureError` | Exception raised; expired token rejected | **PASS** |
| **TC-ERR-MOCK-01** | `unittest.mock.patch` | External dependency isolation via test double | Mocking `WipePlanner.create_plan` using `@patch` | Dependency call intercepted; mock assertions validated | Mock executed; called once with exact arguments | **PASS** |

---

## 4. Test Summary & Results
- **Total Test Cases Executed:** 32
- **Passed:** 32 (100%)
- **Failed:** 0 (0%)
- **Errors:** 0 (0%)
- **Skipped:** 0 (0%)
- **Total Elapsed Execution Time:** ~0.17 seconds
- **Final Evaluation:** **ALL TESTS PASSED [SUCCESS]**
