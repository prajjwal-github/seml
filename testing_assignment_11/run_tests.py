"""Custom Test Runner and Report Generator for Assignment 11.

Demonstrates JUnit TestSuite and TestRunner equivalents in Python `unittest`:
- Constructs a unified `unittest.TestSuite`
- Executes tests with `unittest.TextTestRunner`
- Generates and saves a detailed execution report to `reports/test_results.txt`
"""

import io
import os
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from testing_assignment_11.tests.test_unit import (
    TestCryptographicSecurityUnit,
    TestRequestStateMachineUnit,
)
from testing_assignment_11.tests.test_validation import (
    TestChassisClassificationValidation,
    TestNISTPlannerValidation,
)
from testing_assignment_11.tests.test_error_cases import (
    TestCryptoTamperErrorCases,
    TestMockingAndTestIsolation,
    TestStateMachineErrorCases,
)


def build_test_suite() -> unittest.TestSuite:
    """Assembles all unit, validation, and error test classes into a single TestSuite."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 1. Core Unit Tests
    suite.addTests(loader.loadTestsFromTestCase(TestRequestStateMachineUnit))
    suite.addTests(loader.loadTestsFromTestCase(TestCryptographicSecurityUnit))

    # 2. Validation & Boundary Tests
    suite.addTests(loader.loadTestsFromTestCase(TestNISTPlannerValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestChassisClassificationValidation))

    # 3. Error & Exception Handling Tests
    suite.addTests(loader.loadTestsFromTestCase(TestStateMachineErrorCases))
    suite.addTests(loader.loadTestsFromTestCase(TestCryptoTamperErrorCases))
    suite.addTests(loader.loadTestsFromTestCase(TestMockingAndTestIsolation))

    return suite


def run_tests_and_generate_report() -> bool:
    """Executes the test suite, outputs results to console, and writes report to disk."""
    suite = build_test_suite()
    total_tests = suite.countTestCases()

    print("=" * 80)
    print("ASSIGNMENT 11: PYTHON UNIT TESTING SUITE (JUNIT EQUIVALENT)")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Test Cases Loaded: {total_tests}")
    print("=" * 80)

    # Capture output for both console and file report
    stream_buffer = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream_buffer, verbosity=2)

    start_time = time.time()
    result = runner.run(suite)
    elapsed = time.time() - start_time

    output_text = stream_buffer.getvalue()
    print(output_text)

    # Format execution report
    report_lines = [
        "=" * 80,
        "SECUREWIPE - ASSIGNMENT 11 UNIT TESTING REPORT",
        "=" * 80,
        f"Execution Date:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Testing Framework: Python Standard Library unittest 3.x (JUnit Equivalent)",
        f"Target Project:    SecureWipe (Certified IT Asset Sanitization Platform)",
        f"Isolation Mode:    Strict Simulation (No live DB, No external network)",
        "-" * 80,
        f"Tests Executed:    {result.testsRun}",
        f"Passed:            {result.testsRun - len(result.failures) - len(result.errors)}",
        f"Failures:          {len(result.failures)}",
        f"Errors:            {len(result.errors)}",
        f"Skipped:           {len(result.skipped)}",
        f"Execution Time:    {elapsed:.3f} seconds",
        f"Overall Outcome:   {'ALL TESTS PASSED [SUCCESS]' if result.wasSuccessful() else 'TEST FAILURES DETECTED [FAIL]'}",
        "=" * 80,
        "",
        "DETAILED EXECUTION TRACE:",
        "-" * 80,
        output_text,
    ]

    report_content = "\n".join(report_lines)

    # Save to reports directory
    report_file = PROJECT_ROOT / "testing_assignment_11" / "reports" / "test_results.txt"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(report_content, encoding="utf-8")

    print("=" * 80)
    print(f"Test report successfully saved to: {report_file}")
    print("=" * 80)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests_and_generate_report()
    sys.exit(0 if success else 1)
