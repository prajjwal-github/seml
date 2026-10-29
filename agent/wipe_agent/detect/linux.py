"""Read-only hardware, DMI, and sysfs detection on Linux systems."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from agent.wipe_agent.detect.chassis import classify_with_fallbacks


def read_sysfs_file(path_str: str) -> str:
    """Safely reads a single line from a sysfs or procfs file."""
    path = Path(path_str)
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            pass
    return ""


def detect_linux_host(dmi_root: str = "/sys/class/dmi/id") -> Dict[str, Any]:
    """Reads Linux DMI sysfs files and power supply presence without running root commands."""
    dmi = Path(dmi_root)

    sys_vendor = read_sysfs_file(str(dmi / "sys_vendor")) or "Linux Foundation"
    product_name = read_sysfs_file(str(dmi / "product_name")) or "Generic Linux Machine"
    product_serial = read_sysfs_file(str(dmi / "product_serial")) or "UNKNOWN-SERIAL"
    product_uuid = read_sysfs_file(str(dmi / "product_uuid"))

    bios_vendor = read_sysfs_file(str(dmi / "bios_vendor")) or "Unknown"
    bios_version = read_sysfs_file(str(dmi / "bios_version")) or "Unknown"

    chassis_raw = read_sysfs_file(str(dmi / "chassis_type"))
    chassis_code: Optional[int] = int(chassis_raw) if chassis_raw.isdigit() else None

    # Check battery presence in power_supply
    power_supply = Path("/sys/class/power_supply")
    has_battery = False
    if power_supply.is_dir():
        try:
            for item in power_supply.iterdir():
                type_file = item / "type"
                if type_file.is_file() and "Battery" in read_sysfs_file(str(type_file)):
                    has_battery = True
                    break
        except Exception:
            pass

    # Check ARM SBC device-tree model (e.g. Raspberry Pi)
    dt_model = read_sysfs_file("/proc/device-tree/model")
    is_arm_sbc = bool(dt_model)
    if dt_model:
        product_name = dt_model
        sys_vendor = "Raspberry Pi / ARM"

    category, confidence = classify_with_fallbacks(
        chassis_code=chassis_code,
        has_battery=has_battery,
        is_arm_sbc=is_arm_sbc,
        model_name=product_name,
    )

    # Detect boot mode
    efi_dir = Path("/sys/firmware/efi")
    boot_mode = "UEFI" if efi_dir.is_dir() else "Legacy BIOS"

    return {
        "category": category,
        "confidence": confidence,
        "manufacturer": sys_vendor,
        "model": product_name,
        "serial_number": product_serial,
        "system_uuid": product_uuid,
        "os_name": "Linux",
        "os_version": "Linux Kernel",
        "arch": os.uname().machine if hasattr(os, "uname") else "x86_64",
        "bios_vendor": bios_vendor,
        "bios_version": bios_version,
        "boot_mode": boot_mode,
        "detected_by": "wipe-agent-linux",
        "specs": {
            "chassis_code": chassis_code,
            "has_battery": has_battery,
            "device_tree_model": dt_model,
        },
    }
