# Forbidden Destructive Commands Reference (FORBIDDEN_LIST.md)

> [!CAUTION]
> This platform strictly operates in **SIMULATION MODE** (`WIPE_MODE=simulation`). Under no circumstances may any code, test, script, or documentation example contain or execute real destructive disk, volume, filesystem, or flash memory operations.

The following commands, binaries, utility flags, and destructive file system operations are strictly forbidden across the entire repository. A dedicated CI test (`backend/tests/test_no_destructive_commands.py`) scans all repository files and immediately fails if any of these tokens appear outside of this reference file:

1. `dd` (direct disk write / overwrite)
2. `shred` (filesystem overwrite utility)
3. `mkfs` (filesystem creation / formatting)
4. `format` (disk / volume formatting)
5. `diskpart` (Windows disk partition utility)
6. `cipher /w` (Windows free space wiping)
7. `blkdiscard` (block device discard / TRIM)
8. `hdparm --security-erase` (ATA secure erase command)
9. `nvme format` (NVMe low-level format)
10. `nvme sanitize` (NVMe block/crypto sanitize)
11. `wipefs` (filesystem signature wiper)
12. `fdisk` / `parted` writes (partition table mutation)
13. `fastboot erase` / `fastboot format` (mobile bootloader partition wiping)
14. `adb recovery wipe_data` (Android recovery data wiping)
15. `os.remove` outside designated temporary directory paths

### Safe Alternative: Simulation Engine
All data sanitization and asset clearing workflows must interface solely through `SimulatedWipeAdapter`. The simulation adapter:
- Sleeps between progress intervals to simulate real pass execution.
- Emits real-time progress events (`pass 1/3`, `37%`...) over WebSockets.
- Writes structured status, logs, and audit entries to the PostgreSQL database.
- Strictly never touches any raw block devices, physical storage interfaces, or files outside the application's local scratch storage directory.
