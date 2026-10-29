"""SMBIOS chassis code mapping and device category classification heuristics."""

from typing import Optional, Tuple

# Mapping of SMBIOS 3.x System Enclosure or Chassis Types to DeviceCategory string
# Standard SMBIOS chassis types:
# 1: Other, 2: Unknown
# 3: Desktop, 4: Low Profile Desktop, 5: Pizza Box, 6: Mini Tower, 7: Tower
# 8: Portable, 9: Laptop, 10: Notebook, 14: Sub Notebook
# 11: Hand Held, 12: Docking Station, 13: All in One
# 17: Main Server Chassis, 23: Rack Mount Chassis, 28: Blade
# 30: Tablet, 31: Convertible, 32: Detachable
SMBIOS_CHASSIS_MAP = {
    3: "DESKTOP",
    4: "DESKTOP",
    5: "DESKTOP",
    6: "DESKTOP",
    7: "DESKTOP",
    8: "LAPTOP",
    9: "LAPTOP",
    10: "LAPTOP",
    14: "LAPTOP",
    31: "LAPTOP",  # Convertible
    32: "LAPTOP",  # Detachable
    11: "PHONE",
    13: "ALL_IN_ONE",
    17: "SERVER",
    23: "SERVER",
    28: "SERVER",
    30: "TABLET",
}


def classify_from_smbios_chassis(chassis_code: Optional[int]) -> Tuple[str, float]:
    """Maps SMBIOS chassis integer code to category with confidence level."""
    if chassis_code is None:
        return "OTHER", 0.3
    category = SMBIOS_CHASSIS_MAP.get(chassis_code)
    if category:
        return category, 0.95
    return "OTHER", 0.4


def classify_with_fallbacks(
    chassis_code: Optional[int],
    has_battery: bool = False,
    is_arm_sbc: bool = False,
    is_vm_or_hypervisor: bool = False,
    model_name: str = "",
) -> Tuple[str, float]:
    """Applies fallback heuristics when SMBIOS chassis code is ambiguous or generic."""
    # Check SBC models first (Raspberry Pi, Orange Pi, BeagleBone)
    model_lower = model_name.lower()
    if is_arm_sbc or any(sbc in model_lower for sbc in ["raspberry pi", "orangepi", "khadas", "jetson"]):
        return "SINGLE_BOARD_COMPUTER", 0.98

    # Workstation keywords
    if any(ws in model_lower for ws in ["precision", "thinkstation", "zbook", "z2", "z4", "z6", "z8"]):
        if has_battery or "book" in model_lower:
            return "LAPTOP", 0.9
        return "WORKSTATION", 0.9

    # Server keywords
    if is_vm_or_hypervisor or any(srv in model_lower for srv in ["proliant", "poweredge", "primergy", "ucs"]):
        return "SERVER", 0.95

    # Check SMBIOS chassis mapping
    if chassis_code in SMBIOS_CHASSIS_MAP:
        return SMBIOS_CHASSIS_MAP[chassis_code], 0.92

    # Battery fallback heuristic
    if has_battery:
        return "LAPTOP", 0.8

    return "DESKTOP", 0.6
