"""Database seed script creating 3 default users (Admin, Operator, Approver) and 16 realistic devices across all 14 categories."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.certs.generator import generate_certificate
from backend.core.audit import log_audit_event
from backend.core.database import AsyncSessionLocal
from backend.core.init_db import init_database
from backend.core.security import compute_request_fingerprint, hash_password, sha256_hex
from backend.models import (
    Approval,
    ApprovalDecision,
    Device,
    DeviceCategory,
    DeviceStatus,
    EncryptionStatus,
    JobStatus,
    MediaType,
    NISTCategory,
    Organization,
    RequestStatus,
    RiskLevel,
    StorageVolume,
    User,
    UserRole,
    WipeJob,
    WipeMethod,
    WipeRequest,
)

USERS_SEED = [
    {
        "email": "operator@securewipe.local",
        "name": "Alex Vance (Operator)",
        "password": "Operator123!",
        "role": UserRole.OPERATOR,
    },
    {
        "email": "approver@securewipe.local",
        "name": "Sarah Connor (Approving Authority)",
        "password": "Approver123!",
        "role": UserRole.APPROVER,
    },
    {
        "email": "admin@securewipe.local",
        "name": "Marcus Wright (Asset Administrator)",
        "password": "Admin123!",
        "role": UserRole.ADMIN,
    },
]

DEVICES_SEED = [
    # 1. LAPTOP
    {
        "category": DeviceCategory.LAPTOP,
        "manufacturer": "Lenovo",
        "model": "ThinkPad T14 Gen 4",
        "serial": "PF4X9012",
        "os_name": "Windows",
        "os_version": "Windows 11 Pro 23H2",
        "arch": "x86_64",
        "status": DeviceStatus.ONLINE,
        "confidence": 0.98,
        "detected_by": "wipe-agent-windows",
        "volumes": [
            {
                "name": "NVMe Samsung PM9A1 512GB",
                "mount": "C:",
                "size_gb": 512,
                "media": MediaType.NVME_SSD,
                "bus": "PCIe 4.0 x4",
                "boot": True,
                "system": True,
                "enc": EncryptionStatus.BITLOCKER,
            }
        ],
    },
    # 2. LAPTOP
    {
        "category": DeviceCategory.LAPTOP,
        "manufacturer": "Apple",
        "model": "MacBook Air M2 (15-inch)",
        "serial": "C02KJ908MD6R",
        "os_name": "macOS",
        "os_version": "Sonoma 14.5",
        "arch": "arm64",
        "status": DeviceStatus.ONLINE,
        "confidence": 0.96,
        "detected_by": "wipe-agent-macos",
        "volumes": [
            {
                "name": "Apple Fabric SSD 512GB",
                "mount": "/",
                "size_gb": 512,
                "media": MediaType.NVME_SSD,
                "bus": "Internal Fabric",
                "boot": True,
                "system": True,
                "enc": EncryptionStatus.FILEVAULT,
            }
        ],
    },
    # 3. DESKTOP
    {
        "category": DeviceCategory.DESKTOP,
        "manufacturer": "Dell",
        "model": "OptiPlex 7090 Micro",
        "serial": "7X98102B",
        "os_name": "Ubuntu",
        "os_version": "Ubuntu 24.04 LTS",
        "arch": "x86_64",
        "status": DeviceStatus.ONLINE,
        "confidence": 0.95,
        "detected_by": "wipe-agent-linux",
        "volumes": [
            {
                "name": "Kioxia BG4 NVMe 256GB",
                "mount": "/",
                "size_gb": 256,
                "media": MediaType.NVME_SSD,
                "bus": "NVMe",
                "boot": True,
                "system": True,
                "enc": EncryptionStatus.LUKS,
            },
            {
                "name": "Seagate Barracuda 1TB HDD",
                "mount": "/data",
                "size_gb": 1000,
                "media": MediaType.HDD,
                "bus": "SATA",
                "boot": False,
                "system": False,
                "enc": EncryptionStatus.NONE,
            },
        ],
    },
    # 4. WORKSTATION
    {
        "category": DeviceCategory.WORKSTATION,
        "manufacturer": "Dell",
        "model": "Precision 5820 Tower",
        "serial": "8B71004C",
        "os_name": "Windows",
        "os_version": "Windows 11 Enterprise",
        "arch": "x86_64",
        "status": DeviceStatus.ONLINE,
        "confidence": 0.94,
        "detected_by": "wipe-agent-windows",
        "volumes": [
            {
                "name": "Micron 7450 PRO 1.92TB NVMe",
                "mount": "C:",
                "size_gb": 1920,
                "media": MediaType.NVME_SSD,
                "bus": "NVMe",
                "boot": True,
                "system": True,
                "enc": EncryptionStatus.BITLOCKER,
            },
            {
                "name": "WD Gold 8TB Enterprise HDD",
                "mount": "D:",
                "size_gb": 8000,
                "media": MediaType.HDD,
                "bus": "SATA",
                "boot": False,
                "system": False,
                "enc": EncryptionStatus.NONE,
            },
        ],
    },
    # 5. SERVER
    {
        "category": DeviceCategory.SERVER,
        "manufacturer": "HP",
        "model": "ProLiant DL380 Gen10",
        "serial": "CZ29188001",
        "os_name": "RHEL",
        "os_version": "Red Hat Enterprise Linux 9.3",
        "arch": "x86_64",
        "status": DeviceStatus.ONLINE,
        "confidence": 0.99,
        "detected_by": "wipe-agent-linux",
        "volumes": [
            {
                "name": "HPE Smart Array P408i-a RAID 1 (2x 480GB SSD)",
                "mount": "/",
                "size_gb": 480,
                "media": MediaType.SATA_SSD,
                "bus": "SAS/SATA",
                "boot": True,
                "system": True,
                "enc": EncryptionStatus.LUKS,
            },
            {
                "name": "HPE 2.4TB 10K SAS Enterprise HDD Array",
                "mount": "/var/lib/data",
                "size_gb": 9600,
                "media": MediaType.HDD,
                "bus": "SAS",
                "boot": False,
                "system": False,
                "enc": EncryptionStatus.NONE,
            },
        ],
    },
    # 6. PHONE
    {
        "category": DeviceCategory.PHONE,
        "manufacturer": "Samsung",
        "model": "Galaxy S23 Ultra",
        "serial": "R5CW1088ZZZ",
        "os_name": "Android",
        "os_version": "Android 14 (One UI 6.1)",
        "arch": "arm64-v8a",
        "status": DeviceStatus.ONLINE,
        "confidence": 0.95,
        "detected_by": "wipe-agent-adb",
        "volumes": [
            {
                "name": "Samsung UFS 4.0 Internal Flash 512GB",
                "mount": "/data",
                "size_gb": 512,
                "media": MediaType.UFS,
                "bus": "UFS",
                "boot": True,
                "system": True,
                "enc": EncryptionStatus.ANDROID_FBE,
            }
        ],
    },
    # 7. PHONE
    {
        "category": DeviceCategory.PHONE,
        "manufacturer": "Google",
        "model": "Pixel 8 Pro",
        "serial": "38141FDDA0011B",
        "os_name": "Android",
        "os_version": "Android 15 (AP2A)",
        "arch": "arm64-v8a",
        "status": DeviceStatus.ONLINE,
        "confidence": 0.95,
        "detected_by": "wipe-agent-adb",
        "volumes": [
            {
                "name": "UFS 3.1 Flash Storage 256GB",
                "mount": "/data",
                "size_gb": 256,
                "media": MediaType.UFS,
                "bus": "UFS",
                "boot": True,
                "system": True,
                "enc": EncryptionStatus.ANDROID_FBE,
            }
        ],
    },
    # 8. TABLET
    {
        "category": DeviceCategory.TABLET,
        "manufacturer": "Apple",
        "model": "iPad 10th Gen (Wi-Fi)",
        "serial": "DMPF8012Q16R",
        "os_name": "iPadOS",
        "os_version": "iPadOS 17.5",
        "arch": "arm64",
        "status": DeviceStatus.ONLINE,
        "confidence": 0.94,
        "detected_by": "manual",
        "volumes": [
            {
                "name": "Apple NVMe Flash 64GB",
                "mount": "/",
                "size_gb": 64,
                "media": MediaType.NVME_SSD,
                "bus": "PCIe",
                "boot": True,
                "system": True,
                "enc": EncryptionStatus.FILEVAULT,
            }
        ],
    },
    # 9. TABLET
    {
        "category": DeviceCategory.TABLET,
        "manufacturer": "Samsung",
        "model": "Galaxy Tab S9 FE",
        "serial": "R52W810444A",
        "os_name": "Android",
        "os_version": "Android 14",
        "arch": "arm64-v8a",
        "status": DeviceStatus.ONLINE,
        "confidence": 0.93,
        "detected_by": "wipe-agent-adb",
        "volumes": [
            {
                "name": "eMMC 5.1 Storage 128GB",
                "mount": "/data",
                "size_gb": 128,
                "media": MediaType.EMMC,
                "bus": "eMMC",
                "boot": True,
                "system": True,
                "enc": EncryptionStatus.ANDROID_FBE,
            }
        ],
    },
    # 10. ALL_IN_ONE
    {
        "category": DeviceCategory.ALL_IN_ONE,
        "manufacturer": "HP",
        "model": "EliteOne 800 G6 All-in-One",
        "serial": "8CG10900XX",
        "os_name": "Windows",
        "os_version": "Windows 11 Pro",
        "arch": "x86_64",
        "status": DeviceStatus.ONLINE,
        "confidence": 0.95,
        "detected_by": "wipe-agent-windows",
        "volumes": [
            {
                "name": "SK Hynix PC711 NVMe 512GB",
                "mount": "C:",
                "size_gb": 512,
                "media": MediaType.NVME_SSD,
                "bus": "NVMe",
                "boot": True,
                "system": True,
                "enc": EncryptionStatus.BITLOCKER,
            }
        ],
    },
    # 11. SMART_TV
    {
        "category": DeviceCategory.SMART_TV,
        "manufacturer": "Sony",
        "model": "BRAVIA 4K Android TV (XR-65X90L)",
        "serial": "SNY-TV-401928",
        "os_name": "Google TV",
        "os_version": "Android 12 for TV",
        "arch": "arm64",
        "status": DeviceStatus.ONLINE,
        "confidence": 0.9,
        "detected_by": "manual",
        "volumes": [
            {
                "name": "Embedded eMMC Flash 32GB",
                "mount": "/data",
                "size_gb": 32,
                "media": MediaType.EMMC,
                "bus": "eMMC",
                "boot": True,
                "system": True,
                "enc": EncryptionStatus.NONE,
            }
        ],
    },
    # 12. SINGLE_BOARD_COMPUTER
    {
        "category": DeviceCategory.SINGLE_BOARD_COMPUTER,
        "manufacturer": "Raspberry Pi Ltd",
        "model": "Raspberry Pi 4 Model B (8GB)",
        "serial": "10000000a9821f04",
        "os_name": "Debian",
        "os_version": "Raspberry Pi OS 12 (Bookworm)",
        "arch": "aarch64",
        "status": DeviceStatus.ONLINE,
        "confidence": 0.98,
        "detected_by": "wipe-agent-linux",
        "volumes": [
            {
                "name": "SanDisk Extreme Pro MicroSD 128GB",
                "mount": "/",
                "size_gb": 128,
                "media": MediaType.SD_CARD,
                "bus": "SDIO",
                "boot": True,
                "system": True,
                "enc": EncryptionStatus.NONE,
            }
        ],
    },
    # 13. EXTERNAL_DRIVE
    {
        "category": DeviceCategory.EXTERNAL_DRIVE,
        "manufacturer": "Western Digital",
        "model": "WD My Passport 4TB External HDD",
        "serial": "WXE1A8109982",
        "os_name": "Embedded Controller",
        "os_version": "USB Mass Storage v1.0",
        "arch": "N/A",
        "status": DeviceStatus.ONLINE,
        "confidence": 0.95,
        "detected_by": "manual",
        "volumes": [
            {
                "name": "WD Elements 4TB NTFS Volume",
                "mount": "E:",
                "size_gb": 4000,
                "media": MediaType.HDD,
                "bus": "USB 3.0",
                "boot": False,
                "system": False,
                "enc": EncryptionStatus.NONE,
            }
        ],
    },
    # 14. USB_FLASH
    {
        "category": DeviceCategory.USB_FLASH,
        "manufacturer": "SanDisk",
        "model": "Ultra Flair USB 3.0 128GB",
        "serial": "SDCZ73-128G-0912",
        "os_name": "N/A",
        "os_version": "USB Mass Storage",
        "arch": "N/A",
        "status": DeviceStatus.ONLINE,
        "confidence": 0.95,
        "detected_by": "manual",
        "volumes": [
            {
                "name": "SanDisk FAT32 Removable Drive",
                "mount": "F:",
                "size_gb": 128,
                "media": MediaType.USB_FLASH,
                "bus": "USB",
                "boot": False,
                "system": False,
                "enc": EncryptionStatus.NONE,
            }
        ],
    },
    # 15. SD_CARD
    {
        "category": DeviceCategory.SD_CARD,
        "manufacturer": "Kingston",
        "model": "Canvas Go! Plus SDXC 256GB",
        "serial": "KG-SDXC-88129",
        "os_name": "N/A",
        "os_version": "SD Card Interface",
        "arch": "N/A",
        "status": DeviceStatus.ONLINE,
        "confidence": 0.95,
        "detected_by": "manual",
        "volumes": [
            {
                "name": "SDXC exFAT Volume",
                "mount": "G:",
                "size_gb": 256,
                "media": MediaType.SD_CARD,
                "bus": "SDIO",
                "boot": False,
                "system": False,
                "enc": EncryptionStatus.NONE,
            }
        ],
    },
    # 16. NETWORK_DEVICE
    {
        "category": DeviceCategory.NETWORK_DEVICE,
        "manufacturer": "Cisco",
        "model": "Catalyst 9300-48P Managed Switch",
        "serial": "FCW2348A0XX",
        "os_name": "Cisco IOS-XE",
        "os_version": "17.09.04a",
        "arch": "x86_64",
        "status": DeviceStatus.ONLINE,
        "confidence": 0.97,
        "detected_by": "manual",
        "volumes": [
            {
                "name": "Internal NVRAM & Boot Flash 16GB",
                "mount": "bootflash:",
                "size_gb": 16,
                "media": MediaType.EMMC,
                "bus": "Internal",
                "boot": True,
                "system": True,
                "enc": EncryptionStatus.NONE,
            }
        ],
    },
]


async def seed_database():
    """Seeds the platform with users, organizations, devices, and a sample certified wipe."""
    await init_database()

    async with AsyncSessionLocal() as session:
        # 1. Organization
        org_stmt = select(Organization).where(Organization.slug == "default-recycling")
        org = (await session.execute(org_stmt)).scalar_one_or_none()
        if not org:
            org = Organization(name="Certified Asset Recovery Inc.", slug="default-recycling")
            session.add(org)
            await session.flush()

        # 2. Users
        created_users = {}
        for u_data in USERS_SEED:
            u_stmt = select(User).where(User.email == u_data["email"])
            existing_u = (await session.execute(u_stmt)).scalar_one_or_none()
            if not existing_u:
                user = User(
                    email=u_data["email"],
                    name=u_data["name"],
                    password_hash=hash_password(u_data["password"]),
                    role=u_data["role"],
                    org_id=org.id,
                    is_active=True,
                )
                session.add(user)
                await session.flush()
                created_users[u_data["role"]] = user
            else:
                created_users[u_data["role"]] = existing_u

        # 3. Devices and Volumes
        seeded_devices = []
        for d_data in DEVICES_SEED:
            d_stmt = select(Device).where(Device.serial_number == d_data["serial"])
            existing_d = (await session.execute(d_stmt)).scalar_one_or_none()
            if not existing_d:
                device = Device(
                    category=d_data["category"],
                    manufacturer=d_data["manufacturer"],
                    model=d_data["model"],
                    serial_number=d_data["serial"],
                    os_name=d_data["os_name"],
                    os_version=d_data["os_version"],
                    arch=d_data["arch"],
                    status=d_data["status"],
                    confidence=d_data["confidence"],
                    detected_by=d_data["detected_by"],
                    specs={"seeded": True, "cores": 8, "ram_gb": 16},
                    last_seen=datetime.now(timezone.utc),
                )
                session.add(device)
                await session.flush()

                for v_info in d_data["volumes"]:
                    vol = StorageVolume(
                        device_id=device.id,
                        name=v_info["name"],
                        mount_point=v_info["mount"],
                        size_bytes=v_info["size_gb"] * 1024 * 1024 * 1024,
                        media_type=v_info["media"],
                        bus_type=v_info["bus"],
                        removable=v_info["media"] in (MediaType.USB_FLASH, MediaType.SD_CARD),
                        is_boot=v_info["boot"],
                        is_system=v_info["system"],
                        encryption_status=v_info["enc"],
                        hidden_areas={"hpa_present": False, "dco_present": False, "remapped_sectors": 0},
                        smart={"health": "PASSED", "temperature_c": 32, "power_on_hours": 850},
                    )
                    session.add(vol)

                seeded_devices.append(device)
            else:
                seeded_devices.append(existing_d)

        # 4. Seed a completed sample job and certificate for demonstration
        operator = created_users[UserRole.OPERATOR]
        approver = created_users[UserRole.APPROVER]
        sample_device = seeded_devices[0]  # ThinkPad T14

        # Check if already seeded a completed job for sample_device
        job_stmt = select(WipeJob).join(WipeRequest).where(WipeRequest.device_id == sample_device.id)
        existing_job = (await session.execute(job_stmt)).scalar_one_or_none()

        if not existing_job:
            vol_stmt = select(StorageVolume).where(StorageVolume.device_id == sample_device.id)
            sample_vols = (await session.execute(vol_stmt)).scalars().all()
            vol_ids = [v.id for v in sample_vols]

            now = datetime.now(timezone.utc)
            req = WipeRequest(
                device_id=sample_device.id,
                requested_by=operator.id,
                reason="End-of-lease corporate asset sanitization and recycling",
                method=WipeMethod.NIST_800_88_CLEAR,
                nist_category=NISTCategory.CLEAR,
                volume_ids=vol_ids,
                risk_level=RiskLevel.LOW,
                status=RequestStatus.COMPLETED,
                expires_at=now + timedelta(hours=24),
                decided_at=now - timedelta(minutes=15),
            )
            session.add(req)
            await session.flush()

            fp = compute_request_fingerprint(
                device_id=sample_device.id,
                volume_ids=vol_ids,
                method=req.method.value,
                serial_number=sample_device.serial_number,
            )

            approval = Approval(
                request_id=req.id,
                approver_id=approver.id,
                decision=ApprovalDecision.APPROVED,
                comment="Authorized for certified asset clearing per NIST SP 800-88 Rev. 1",
                request_fingerprint=fp,
                token_hash=sha256_hex(uuid.uuid4().hex),
                expires_at=now + timedelta(hours=24),
                used_at=None,
            )
            session.add(approval)
            await session.flush()

            job = WipeJob(
                request_id=req.id,
                approval_id=approval.id,
                status=JobStatus.COMPLETED,
                progress=100.0,
                current_pass=1,
                total_passes=1,
                mode="simulation",
                started_at=now - timedelta(minutes=10),
                finished_at=now - timedelta(minutes=5),
                result={
                    "mode": "simulation",
                    "verification": {
                        "verified": True,
                        "sample_percentage": 15.0,
                        "hash_verification": "ZERO_PATTERN_CONFIRMED",
                    },
                    "hidden_areas": {
                        "hpa_cleared": True,
                        "dco_cleared": True,
                        "remapped_sectors_checked": True,
                    },
                },
            )
            session.add(job)
            await session.flush()
            approval.used_at = now

            # Generate sample certificate
            cert = await generate_certificate(session, job)

            await log_audit_event(
                session=session,
                action="SEED_DATA_LOADED",
                entity_type="SYSTEM",
                entity_id="SEED",
                details={
                    "users": len(USERS_SEED),
                    "devices": len(DEVICES_SEED),
                    "sample_cert": cert.certificate_id,
                },
            )

        await session.commit()
        print(f"Successfully seeded database with {len(USERS_SEED)} users and {len(DEVICES_SEED)} devices across all categories.")


if __name__ == "__main__":
    asyncio.run(seed_database())
