"""Error-Handling, Exception, and Tamper-Detection Tests for SecureWipe.

Demonstrates JUnit exception and negative testing equivalents in Python standard library `unittest`:
- `self.assertRaises(...)` / `with self.assertRaises(ExpectedException):` (JUnit assertThrows)
- Negative security assertions and cryptographic tamper detection
- Mocking and dependency isolation using `unittest.mock.patch`
"""

import base64
import os
import sys
import unittest
import uuid
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path for standalone execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import jwt
from backend.models.enums import RequestStatus
from backend.services.state_machine import (
    InvalidStateTransitionError,
    RequestStateMachine,
)
from backend.core.security import (
    canonical_json,
    create_access_token,
    decode_token,
    generate_ed25519_keypair,
    sign_payload_ed25519,
    verify_password,
    verify_signature_ed25519,
)


class TestStateMachineErrorCases(unittest.TestCase):
    """Error-handling tests for illegal state machine transitions and domain exceptions."""

    def test_illegal_direct_jump_raises_exception(self):
        """TC-ERR-SM-01: Verifies attempting to jump directly from DRAFT to COMPLETED raises InvalidStateTransitionError."""
        with self.assertRaises(InvalidStateTransitionError) as ctx:
            RequestStateMachine.transition(RequestStatus.DRAFT, RequestStatus.COMPLETED)

        # Inspect exception details (equivalent to JUnit assertThrows return value)
        exc = ctx.exception
        self.assertEqual(exc.current_status, RequestStatus.DRAFT)
        self.assertEqual(exc.target_status, RequestStatus.COMPLETED)
        self.assertIn("Illegal state transition from 'DRAFT' to 'COMPLETED'", str(exc))

    def test_illegal_jump_from_pending_to_running(self):
        """TC-ERR-SM-02: Verifies jumping from PENDING_APPROVAL directly to RUNNING without approval raises exception."""
        with self.assertRaises(InvalidStateTransitionError) as ctx:
            RequestStateMachine.transition(RequestStatus.PENDING_APPROVAL, RequestStatus.RUNNING)

        self.assertIn("PENDING_APPROVAL", str(ctx.exception))
        self.assertIn("RUNNING", str(ctx.exception))

    def test_transition_from_terminal_completed_raises_exception(self):
        """TC-ERR-SM-03: Verifies attempting to transition out of terminal COMPLETED state raises InvalidStateTransitionError."""
        with self.assertRaises(InvalidStateTransitionError):
            RequestStateMachine.transition(RequestStatus.COMPLETED, RequestStatus.RUNNING)

        with self.assertRaises(InvalidStateTransitionError):
            RequestStateMachine.transition(RequestStatus.COMPLETED, RequestStatus.DRAFT)

    def test_transition_from_terminal_rejected_raises_exception(self):
        """TC-ERR-SM-04: Verifies attempting to transition out of terminal REJECTED state raises InvalidStateTransitionError."""
        with self.assertRaises(InvalidStateTransitionError):
            RequestStateMachine.transition(RequestStatus.REJECTED, RequestStatus.APPROVED)


class TestCryptoTamperErrorCases(unittest.TestCase):
    """Negative testing suite for cryptographic tamper detection and invalid credentials."""

    @classmethod
    def setUpClass(cls):
        """Generates keypairs for cryptographic negative testing."""
        cls.public_pem_a, cls.private_pem_a = generate_ed25519_keypair()
        cls.public_pem_b, cls.private_pem_b = generate_ed25519_keypair()

    def setUp(self):
        self.valid_payload = {
            "certificate_id": "CERT-TAMPER-TEST-001",
            "media_sanitized": "SATA_SSD_512GB",
            "passes": 2,
            "status": "COMPLETED",
        }
        self.canonical_bytes = canonical_json(self.valid_payload)
        self.valid_signature = sign_payload_ed25519(self.canonical_bytes, self.private_pem_a)

    def test_tampered_payload_verification_fails(self):
        """TC-ERR-CRYPTO-01: Verifies that modifying a single character in the payload causes signature verification to fail."""
        # Tamper payload: change passes from 2 to 1
        tampered_payload = dict(self.valid_payload)
        tampered_payload["passes"] = 1
        tampered_bytes = canonical_json(tampered_payload)

        # Verification must return False (tamper detected)
        is_valid = verify_signature_ed25519(tampered_bytes, self.valid_signature, self.public_pem_a)
        self.assertFalse(is_valid, "Tampered payload must fail Ed25519 signature verification")

    def test_tampered_signature_string_verification_fails(self):
        """TC-ERR-CRYPTO-02: Verifies that corrupting the Base64 signature string causes verification to fail safely."""
        # Corrupt the last character of the Base64 signature string
        corrupted_signature = (
            self.valid_signature[:-1] + ("A" if self.valid_signature[-1] != "A" else "B")
        )

        is_valid = verify_signature_ed25519(self.canonical_bytes, corrupted_signature, self.public_pem_a)
        self.assertFalse(is_valid, "Corrupted signature string must return False without crashing")

    def test_verification_with_wrong_public_key_fails(self):
        """TC-ERR-CRYPTO-03: Verifies that verifying a valid signature with an unassociated public key fails."""
        # Keypair B public key against signature generated with Keypair A
        is_valid = verify_signature_ed25519(self.canonical_bytes, self.valid_signature, self.public_pem_b)
        self.assertFalse(is_valid, "Signature must not verify with an unrelated public key")

    def test_jwt_tampered_token_signature_raises_error(self):
        """TC-ERR-CRYPTO-04: Verifies that altering a signed JWT token string raises InvalidSignatureError."""
        valid_token = create_access_token(user_id=uuid.uuid4(), role="APPROVER")
        header, payload, sig = valid_token.split(".")

        # Flip the first character of the signature to another valid base64url char ('a' <-> 'b')
        flipped_char = "b" if sig[0] == "a" else "a"
        tampered_sig = flipped_char + sig[1:]
        tampered_token = f"{header}.{payload}.{tampered_sig}"

        with self.assertRaises(jwt.exceptions.InvalidSignatureError):
            decode_token(tampered_token)

    def test_jwt_expired_token_raises_error(self):
        """TC-ERR-CRYPTO-05: Verifies that passing an expired JWT access token raises ExpiredSignatureError."""
        expired_delta = timedelta(seconds=-60)  # Expired 1 minute ago
        expired_token = create_access_token(
            user_id=uuid.uuid4(),
            role="OPERATOR",
            expires_delta=expired_delta,
        )

        with self.assertRaises(jwt.exceptions.ExpiredSignatureError):
            decode_token(expired_token)


class TestMockingAndTestIsolation(unittest.TestCase):
    """Demonstrates test isolation and dependency mocking using `unittest.mock`."""

    def test_isolated_audit_notification_using_mock(self):
        """TC-ERR-MOCK-01: Verifies external notification service can be isolated using unittest.mock.patch."""
        # Simulated external notifier function
        mock_notifier = MagicMock(return_value=True)

        with patch("backend.services.wipe_planner.WipePlanner.create_plan") as mock_planner:
            # Configure mock return value
            mock_planner.return_value = "MOCKED_PLAN_RESULT"

            # Execute code that depends on planner
            from backend.services.wipe_planner import WipePlanner
            result = WipePlanner.create_plan("MOCK_TYPE", "MOCK_METHOD")

            # Assertions on mock interaction
            self.assertEqual(result, "MOCKED_PLAN_RESULT")
            mock_planner.assert_called_once_with("MOCK_TYPE", "MOCK_METHOD")


if __name__ == "__main__":
    unittest.main(verbosity=2)
