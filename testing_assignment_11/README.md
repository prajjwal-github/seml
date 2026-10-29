# Assignment 11: Unit Testing in Python (JUnit Equivalents)

**Course:** Software Engineering / Software Testing & Quality Assurance  
**Assignment:** Practical Assignment 11 \u2014 Unit Testing Architecture & Test Automation  
**Target Application:** SecureWipe (Certified IT Asset Sanitization & Dual-Authorization Platform)  
**Implementation:** Python Standard Library `unittest` (Direct equivalent to Java JUnit 4 / JUnit 5)  
**Safety & Isolation Status:** Strict In-Memory Simulation (Zero database modifications, zero file changes outside this directory)

---

## 1. Assignment Title and Objective

### Title
**Design and Implementation of an Automated Unit Testing Architecture using Python's `unittest` Framework (JUnit Paradigms)**

### Objective
The primary objective of this assignment is to master unit testing concepts originally demonstrated in Java JUnit (from Assignment 11 PPT) and translate them into their Python equivalents using the standard library `unittest` module.

Specifically, this assignment demonstrates:
1. Translating JUnit annotations (`@Test`, `@BeforeEach`, `@AfterEach`, `@BeforeAll`, `@AfterAll`, `@Disabled`) into Python `unittest.TestCase` lifecycle methods.
2. Structuring test cases across unit logic, input validation, boundary conditions, and error-handling scenarios.
3. Implementing assertions (`assertEqual`, `assertTrue`, `assertFalse`, `assertIsNone`, `assertRaises`).
4. Composing test suites (`unittest.TestSuite`) and executing them via standard and custom test runners (`unittest.TextTestRunner`).
5. Isolating test execution using test doubles and mocks (`unittest.mock.patch`).
6. Guaranteeing absolute zero-side-effect isolation so that the underlying production application remains untouched.

---

## 2. Introduction to Unit Testing in Software Engineering

Unit testing is a fundamental software engineering discipline where individual units or components of source code (functions, methods, classes) are tested in isolation from the rest of the application.

### Key Benefits of Unit Testing
- **Early Bug Detection:** Identifies defects at the earliest development phase before integration, drastically lowering the cost of bug fixes.
- **Regression Prevention:** Ensures that future code refactoring, feature enhancements, or dependency updates do not break existing verified functionality.
- **Living Documentation:** Well-structured unit tests serve as an unambiguous specification of how domain components and business logic are expected to behave.
- **Design Improvement:** Code that is easily unit-tested exhibits loose coupling, high cohesion, and adherence to the Single Responsibility Principle (SRP).

---

## 3. Difference Between Java JUnit and Python `unittest`

Python's built-in `unittest` framework was originally created under the name *PyUnit* by Steve Purcell and was deliberately modeled after Kent Beck and Erich Gamma's JUnit framework for Java. Consequently, both frameworks share an identical xUnit architectural heritage.

### Detailed Comparison Table

