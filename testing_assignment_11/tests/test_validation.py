"""Validation and Boundary Condition Tests for SecureWipe.

Demonstrates JUnit validation concepts in Python standard library `unittest`:
- Boundary value testing (e.g. minimum/maximum passes, verification percentages)
- Equivalence partitioning across storage media types
- Parameter structure and dictionary schema assertions
- Chassis code classification heuristics
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to path for standalone execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.models.enums import MediaType, NISTCategory, WipeMethod
from backend.services.wipe_planner import WipePlan, WipePlanner
from agent.wipe_agent.detect.chassis import (
    classify_from_smbios_chassis,
    classify_with_fallbacks,
)


class TestNISTPlannerValidation(unittest.TestCase):
    """Validation test suite for NIST SP 800-88 Rev. 1 sanitization policy planning."""

    def test_hdd_clear_default_single_pass_boundary(self):
        """TC-VAL-NIST-01: Verifies magnetic HDD NIST Clear generates 1 overwrite pass with 15% sample rate."""
        plan = WipePlanner.create_plan(
            media_type=MediaType.HDD,
            method=WipeMethod.NIST_800_88_CLEAR,
        )
        self.assertIsInstance(plan, WipePlan)
        self.assertEqual(plan.method, WipeMethod.NIST_800_88_CLEAR)
        self.assertEqual(len(plan.passes), 1, "Default HDD Clear must have exactly 1 pass")
        self.assertEqual(plan.passes[0]["type"], "OVERWRITE_ZERO")
        self.assertEqual(plan.verification_sample_pct, 15.0, "HDD Clear requires 15% random sector readback")
        self.assertTrue(plan.hidden_area_check, "Hidden area (HPA/DCO) check must be enabled")

    def test_hdd_clear_custom_pass_override_boundaries(self):
        """TC-VAL-NIST-02: Boundary testing for HDD Clear with custom pass count overrides (3 and 7 passes)."""
        # Boundary 1: 3-pass DoD-style overwrite
        plan_3 = WipePlanner.create_plan(
            media_type=MediaType.HDD,
            method=WipeMethod.NIST_800_88_CLEAR,
            passes_override=3,
        )
        self.assertEqual(len(plan_3.passes), 3)
        self.assertEqual(plan_3.passes[0]["pass_number"], 1)
        self.assertEqual(plan_3.passes[2]["pass_number"], 3)

        # Boundary 2: 7-pass multi-pass overwrite
        plan_7 = WipePlanner.create_plan(
            media_type=MediaType.HDD,
            method=WipeMethod.NIST_800_88_CLEAR,
            passes_override=7,
        )
        self.assertEqual(len(plan_7.passes), 7)
        self.assertEqual(plan_7.passes[6]["pass_number"], 7)

    def test_hdd_purge_requires_full_verification(self):
        """TC-VAL-NIST-03: Verifies magnetic HDD NIST Purge requires ATA Secure Erase and 100% verification."""
        plan = WipePlanner.create_plan(
            media_type=MediaType.HDD,
            method=WipeMethod.NIST_800_88_PURGE,
        )
        self.assertEqual(plan.method, WipeMethod.NIST_800_88_PURGE)
        self.assertEqual(len(plan.passes), 1)
        self.assertEqual(plan.passes[0]["type"], "ATA_SECURE_ERASE_SIMULATED")
        self.assertEqual(plan.verification_sample_pct, 100.0, "Purge methods mandate 100% verification sampling")

    def test_sata_ssd_purge_crypto_erase_passes(self):
        """TC-VAL-NIST-04: Verifies SATA SSD Purge plans cryptographic key invalidation followed by block sanitize."""
        plan = WipePlanner.create_plan(
            media_type=MediaType.SATA_SSD,
            method=WipeMethod.NIST_800_88_PURGE,
        )
        self.assertEqual(len(plan.passes), 2, "SSD Purge requires 2-stage sanitize sequence")
        self.assertEqual(plan.passes[0]["type"], "CRYPTO_ERASE")
        self.assertEqual(plan.passes[1]["type"], "BLOCK_SANITIZE")
        self.assertEqual(plan.verification_sample_pct, 100.0)

    def test_nvme_ssd_purge_structure(self):
        """TC-VAL-NIST-05: Verifies NVMe SSD Purge sanitization structure."""
        plan = WipePlanner.create_plan(
            media_type=MediaType.NVME_SSD,
            method=WipeMethod.NIST_800_88_PURGE,
        )
        self.assertEqual(len(plan.passes), 2)
        self.assertIn("CRYPTO_ERASE", [p["type"] for p in plan.passes])
        self.assertEqual(plan.verification_sample_pct, 100.0)

    def test_removable_media_sample_percentage_boundary(self):
        """TC-VAL-NIST-06: Verifies removable flash media (USB/SD) gets 25% verification readback."""
        usb_plan = WipePlanner.create_plan(
            media_type=MediaType.USB_FLASH,
            method=WipeMethod.NIST_800_88_CLEAR,
        )
        self.assertEqual(usb_plan.verification_sample_pct, 25.0)

        sd_plan = WipePlanner.create_plan(
            media_type=MediaType.SD_CARD,
            method=WipeMethod.NIST_800_88_CLEAR,
        )
        self.assertEqual(sd_plan.verification_sample_pct, 25.0)

    def test_plan_to_dict_mandatory_simulation_mode(self):
        """TC-VAL-NIST-07: Verifies serialized plan dictionary contains all required fields and mode is 'simulation'."""
        plan = WipePlanner.create_plan(
            media_type=MediaType.HDD,
            method=WipeMethod.NIST_800_88_CLEAR,
        )
        data = plan.to_dict()

        expected_keys = [
            "method",
            "nist_category",
            "method_name",
            "total_passes",
            "passes",
            "hidden_area_check",
            "verification_sample_pct",
            "description",
            "mode",
        ]
        for key in expected_keys:
            self.assertIn(key, data, f"Serialized plan dictionary must contain key '{key}'")

        self.assertEqual(data["mode"], "simulation", "Simulation mode flag must be present and immutable")


class TestChassisClassificationValidation(unittest.TestCase):
    """Validation test suite for SMBIOS chassis decoding and hardware categorization heuristics."""

    def test_desktop_chassis_codes_mapping(self):
        """TC-VAL-CHAS-01: Verifies standard desktop SMBIOS codes (3, 4, 6, 7) map to DESKTOP with 0.95 confidence."""
        desktop_codes = [3, 4, 5, 6, 7]
        for code in desktop_codes:
            with self.subTest(chassis_code=code):
                category, confidence = classify_from_smbios_chassis(code)
                self.assertEqual(category, "DESKTOP")
                self.assertEqual(confidence, 0.95)

    def test_laptop_chassis_codes_mapping(self):
        """TC-VAL-CHAS-02: Verifies laptop/portable SMBIOS codes (8, 9, 10, 14, 31, 32) map to LAPTOP."""
        laptop_codes = [8, 9, 10, 14, 31, 32]
        for code in laptop_codes:
            with self.subTest(chassis_code=code):
                category, confidence = classify_from_smbios_chassis(code)
                self.assertEqual(category, "LAPTOP")
                self.assertEqual(confidence, 0.95)

    def test_server_chassis_codes_mapping(self):
        """TC-VAL-CHAS-03: Verifies server enclosure codes (17, 23, 28) map to SERVER."""
        server_codes = [17, 23, 28]
        for code in server_codes:
            with self.subTest(chassis_code=code):
                category, confidence = classify_from_smbios_chassis(code)
                self.assertEqual(category, "SERVER")
                self.assertEqual(confidence, 0.95)

    def test_unknown_and_none_chassis_fallbacks(self):
        """TC-VAL-CHAS-04: Boundary test for None and unmapped chassis integer codes."""
        # None input
        cat_none, conf_none = classify_from_smbios_chassis(None)
        self.assertEqual(cat_none, "OTHER")
        self.assertEqual(conf_none, 0.3)

        # Unmapped large integer
        cat_unmapped, conf_unmapped = classify_from_smbios_chassis(9999)
        self.assertEqual(cat_unmapped, "OTHER")
        self.assertEqual(conf_unmapped, 0.4)

    def test_model_keyword_fallback_heuristics(self):
        """TC-VAL-CHAS-05: Verifies model string heuristic overrides for workstations and SBCs."""
        # Precision Workstation with battery
        cat, conf = classify_with_fallbacks(
            chassis_code=None,
            has_battery=True,
            model_name="Dell Precision 5570",
        )
        self.assertEqual(cat, "LAPTOP")

        # ThinkStation Desktop Workstation
        cat_ws, conf_ws = classify_with_fallbacks(
            chassis_code=None,
            has_battery=False,
            model_name="Lenovo ThinkStation P620",
        )
        self.assertEqual(cat_ws, "WORKSTATION")
        self.assertEqual(conf_ws, 0.9)

        # Raspberry Pi Single Board Computer
        cat_sbc, conf_sbc = classify_with_fallbacks(
            chassis_code=None,
            is_arm_sbc=True,
            model_name="Raspberry Pi 4 Model B",
        )
        self.assertEqual(cat_sbc, "SINGLE_BOARD_COMPUTER")
        self.assertEqual(conf_sbc, 0.98)


if __name__ == "__main__":
    unittest.main(verbosity=2)
