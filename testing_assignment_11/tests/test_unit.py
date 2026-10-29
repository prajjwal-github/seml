"""Unit Tests for Core SecureWipe Business Logic.

Demonstrates JUnit equivalents in Python standard library `unittest`:
- Test lifecycle fixtures: `setUpClass`, `tearDownClass`, `setUp`, `tearDown`
- Assertions: `assertEqual`, `assertTrue`, `assertFalse`, `assertIsNone`, `assertIn`
- Testing state machine transitions and cryptographic primitives
"""

import os
import sys
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path for standalone execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.models.enums import RequestStatus
from backend.services.state_machine import RequestStateMachine
from backend.core.security import (
    canonical_json,
    compute_request_fingerprint,
    create_access_token,
    decode_token,
    generate_ed25519_keypair,
    hash_password,
    sha256_hex,
    sign_payload_ed25519,
    verify_password,
    verify_signature_ed25519,
)


class TestRequestStateMachineUnit(unittest.TestCase):
    """Unit test suite for RequestStateMachine lifecycle logic.

    Equivalent to JUnit `@Nested` or test class focusing on state transitions.
    """

    @classmethod
    def setUpClass(cls):
        """Executes once before any test in this class runs (JUnit @BeforeAll / @BeforeClass)."""
        cls.all_statuses = list(RequestStatus)

    @classmethod
    def tearDownClass(cls):
        """Executes once after all tests in this class complete (JUnit @AfterAll / @AfterClass)."""
        cls.all_statuses = None

    def setUp(self):
        """Executes before each individual test method (JUnit @BeforeEach / @Before)."""
        self.draft_state = RequestStatus.DRAFT
        self.pending_state = RequestStatus.PENDING_APPROVAL
        self.approved_state = RequestStatus.APPROVED
        self.completed_state = RequestStatus.COMPLETED

    def tearDown(self):
        """Executes after each individual test method (JUnit @AfterEach / @After)."""
        # Clean up per-test references
        self.draft_state = None
        self.pending_state = None
        self.approved_state = None
        self.completed_state = None

    def test_legal_transition_draft_to_pending(self):
        """TC-UT-SM-01: Verifies transition from DRAFT to PENDING_APPROVAL is allowed."""
        can_move = RequestStateMachine.can_transition(self.draft_state, self.pending_state)
        self.assertTrue(can_move, "DRAFT should be legally allowed to transition to PENDING_APPROVAL")

        result = RequestStateMachine.transition(self.draft_state, self.pending_state)
        self.assertEqual(result, RequestStatus.PENDING_APPROVAL)

    def test_legal_transition_pending_to_approved(self):
        """TC-UT-SM-02: Verifies transition from PENDING_APPROVAL to APPROVED is allowed."""
        can_move = RequestStateMachine.can_transition(self.pending_state, self.approved_state)
        self.assertTrue(can_move, "PENDING_APPROVAL should be legally allowed to transition to APPROVED")

        result = RequestStateMachine.transition(self.pending_state, self.approved_state)
        self.assertEqual(result, RequestStatus.APPROVED)

    def test_reflexive_transition_same_state(self):
        """TC-UT-SM-03: Verifies that transitioning to the identical state is a no-op."""
        for status in self.all_statuses:
            with self.subTest(status=status):
                self.assertTrue(
                    RequestStateMachine.can_transition(status, status),
                    f"Reflexive transition for state {status} must be valid",
                )
                self.assertEqual(RequestStateMachine.transition(status, status), status)

    def test_terminal_states_have_no_outbound_transitions(self):
        """TC-UT-SM-04: Verifies that terminal states (COMPLETED, REJECTED, etc.) have no outbound transitions."""
        terminal_states = [
            RequestStatus.COMPLETED,
            RequestStatus.REJECTED,
            RequestStatus.EXPIRED,
            RequestStatus.FAILED,
            RequestStatus.CANCELLED,
        ]
        for term in terminal_states:
            with self.subTest(state=term):
                allowed_targets = RequestStateMachine.LEGAL_TRANSITIONS.get(term, set())
                self.assertEqual(
                    len(allowed_targets),
                    0,
                    f"Terminal state '{term.value}' must not have any outbound transitions",
                )


