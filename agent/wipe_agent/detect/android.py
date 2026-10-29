"""Read-only Android mobile and tablet inspection via ADB."""

import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple


def parse_getprop_output(output: str) -> Dict[str, str]:
    """Parses standard ADB getprop output format: [key]: [value]."""
    props = {}
    pattern = re.compile(r"\[(.*?)\]:\s*\[(.*?)\]")
    for line in output.splitlines():
        match = pattern.search(line)
        if match:
            props[match.group(1)] = match.group(2)
    return props


def calculate_smallest_width_dp(size_str: str, density_str: str) -> Optional[int]:
    """Calculates smallest screen width in dp from 'wm size' and 'wm density'."""
    # wm size: Physical size: 1080x2400 or 1600x2560
    # wm density: Physical density: 440
    size_match = re.search(r"(\d+)\s*x\s*(\d+)", size_str)
    density_match = re.search(r"(\d+)", density_str)

    if size_match and density_match:
        w = int(size_match.group(1))
        h = int(size_match.group(2))
        density = int(density_match.group(1))
        if density > 0:
            smallest_px = min(w, h)
            smallest_dp = int(smallest_px * 160 / density)
            return smallest_dp
    return None


def classify_android_device(
    characteristics: str,
    smallest_width_dp: Optional[int] = None,
) -> Tuple[str, float]:
    """Classifies an Android device as TABLET or PHONE."""
    if "tablet" in characteristics.lower():
        return "TABLET", 0.95

    if smallest_width_dp is not None:
        if smallest_width_dp >= 600:
            return "TABLET", 0.92
        else:
            return "PHONE", 0.95

    return "PHONE", 0.85


def detect_android_device_from_strings(
    getprop_text: str,
    wm_size_text: str = "",
    wm_density_text: str = "",
    serial_str: str = "",
) -> Dict[str, Any]:
    """Parses recorded Android getprop and wm dumps into a normalized device profile."""
    props = parse_getprop_output(getprop_text)

    manufacturer = props.get("ro.product.manufacturer", "Android OEM")
    model = props.get("ro.product.model", "Android Device")
    release = props.get("ro.build.version.release", "Android")
    characteristics = props.get("ro.build.characteristics", "")
    serial = serial_str or props.get("ro.serialno") or "SERIAL-UNKNOWN"

    sw_dp = calculate_smallest_width_dp(wm_size_text, wm_density_text)
    category, confidence = classify_android_device(characteristics, sw_dp)

    return {
        "category": category,
        "confidence": confidence,
        "manufacturer": manufacturer,
        "model": model,
        "serial_number": serial,
        "os_name": "Android",
        "os_version": f"Android {release}",
        "arch": props.get("ro.product.cpu.abi", "arm64-v8a"),
        "boot_mode": "Android Bootloader",
        "detected_by": "wipe-agent-adb",
        "specs": {
            "characteristics": characteristics,
            "smallest_width_dp": sw_dp,
            "device_codename": props.get("ro.product.device"),
        },
    }
