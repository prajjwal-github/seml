"""Enumerations used across the platform models, schemas, and services."""

from enum import Enum


class UserRole(str, Enum):
    OPERATOR = "OPERATOR"
    APPROVER = "APPROVER"
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"


class DeviceCategory(str, Enum):
    LAPTOP = "LAPTOP"
    DESKTOP = "DESKTOP"
    WORKSTATION = "WORKSTATION"
    SERVER = "SERVER"
    PHONE = "PHONE"
    TABLET = "TABLET"
    ALL_IN_ONE = "ALL_IN_ONE"
    SMART_TV = "SMART_TV"
    SINGLE_BOARD_COMPUTER = "SINGLE_BOARD_COMPUTER"
    EXTERNAL_DRIVE = "EXTERNAL_DRIVE"
    USB_FLASH = "USB_FLASH"
    SD_CARD = "SD_CARD"
    NETWORK_DEVICE = "NETWORK_DEVICE"
    OTHER = "OTHER"


class DeviceStatus(str, Enum):
    ONLINE = "ONLINE"
    STALE = "STALE"
    OFFLINE = "OFFLINE"


class MediaType(str, Enum):
    HDD = "HDD"
    SATA_SSD = "SATA_SSD"
    NVME_SSD = "NVME_SSD"
    EMMC = "EMMC"
    UFS = "UFS"
    USB_FLASH = "USB_FLASH"
    SD_CARD = "SD_CARD"
    OTHER = "OTHER"


class EncryptionStatus(str, Enum):
    NONE = "NONE"
    BITLOCKER = "BITLOCKER"
    LUKS = "LUKS"
    FILEVAULT = "FILEVAULT"
    ANDROID_FBE = "ANDROID_FBE"
    UNKNOWN = "UNKNOWN"


class WipeMethod(str, Enum):
    NIST_800_88_CLEAR = "NIST_800_88_CLEAR"
    NIST_800_88_PURGE = "NIST_800_88_PURGE"


class NISTCategory(str, Enum):
    CLEAR = "CLEAR"
    PURGE = "PURGE"


class RequestStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ApprovalDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