class TestCryptographicSecurityUnit(unittest.TestCase):
    """Unit test suite for cryptographic primitives and security helpers.

    Tests Argon2id hashing, RFC 8785 canonical JSON, and Ed25519 digital signatures.
    """

    @classmethod
    def setUpClass(cls):
        """Generates an ephemeral Ed25519 keypair once for the entire test class."""
        cls.public_pem, cls.private_pem = generate_ed25519_keypair()

    @classmethod
    def tearDownClass(cls):
        """Cleans up the ephemeral keypair."""
        cls.public_pem = None
        cls.private_pem = None

    def setUp(self):
        """Sets up test data for each test method."""
        self.test_password = "SecureWipeP@ssw0rd2026!"
        self.test_payload = {
            "certificate_id": "CERT-2026-TEST-001",
            "device_serial": "DELL-SN-789012",
            "sanitization_standard": "NIST_800_88_PURGE",
            "verification_status": "VERIFIED_PASSED",
            "passes_completed": 2,
        }

    def test_argon2id_password_hash_and_verify(self):
        """TC-UT-CRYPTO-01: Verifies password hashing and verification with Argon2id."""
        hashed = hash_password(self.test_password)
        self.assertIsNotNone(hashed, "Hashed password must not be None")
        self.assertTrue(hashed.startswith("$argon2id$"), "Hash must use Argon2id format")

        # Positive verification
        is_valid = verify_password(self.test_password, hashed)
        self.assertTrue(is_valid, "Password verification must succeed with correct plaintext")

        # Negative verification
        is_invalid = verify_password("WrongPassword123!", hashed)
        self.assertFalse(is_invalid, "Password verification must fail with incorrect plaintext")

    def test_canonical_json_deterministic_ordering(self):
        """TC-UT-CRYPTO-02: Verifies RFC 8785 canonical JSON produces identical byte sequences regardless of key insertion order."""
        dict_order_a = {"alpha": 1, "beta": 2, "gamma": [3, 4]}
        dict_order_b = {"gamma": [3, 4], "alpha": 1, "beta": 2}

        bytes_a = canonical_json(dict_order_a)
        bytes_b = canonical_json(dict_order_b)

        self.assertEqual(bytes_a, bytes_b, "Canonical JSON must sort keys deterministically")
        self.assertEqual(bytes_a, b'{"alpha":1,"beta":2,"gamma":[3,4]}')

    def test_sha256_hex_digest_accuracy(self):
        """TC-UT-CRYPTO-03: Verifies SHA-256 hexadecimal hashing matches standard test vector."""
        test_string = "SecureWipe-Audit-Genesis-2026"
        expected_digest = "9b1441c58cecb20aeda96a0ada2a62012b19b1484fb33d58ab834d71ea7a3ca6"
        actual_digest = sha256_hex(test_string)

        self.assertEqual(len(actual_digest), 64, "SHA-256 hex digest must be 64 characters long")
        self.assertEqual(actual_digest, expected_digest)

    def test_ed25519_sign_and_verify_valid_signature(self):
        """TC-UT-CRYPTO-04: Verifies Ed25519 signing and positive signature verification."""
        canonical_bytes = canonical_json(self.test_payload)
        signature_b64 = sign_payload_ed25519(canonical_bytes, self.private_pem)

        self.assertIsNotNone(signature_b64, "Generated signature must not be None")
        self.assertTrue(len(signature_b64) > 0, "Generated signature must not be empty")

        # Verify signature with corresponding public key
        is_valid = verify_signature_ed25519(canonical_bytes, signature_b64, self.public_pem)
        self.assertTrue(is_valid, "Ed25519 signature must verify successfully with matching public key")

    def test_jwt_access_token_creation_and_decoding(self):
        """TC-UT-CRYPTO-05: Verifies JWT access token generation and claims decoding."""
        user_uuid = uuid.uuid4()
        user_role = "OPERATOR"
        token = create_access_token(user_id=user_uuid, role=user_role)

        self.assertIsInstance(token, str, "Access token must be a string")
        decoded = decode_token(token)

        self.assertEqual(decoded["sub"], str(user_uuid))
        self.assertEqual(decoded["role"], user_role)
        self.assertEqual(decoded["type"], "access")
        self.assertIn("exp", decoded)
        self.assertIn("iat", decoded)

    def test_compute_request_fingerprint_deterministic(self):
        """TC-UT-CRYPTO-06: Verifies deterministic request fingerprint calculation."""
        dev_id = uuid.uuid4()
        vol_a = uuid.uuid4()
        vol_b = uuid.uuid4()

        # Order 1
        fp_1 = compute_request_fingerprint(
            device_id=dev_id,
            volume_ids=[vol_a, vol_b],
            method="NIST_800_88_PURGE",
            serial_number="SERIAL-123",
        )
        # Order 2 (reversed volume IDs)
        fp_2 = compute_request_fingerprint(
            device_id=dev_id,
            volume_ids=[vol_b, vol_a],
            method="NIST_800_88_PURGE",
            serial_number="SERIAL-123",
        )

        self.assertEqual(fp_1, fp_2, "Volume list ordering must be sorted deterministically in fingerprint")
        self.assertEqual(len(fp_1), 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