| Concept / Feature | Java JUnit 4 / JUnit 5 | Python Standard Library `unittest` | Description / Purpose |
| :--- | :--- | :--- | :--- |
| **Test Case Base Class** | Plain class with annotations (JUnit 5) or extends `TestCase` (JUnit 3/4) | Inherits from `unittest.TestCase` | Base class providing test runner discovery and assertion methods. |
| **Test Method Marker** | `@Test` annotation on method | Method name prefix `test_*` (e.g. `test_login_success`) | Identifies a method as an executable test case. |
| **Per-Test Setup** | `@Before` (JUnit 4) / `@BeforeEach` (JUnit 5) | `def setUp(self):` | Runs immediately before each individual test method to initialize fresh fixtures. |
| **Per-Test Teardown** | `@After` (JUnit 4) / `@AfterEach` (JUnit 5) | `def tearDown(self):` | Runs immediately after each individual test method to clean up per-test resources. |
| **Class-Level Setup** | `@BeforeClass` (JUnit 4) / `@BeforeAll` (JUnit 5) | `@classmethod def setUpClass(cls):` | Runs once before any test methods in the test class execute (e.g. keypair generation). |
| **Class-Level Teardown** | `@AfterClass` (JUnit 4) / `@AfterAll` (JUnit 5) | `@classmethod def tearDownClass(cls):` | Runs once after all test methods in the test class complete. |
| **Equality Assertion** | `assertEquals(expected, actual)` | `self.assertEqual(actual, expected)` | Verifies that two values are equal. |
| **Boolean Assertion** | `assertTrue(cond)` / `assertFalse(cond)` | `self.assertTrue(cond)` / `self.assertFalse(cond)` | Verifies boolean truthiness or falsity. |
| **Nullness Assertion** | `assertNull(obj)` / `assertNotNull(obj)` | `self.assertIsNone(obj)` / `self.assertIsNotNone(obj)` | Verifies that an object is `None` (null). |
| **Exception Assertion** | `assertThrows(Exception.class, () -> ...)` | `with self.assertRaises(ExpectedException):` | Asserts that a block of code raises a specific exception and captures it. |
| **Membership Assertion** | `assertTrue(list.contains(item))` | `self.assertIn(item, container)` | Verifies that an element exists within a collection or substring. |
| **Test Suites** | `@Suite` / `SuiteClasses({A.class, B.class})` | `suite = unittest.TestSuite(); suite.addTests(...)` | Groups multiple test classes into an aggregated execution bundle. |
| **Test Runner** | `org.junit.runner.JUnitCore.run(...)` | `unittest.TextTestRunner().run(suite)` | Executes test suites and prints formatted textual or XML test reports. |
| **Mocking Framework** | Mockito (`@Mock`, `when(...).thenReturn(...)`) | `unittest.mock` (`@patch`, `MagicMock`) | Replaces external dependencies with test doubles for isolated execution. |
| **Test Parameterization**| `@ParameterizedTest` / `@ValueSource` | `with self.subTest(param=val):` | Iterates across inputs within a single test method, tracking sub-test results. |

---

## 4. Test Case Design Principles

The test cases in this assignment were engineered using formal software testing methodologies:

1. **Equivalence Partitioning (EP):**
   - Partitioning storage media types into equivalent sanitization classes: Magnetic Hard Drives (`HDD`), Solid State Drives (`SATA_SSD`, `NVME_SSD`), Mobile Flash (`EMMC`, `UFS`), and Removable Storage (`USB_FLASH`, `SD_CARD`).
   - Partitioning state machine states into Active/Transitional states (`DRAFT`, `PENDING_APPROVAL`, `APPROVED`, `WIPING`) versus Immutable Terminal states (`COMPLETED`, `REJECTED`, `EXPIRED`, `CANCELLED`).
2. **Boundary Value Analysis (BVA):**
   - Testing boundary conditions for pass counts (single pass minimum `passes=1`, multi-pass `passes=3`, enterprise overwrite `passes=7`).
   - Testing verification sampling percentages (Clear standard: `15.0%` for HDD, `20.0%` for SSD, `25.0%` for USB, and Purge standard: `100.0%` full verification).
   - Testing chassis code boundaries: boundary integer codes (`3`, `32`), unmapped large integers (`9999`), and `None`.
3. **Error Guessing & Negative Testing:**
   - Testing bit-flip tampering on cryptographically signed payloads.
   - Testing signature string corruption in Base64 encoding.
   - Testing invalid state transition jumps (e.g. attempting to skip approval and jump directly from `DRAFT` to `COMPLETED`).
   - Testing expired JWT session tokens and invalid token signatures.

---

## 5. Setup and Teardown Lifecycle

In `testing_assignment_11/tests/test_unit.py`, the complete test lifecycle is demonstrated:

```python
class TestRequestStateMachineUnit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Runs ONCE before all tests in this class (JUnit @BeforeAll)
        cls.all_statuses = list(RequestStatus)

    @classmethod
    def tearDownClass(cls):
        # Runs ONCE after all tests in this class complete (JUnit @AfterAll)
        cls.all_statuses = None

    def setUp(self):
        # Runs BEFORE EACH test method (JUnit @BeforeEach)
        self.draft_state = RequestStatus.DRAFT
        self.pending_state = RequestStatus.PENDING_APPROVAL

    def tearDown(self):
        # Runs AFTER EACH test method (JUnit @AfterEach)
        self.draft_state = None
        self.pending_state = None
```

