"""Read-only hardware, BIOS, and chassis detection on Windows via WMI/CIM."""

import platform
import subprocess
from typing import Any, Dict, Optional
from agent.wipe_agent.detect.chassis import classify_with_fallbacks


def query_wmi_powershell(class_name: str, properties: str) -> Dict[str, str]:
    """Queries WMI class properties safely and in read-only mode using PowerShell Get-CimInstance."""
    cmd = f"Get-CimInstance -ClassName {class_name} | Select-Object -Property {properties} | ConvertTo-Json -Compress"
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            import json
            data = json.loads(proc.stdout)
            if isinstance(data, list) and data:
                return data[0]
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def detect_windows_host() -> Dict[str, Any]:
    """Collects read-only Windows host hardware identity, BIOS, and enclosure data."""
    cs = query_wmi_powershell("Win32_ComputerSystem", "Manufacturer,Model,PCSystemType,TotalPhysicalMemory")
    enc = query_wmi_powershell("Win32_SystemEnclosure", "ChassisTypes,SerialNumber,SMBIOSAssetTag")
    bios = query_wmi_powershell("Win32_BIOS", "Manufacturer,SMBIOSBIOSVersion,ReleaseDate,SerialNumber")
    os_info = query_wmi_powershell("Win32_OperatingSystem", "Caption,Version,BuildNumber,OSArchitecture")
    battery = query_wmi_powershell("Win32_Battery", "BatteryStatus")

    manufacturer = cs.get("Manufacturer", "").strip() or "Generic OEM"
    model = cs.get("Model", "").strip() or "Standard PC"
    serial = bios.get("SerialNumber", "").strip() or enc.get("SerialNumber", "").strip() or "UNKNOWN-SERIAL"

    # Extract chassis code
    chassis_types = enc.get("ChassisTypes", [])
    chassis_code: Optional[int] = None
    if isinstance(chassis_types, list) and chassis_types:
        chassis_code = int(chassis_types[0])
    elif isinstance(chassis_types, (int, str)) and str(chassis_types).isdigit():
        chassis_code = int(chassis_types)

    has_battery = bool(battery)
    category, confidence = classify_with_fallbacks(
        chassis_code=chassis_code,
        has_battery=has_battery,
        model_name=model,
    )

    return {
        "category": category,
        "confidence": confidence,
        "manufacturer": manufacturer,
        "model": model,
        "serial_number": serial,
        "system_uuid": bios.get("SerialNumber", ""),
        "os_name": "Windows",
        "os_version": os_info.get("Caption", platform.system() + " " + platform.release()),
        "os_build": os_info.get("BuildNumber", platform.version()),
        "arch": platform.machine(),
        "bios_vendor": bios.get("Manufacturer", "Unknown"),
        "bios_version": bios.get("SMBIOSBIOSVersion", "Unknown"),
        "boot_mode": "UEFI",
        "detected_by": "wipe-agent-windows",
        "specs": {
            "chassis_code": chassis_code,
            "has_battery": has_battery,
            "pc_system_type": cs.get("PCSystemType"),
        },
    }
