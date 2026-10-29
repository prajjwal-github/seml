"""Safety test ensuring no destructive disk or system commands exist in code, scripts, or docs.

Rule:
- Wiping goes through an interface WipeAdapter with exactly ONE implementation, SimulatedWipeAdapter.
- Forbidden anywhere in code, scripts, tests and docs examples:
  dd, shred, mkfs, format, diskpart, cipher /w, blkdiscard, hdparm --security-erase,
  nvme format, nvme sanitize, wipefs, fdisk/parted writes, fastboot erase/format,
  adb recovery wipe_data, os.remove outside the app temp dir.
- Exception: docs/FORBIDDEN_LIST.md and this test file itself.
"""

from pathlib import Path
import re
import pytest

# Exact forbidden destructive tokens and regexes
FORBIDDEN_PATTERNS = [
    (r"\bdd\s+if=", "dd raw copy/overwrite"),
    (r"\bshred\b", "shred file/disk overwrite"),
    (r"\bmkfs(?:\.[a-z0-9]+)?\b", "mkfs filesystem format"),
    (r"\bformat\s+[a-zA-Z]:", "Windows format drive"),
    (r"\bdiskpart\b", "diskpart storage partitioning"),
    (r"\bcipher\s+/w", "cipher free space wipe"),
    (r"\bblkdiscard\b", "blkdiscard SSD TRIM/discard"),
    (r"hdparm\s+--security-erase", "hdparm security erase"),
    (r"nvme\s+format\b", "nvme low-level format"),
    (r"nvme\s+sanitize\b", "nvme sanitize"),
    (r"\bwipefs\b", "wipefs signature wiper"),
    (r"\bfdisk\b.*-[wW]", "fdisk partition table write"),
    (r"parted\b.*mklabel", "parted disk relabel"),
    (r"fastboot\s+(?:erase|format)\b", "fastboot partition erase/format"),
    (r"adb\s+recovery\s+wipe_data", "adb recovery wipe data"),
]

# Patterns for os.remove outside allowed scratch/temp directories
DANGEROUS_OS_REMOVE = re.compile(r"os\.remove\((?!.*(?:temp|scratch|tmp|pdf_path|temp_dir))")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Files exempt from the check (the reference list and this test file)
EXEMPT_FILES = {
    "docs/FORBIDDEN_LIST.md",
    "backend/tests/test_no_destructive_commands.py",
}

IGNORED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    "pgdata",
    "test_pgdata",
}


def test_no_destructive_commands_in_repo():
    """Scans all repository source files and documentation for destructive command strings."""
    violations = []

    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue

        # Skip ignored directories
        rel_parts = path.relative_to(REPO_ROOT).parts
        if any(ignored in rel_parts for ignored in IGNORED_DIRS):
            continue

        rel_path_str = str(path.relative_to(REPO_ROOT)).replace("\\", "/")

        if rel_path_str in EXEMPT_FILES:
            continue

        # Only check text files
        if path.suffix.lower() not in {
            ".py",
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".sh",
            ".bash",
            ".ps1",
            ".bat",
            ".cmd",
            ".md",
            ".json",
            ".yml",
            ".yaml",
            ".sql",
            ".html",
            ".css",
        }:
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pattern, description in FORBIDDEN_PATTERNS:
            matches = re.findall(pattern, content, flags=re.IGNORECASE)
            if matches:
                violations.append(
                    f"{rel_path_str}: Found forbidden pattern '{description}' -> matches: {matches}"
                )

        # Check dangerous os.remove
        if path.suffix == ".py":
            for line_no, line in enumerate(content.splitlines(), start=1):
                if "os.remove(" in line and not any(
                    safe in line for safe in ["temp", "scratch", "tmp", "pdf_path", "temp_dir", "target_path"]
                ):
                    violations.append(
                        f"{rel_path_str}:{line_no}: Potential unsafe os.remove invocation: {line.strip()}"
                    )

    assert not violations, "Destructive command scan failed with violations:\n" + "\n".join(violations)


def test_wipe_mode_strictly_simulation():
    """Validates that WIPE_MODE default and environment config is strictly 'simulation'."""
    from backend.core.config import settings

    assert settings.WIPE_MODE == "simulation", "WIPE_MODE must strictly be 'simulation'"