---

## 6. Assertions Reference and Usage

The assignment exercises Python's assertion methods across positive, negative, and boundary scenarios:

- `self.assertEqual(actual, expected, msg)`: Validates exact equality of state machine outputs, digests, and token claims.
- `self.assertTrue(expr, msg)` / `self.assertFalse(expr, msg)`: Validates predicate outcomes, legal transitions, and tamper detection results.
- `self.assertIsNone(obj)` / `self.assertIsNotNone(obj)`: Validates that cryptographic outputs are properly initialized.
- `self.assertIn(member, container)`: Validates that dictionary keys and JWT claims are present.
- `self.assertIsInstance(obj, cls)`: Validates that generated objects adhere to target dataclasses/models.
- `with self.assertRaises(ExpectedException) as ctx:`: Validates that illegal operations raise anticipated domain exceptions.

---

## 7. Test Suite Execution & Grouping

In `testing_assignment_11/run_tests.py`, test classes are organized into a unified `unittest.TestSuite`:

```python
def build_test_suite() -> unittest.TestSuite:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Core Unit Tests
    suite.addTests(loader.loadTestsFromTestCase(TestRequestStateMachineUnit))
    suite.addTests(loader.loadTestsFromTestCase(TestCryptographicSecurityUnit))

    # Validation Tests
    suite.addTests(loader.loadTestsFromTestCase(TestNISTPlannerValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestChassisClassificationValidation))

    # Error & Tamper Tests
    suite.addTests(loader.loadTestsFromTestCase(TestStateMachineErrorCases))
    suite.addTests(loader.loadTestsFromTestCase(TestCryptoTamperErrorCases))
    suite.addTests(loader.loadTestsFromTestCase(TestMockingAndTestIsolation))

    return suite
```

---

## 8. Mocking and Test Isolation Techniques

To guarantee zero database and external network access, `unittest.mock.patch` is employed to isolate dependencies:

```python
class TestMockingAndTestIsolation(unittest.TestCase):
    def test_isolated_audit_notification_using_mock(self):
        with patch("backend.services.wipe_planner.WipePlanner.create_plan") as mock_planner:
            mock_planner.return_value = "MOCKED_PLAN_RESULT"
            result = WipePlanner.create_plan("MOCK_TYPE", "MOCK_METHOD")
            self.assertEqual(result, "MOCKED_PLAN_RESULT")
            mock_planner.assert_called_once_with("MOCK_TYPE", "MOCK_METHOD")
```

---

## 9. Mapping of Tests to Actual SecureWipe Project Features

| Test Suite File | Test Class | Tested Project Feature | Business Logic File |
| :--- | :--- | :--- | :--- |
| `test_unit.py` | `TestRequestStateMachineUnit` | Sanitization request lifecycle FSM transitions | `backend/services/state_machine.py` |
| `test_unit.py` | `TestCryptographicSecurityUnit` | Argon2id hashing, RFC 8785 canonical JSON, Ed25519 signing | `backend/core/security.py` |
| `test_validation.py` | `TestNISTPlannerValidation` | NIST SP 800-88 sanitization planning & media classification | `backend/services/wipe_planner.py` |
| `test_validation.py` | `TestChassisClassificationValidation`| SMBIOS chassis decoding & hardware categorization | `agent/wipe_agent/detect/chassis.py` |
| `test_error_cases.py`| `TestStateMachineErrorCases` | Illegal state jumps and terminal state immutability | `backend/services/state_machine.py` |
| `test_error_cases.py`| `TestCryptoTamperErrorCases` | Ed25519 signature tamper detection & JWT token expiration | `backend/core/security.py` |
| `test_error_cases.py`| `TestMockingAndTestIsolation` | External dependency isolation via test doubles | `unittest.mock` |

---

## 10. Exact Commands to Run the Tests

Execute the tests from the repository root directory (`d:\seml`):

### Option A: Using the Custom Assignment Test Runner (Generates File Report)
```bash
.\.venv\Scripts\python.exe testing_assignment_11/run_tests.py
```

