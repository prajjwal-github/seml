"""Unit tests for cross-platform detection agent using recorded fixtures."""

import json
from pathlib import Path
import pytest
from agent.wipe_agent.detect.android import (
    calculate_smallest_width_dp,
    classify_android_device,
    detect_android_device_from_strings,
    parse_getprop_output,
)
from agent.wipe_agent.detect.chassis import classify_from_smbios_chassis, classify_with_fallbacks
from agent.wipe_agent.detect.linux import detect_linux_host
from agent.wipe_agent.detect.macos import parse_system_profiler_output


def test_smbios_chassis_mapping():
    """Validates standard SMBIOS enclosure code mapping."""
    # Laptops: 8, 9, 10, 14
    for code in [8, 9, 10, 14]:
        cat, conf = classify_from_smbios_chassis(code)
        assert cat == "LAPTOP"
        assert conf > 0.9

    # Desktops: 3, 4, 5, 6, 7
    for code in [3, 4, 5, 6, 7]:
        cat, conf = classify_from_smbios_chassis(code)
        assert cat == "DESKTOP"
        assert conf > 0.9

    # Servers: 17, 23, 28
    for code in [17, 23, 28]:
        cat, conf = classify_from_smbios_chassis(code)
        assert cat == "SERVER"
        assert conf > 0.9

    # Tablets: 30
    cat, conf = classify_from_smbios_chassis(30)
    assert cat == "TABLET"


def test_fallback_heuristics():
    """Validates fallback heuristics for SBCs, workstations, and battery presence."""
    # Raspberry Pi ARM SBC
    cat, conf = classify_with_fallbacks(chassis_code=None, is_arm_sbc=True, model_name="Raspberry Pi 4 Model B")
    assert cat == "SINGLE_BOARD_COMPUTER"
    assert conf > 0.9

    # Workstation
    cat, conf = classify_with_fallbacks(chassis_code=7, model_name="Dell Precision 5820 Tower")
    assert cat == "WORKSTATION"

    # Battery fallback without chassis code
    cat, conf = classify_with_fallbacks(chassis_code=None, has_battery=True, model_name="Generic Machine")
    assert cat == "LAPTOP"
    assert conf >= 0.8


def test_linux_dmi_fixtures(tmp_path):
    """Simulates reading Linux sysfs DMI directory fixtures."""
    dmi_dir = tmp_path / "dmi"
    dmi_dir.mkdir()

    (dmi_dir / "sys_vendor").write_text("LENOVO\n")
    (dmi_dir / "product_name").write_text("ThinkPad T14 Gen 4\n")
    (dmi_dir / "product_serial").write_text("PF4X99ZZ\n")
    (dmi_dir / "chassis_type").write_text("10\n")  # Notebook
    (dmi_dir / "bios_vendor").write_text("LENOVO\n")
    (dmi_dir / "bios_version").write_text("N3MET05W\n")

    info = detect_linux_host(dmi_root=str(dmi_dir))
    assert info["category"] == "LAPTOP"
    assert info["manufacturer"] == "LENOVO"
    assert "ThinkPad" in info["model"]
    assert info["serial_number"] == "PF4X99ZZ"
    assert info["confidence"] > 0.9


def test_macos_system_profiler_parsing():
    """Validates parsing of macOS system_profiler SPHardwareDataType dump."""
    dump = """
Hardware:

    Hardware Overview:

      Model Name: MacBook Pro
      Model Identifier: Mac14,6
      Model Number: Z174000FTLL/A
      Chip: Apple M2 Max
      Total Number of Cores: 12 (8 performance and 4 efficiency)
      Memory: 64 GB
      System Firmware Version: 10151.101.3
      OS Loader Version: 10151.101.3
      Serial Number (system): C02G99ZZMD6R
      Hardware UUID: 7B5542E5-7AEB-5E4E-A54C-38A246B4E542
    """
    parsed = parse_system_profiler_output(dump)
    assert parsed["Model Name"] == "MacBook Pro"
    assert parsed["Model Identifier"] == "Mac14,6"
    assert parsed["Serial Number (system)"] == "C02G99ZZMD6R"


def test_android_adb_getprop_and_tablet_classification():
    """Validates Android phone vs tablet detection using getprop and window manager density."""
    phone_dump = """
[ro.product.manufacturer]: [Google]
[ro.product.model]: [Pixel 8]
[ro.product.device]: [shiba]
[ro.build.version.release]: [15]
[ro.build.characteristics]: [default]
[ro.product.cpu.abi]: [arm64-v8a]
[ro.serialno]: [38141FDDA0009Z]
"""
    # Phone screen: 1080x2400 at 440 dpi -> 1080 * 160 / 440 = 392 dp (< 600 dp)
    phone_info = detect_android_device_from_strings(
        getprop_text=phone_dump,
        wm_size_text="Physical size: 1080x2400",
        wm_density_text="Physical density: 440",
    )
    assert phone_info["category"] == "PHONE"
    assert phone_info["manufacturer"] == "Google"
    assert phone_info["model"] == "Pixel 8"
    assert phone_info["serial_number"] == "38141FDDA0009Z"

    tablet_dump = """
[ro.product.manufacturer]: [samsung]
[ro.product.model]: [Galaxy Tab S9]
[ro.product.device]: [gts9]
[ro.build.version.release]: [14]
[ro.build.characteristics]: [tablet]
[ro.product.cpu.abi]: [arm64-v8a]
[ro.serialno]: [R52W800ZZZZ]
"""
    # Tablet screen: 1600x2560 at 280 dpi -> 1600 * 160 / 280 = 914 dp (>= 600 dp)
    tablet_info = detect_android_device_from_strings(
        getprop_text=tablet_dump,
        wm_size_text="Physical size: 1600x2560",
        wm_density_text="Physical density: 280",
    )
    assert tablet_info["category"] == "TABLET"
    assert tablet_info["manufacturer"] == "samsung"
    assert tablet_info["model"] == "Galaxy Tab S9"
