"""Unit tests for the NIST SP 800-88 Rev. 1 WipePlanner."""

import pytest
from backend.models.enums import MediaType, NISTCategory, WipeMethod
from backend.services.wipe_planner import WipePlanner


def test_hdd_planner():
    """Verifies NIST plan for traditional spinning HDDs."""
    # HDD Clear: 1-pass overwrite
    plan_clear = WipePlanner.create_plan(MediaType.HDD, WipeMethod.NIST_800_88_CLEAR)
    assert plan_clear.nist_category == NISTCategory.CLEAR
    assert len(plan_clear.passes) == 1
    assert plan_clear.hidden_area_check is True

    # HDD Purge: ATA Secure Erase
    plan_purge = WipePlanner.create_plan(MediaType.HDD, WipeMethod.NIST_800_88_PURGE)
    assert plan_purge.nist_category == NISTCategory.PURGE
    assert plan_purge.passes[0]["type"] == "ATA_SECURE_ERASE_SIMULATED"
    assert plan_purge.verification_sample_pct == 100.0


def test_nvme_and_ssd_planner():
    """Verifies NIST plan for SATA SSD and NVMe drives."""
    # NVMe Purge: Crypto erase + NAND sanitize
    plan_nvme_purge = WipePlanner.create_plan(MediaType.NVME_SSD, WipeMethod.NIST_800_88_PURGE)
    assert plan_nvme_purge.nist_category == NISTCategory.PURGE
    assert len(plan_nvme_purge.passes) == 2
    assert plan_nvme_purge.passes[0]["type"] == "CRYPTO_ERASE"
    assert plan_nvme_purge.verification_sample_pct == 100.0


def test_mobile_and_removable_planner():
    """Verifies NIST plan for mobile eMMC/UFS and removable USB/SD media."""
    # eMMC Purge
    plan_emmc = WipePlanner.create_plan(MediaType.EMMC, WipeMethod.NIST_800_88_PURGE)
    assert plan_emmc.nist_category == NISTCategory.PURGE
    assert plan_emmc.passes[0]["type"] == "FBE_KEY_WIPE"

    # USB Flash Clear
    plan_usb = WipePlanner.create_plan(MediaType.USB_FLASH, WipeMethod.NIST_800_88_CLEAR)
    assert plan_usb.nist_category == NISTCategory.CLEAR
    assert len(plan_usb.passes) == 1