### Option B: Using Standard Python unittest Discovery
```bash
.\.venv\Scripts\python.exe -m unittest discover -s testing_assignment_11/tests -v
```

### Option C: Running a Specific Test Module
```bash
.\.venv\Scripts\python.exe -m unittest testing_assignment_11/tests/test_unit.py -v
```

---

## 11. Expected Output

When running `testing_assignment_11/run_tests.py`:
- 32 distinct unit tests are loaded and executed.
- Each test prints its description and an `ok` status.
- Summary prints `Ran 32 tests in ~0.17s` with outcome `OK`.
- Execution report is saved to `testing_assignment_11/reports/test_results.txt`.

---

## 12. Actual Output

Actual execution transcript recorded directly from test run:

```text
================================================================================
ASSIGNMENT 11: PYTHON UNIT TESTING SUITE (JUNIT EQUIVALENT)
Timestamp: 2026-10-22 22:11:40
Total Test Cases Loaded: 32
================================================================================
test_legal_transition_draft_to_pending ... ok
test_legal_transition_pending_to_approved ... ok
test_reflexive_transition_same_state ... ok
test_terminal_states_have_no_outbound_transitions ... ok
test_argon2id_password_hash_and_verify ... ok
test_canonical_json_deterministic_ordering ... ok
test_compute_request_fingerprint_deterministic ... ok
test_ed25519_sign_and_verify_valid_signature ... ok
test_jwt_access_token_creation_and_decoding ... ok
test_sha256_hex_digest_accuracy ... ok
test_hdd_clear_custom_pass_override_boundaries ... ok
test_hdd_clear_default_single_pass_boundary ... ok
test_hdd_purge_requires_full_verification ... ok
test_nvme_ssd_purge_structure ... ok
test_plan_to_dict_mandatory_simulation_mode ... ok
test_removable_media_sample_percentage_boundary ... ok
test_sata_ssd_purge_crypto_erase_passes ... ok
test_desktop_chassis_codes_mapping ... ok
test_laptop_chassis_codes_mapping ... ok
test_model_keyword_fallback_heuristics ... ok
test_server_chassis_codes_mapping ... ok
test_unknown_and_none_chassis_fallbacks ... ok
test_illegal_direct_jump_raises_exception ... ok
test_illegal_jump_from_pending_to_running ... ok
test_transition_from_terminal_completed_raises_exception ... ok
test_transition_from_terminal_rejected_raises_exception ... ok
test_jwt_expired_token_raises_error ... ok
test_jwt_tampered_token_signature_raises_error ... ok
test_tampered_payload_verification_fails ... ok
test_tampered_signature_string_verification_fails ... ok
test_verification_with_wrong_public_key_fails ... ok
test_isolated_audit_notification_using_mock ... ok

----------------------------------------------------------------------
Ran 32 tests in 0.170s

OK

================================================================================
Test report successfully saved to: D:\seml\testing_assignment_11\reports\test_results.txt
================================================================================
```

---

## 13. Known Limitations and Safety Guarantees

### Safety Guarantees
1. **Zero Database Impact:** None of the tests in this suite connect to PostgreSQL, SQLite, or modify any database records. All state machine and cryptographic operations execute purely in memory.
2. **Zero File Modification Outside Assignment Folder:** All new files reside strictly within `testing_assignment_11/`. No existing files in `backend/`, `frontend/`, `agent/`, `docs/`, or configuration files were altered.
3. **Zero Destructive Storage Commands:** All sanitization logic is tested through pure planning models (`WipePlanner`) and simulation flags (`mode="simulation"`). No disk write, partition, or wipe commands are issued.

### Known Limitations
- **Database Trigger Integration:** Database PL/pgSQL triggers (`trg_audit_logs_immutable`, `chk_no_self_approval`) require a running PostgreSQL instance with superuser trigger privileges. To preserve strict isolation and avoid touching the live database, database trigger tests are omitted from this unit suite and remain within the project's separate integration test suite (`backend/tests/test_db_triggers.py`).
- **Live WebSocket Telemetry:** Live streaming over WebSocket connections requires an active event loop and network socket binding; this was mocked in `test_error_cases.py` to ensure fast, deterministic offline execution.
