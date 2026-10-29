"""Cross-platform hardware detection coordinator."""

import platform
from typing import Any, Dict
from agent.wipe_agent.detect.linux import detect_linux_host
from agent.wipe_agent.detect.macos import detect_macos_host
from agent.wipe_agent.detect.storage import detect_local_storage_volumes
from agent.wipe_agent.detect.windows import detect_windows_host


def detect_host_device() -> Dict[str, Any]:
    """Inspects the local host machine in read-only mode and aggregates device identity & storage inventory."""
    sys_name = platform.system().lower()

    if sys_name == "windows":
        device_info = detect_windows_host()
    elif sys_name == "linux":
        device_info = detect_linux_host()
    elif sys_name == "darwin":
        device_info = detect_macos_host()
    else:
        device_info = {
            "category": "OTHER",
            "confidence": 0.5,
            "manufacturer": "Generic",
            "model": "Generic Host",
            "serial_number": "GENERIC-SERIAL",
            "os_name": platform.system(),
            "os_version": platform.release(),
            "arch": platform.machine(),
            "boot_mode": "UEFI",
            "detected_by": "wipe-agent-generic",
            "specs": {},
        }

    # Discover storage volumes
    volumes = detect_local_storage_volumes()
    device_info["volumes"] = volumes

    return device_info
