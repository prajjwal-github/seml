"""Read-only hardware and model detection for macOS via system_profiler."""

import subprocess
from typing import Any, Dict


def parse_system_profiler_output(text: str) -> Dict[str, str]:
    """Parses key-value pairs from macOS system_profiler SPHardwareDataType."""
    data = {}
    for line in text.splitlines():
        line = line.strip()
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip()
            val = parts[1].strip()
            data[key] = val
    return data


def detect_macos_host() -> Dict[str, Any]:
    """Executes read-only system_profiler SPHardwareDataType on macOS."""
    model_name = "Mac"
    model_id = ""
    serial = "UNKNOWN-SERIAL"

    try:
        proc = subprocess.run(
            ["system_profiler", "SPHardwareDataType"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            parsed = parse_system_profiler_output(proc.stdout)
            model_name = parsed.get("Model Name", "Mac")
            model_id = parsed.get("Model Identifier", "")
            serial = parsed.get("Serial Number (system)", "UNKNOWN-SERIAL")
    except Exception:
        pass

    # Classify category
    lower_model = model_name.lower()
    if "macbook" in lower_model:
        category = "LAPTOP"
    elif "imac" in lower_model:
        category = "ALL_IN_ONE"
    elif "mac pro" in lower_model or "mac studio" in lower_model:
        category = "WORKSTATION"
    elif "mac mini" in lower_model:
        category = "DESKTOP"
    else:
        category = "DESKTOP"

    return {
        "category": category,
        "confidence": 0.95,
        "manufacturer": "Apple Inc.",
        "model": model_name + (f" ({model_id})" if model_id else ""),
        "serial_number": serial,
        "os_name": "macOS",
        "os_version": "Darwin",
        "arch": "arm64",
        "bios_vendor": "Apple",
        "bios_version": "iBoot",
        "boot_mode": "UEFI",
        "detected_by": "wipe-agent-macos",
        "specs": {"model_identifier": model_id},
    }
