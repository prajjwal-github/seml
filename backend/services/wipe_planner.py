"""NIST SP 800-88 Rev. 1 sanitization planner mapping media types to Clear/Purge methods."""

from typing import Any, Dict, List, Optional
from backend.models.enums import MediaType, NISTCategory, WipeMethod


class WipePlan:
    """Represents a planned sanitization recipe for one or more storage volumes."""

    def __init__(
        self,
        method: WipeMethod,
        nist_category: NISTCategory,
        method_name: str,
        passes: List[Dict[str, Any]],
        hidden_area_check: bool,
        verification_sample_pct: float,
        description: str,
    ):
        self.method = method
        self.nist_category = nist_category
        self.method_name = method_name
        self.passes = passes
        self.hidden_area_check = hidden_area_check
        self.verification_sample_pct = verification_sample_pct
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": getattr(self.method, "value", self.method),
            "nist_category": getattr(self.nist_category, "value", self.nist_category),
            "method_name": self.method_name,
            "total_passes": len(self.passes),
            "passes": self.passes,
            "hidden_area_check": self.hidden_area_check,
            "verification_sample_pct": self.verification_sample_pct,
            "description": self.description,
            "mode": "simulation",
        }


class WipePlanner:
    """Generates NIST SP 800-88 Rev. 1 compliant sanitization plans."""

    @classmethod
    def create_plan(
        self,
        media_type: MediaType,
        method: WipeMethod,
        passes_override: Optional[int] = None,
    ) -> WipePlan:
        """Determines the appropriate simulated sanitization recipe based on media characteristics."""
        # Callers may pass raw strings read from the database; normalise them to enums
        method = WipeMethod(getattr(method, "value", method))
        try:
            media_type = MediaType(getattr(media_type, "value", media_type))
        except ValueError:
            media_type = MediaType.OTHER
        is_purge = method == WipeMethod.NIST_800_88_PURGE

        if media_type == MediaType.HDD:
            if is_purge:
                passes = [
                    {"pass_number": 1, "type": "ATA_SECURE_ERASE_SIMULATED", "name": "ATA Secure Erase Command"}
                ]
                desc = "NIST SP 800-88 Rev. 1 Purge: ATA Secure Erase firmware command simulation with complete sector clearing."
                verify_pct = 100.0
            else:
                num_passes = passes_override or 1
                passes = [
                    {"pass_number": i, "type": "OVERWRITE_ZERO", "name": f"Single-Pass Pseudorandom Zero Overwrite (Pass {i})"}
                    for i in range(1, num_passes + 1)
                ]
                desc = f"NIST SP 800-88 Rev. 1 Clear: {num_passes}-pass logical overwrite across all addressable storage sectors."
                verify_pct = 15.0

        elif media_type in (MediaType.SATA_SSD, MediaType.NVME_SSD):
            if is_purge:
                passes = [
                    {"pass_number": 1, "type": "CRYPTO_ERASE", "name": "Cryptographic Key Invalidation"},
                    {"pass_number": 2, "type": "BLOCK_SANITIZE", "name": "NAND Flash Block Sanitize & Wear-Leveling Sweep"},
                ]
                desc = "NIST SP 800-88 Rev. 1 Purge: Cryptographic erase combined with controller-level block sanitization."
                verify_pct = 100.0
            else:
                passes = [
                    {"pass_number": 1, "type": "LOGICAL_OVERWRITE", "name": "NAND Logical LBA Overwrite"}
                ]
                desc = "NIST SP 800-88 Rev. 1 Clear: Logical address overwrite bypassing flash wear-leveling remappings."
                verify_pct = 20.0

        elif media_type in (MediaType.EMMC, MediaType.UFS):
            if is_purge:
                passes = [
                    {"pass_number": 1, "type": "FBE_KEY_WIPE", "name": "Hardware Key Store & TEE Key Purge"},
                    {"pass_number": 2, "type": "EMMC_SANITIZE", "name": "eMMC/UFS Secure Erase / Trim Block Sweep"},
                ]
                desc = "NIST SP 800-88 Rev. 1 Purge: Mobile SoC hardware encryption key wipe and eMMC sanitize sequence."
                verify_pct = 100.0
            else:
                passes = [
                    {"pass_number": 1, "type": "STORAGE_OVERWRITE", "name": "User-Partition Logical Clear"}
                ]
                desc = "NIST SP 800-88 Rev. 1 Clear: Logical overwrite of accessible storage partitions."
                verify_pct = 15.0

        elif media_type in (MediaType.USB_FLASH, MediaType.SD_CARD):
            passes = [
                {"pass_number": 1, "type": "FULL_OVERWRITE", "name": "Single-Pass Binary Zero Overwrite"}
            ]
            desc = "NIST SP 800-88 Rev. 1 Clear: Full sequential overwrite of removable flash media."
            verify_pct = 25.0

        else:
            passes = [
                {"pass_number": 1, "type": "STANDARD_CLEAR", "name": "Generic NIST Clear Overwrite"}
            ]
            desc = "NIST SP 800-88 Rev. 1 Clear: Standard media sanitization procedure."
            verify_pct = 10.0

        return WipePlan(
            method=method,
            nist_category=NISTCategory.PURGE if is_purge else NISTCategory.CLEAR,
            method_name="NIST SP 800-88 Rev. 1 Purge" if is_purge else "NIST SP 800-88 Rev. 1 Clear",
            passes=passes,
            hidden_area_check=True,
            verification_sample_pct=verify_pct,
            description=desc,
        )
