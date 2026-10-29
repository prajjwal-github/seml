"""Pydantic v2 schemas for devices and storage volumes."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.models.enums import DeviceCategory, DeviceStatus, EncryptionStatus, MediaType


class StorageVolumeBase(BaseModel):
    name: str
    mount_point: Optional[str] = None
    size_bytes: int = 0
    media_type: MediaType = MediaType.HDD
    bus_type: str = "SATA"
    removable: bool = False
    partition_table: str = "GPT"
    is_boot: bool = False
    is_system: bool = False
    encryption_status: EncryptionStatus = EncryptionStatus.NONE
    hidden_areas: Dict[str, Any] = Field(default_factory=dict)
    smart: Dict[str, Any] = Field(default_factory=dict)


class StorageVolumeCreate(StorageVolumeBase):
    pass


class StorageVolumeResponse(StorageVolumeBase):
    id: uuid.UUID
    device_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceBase(BaseModel):
    category: DeviceCategory = DeviceCategory.OTHER
    manufacturer: str = "Unknown"
    model: str = "Unknown"
    serial_number: str
    system_uuid: Optional[str] = None
    os_name: str = "Unknown"
    os_version: str = "Unknown"
    os_build: Optional[str] = None
    arch: str = "x86_64"
    bios_vendor: Optional[str] = None
    bios_version: Optional[str] = None
    boot_mode: str = "UEFI"
    status: DeviceStatus = DeviceStatus.ONLINE
    confidence: float = 1.0
    detected_by: str = "manual"
    specs: Dict[str, Any] = Field(default_factory=dict)


class DeviceCreate(DeviceBase):
    volumes: List[StorageVolumeCreate] = Field(default_factory=list)


class DeviceUpdate(BaseModel):
    category: Optional[DeviceCategory] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    status: Optional[DeviceStatus] = None
    specs: Optional[Dict[str, Any]] = None


class DeviceResponse(DeviceBase):
    id: uuid.UUID
    created_at: datetime
    last_seen: datetime
    volumes_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class DeviceDetailResponse(DeviceBase):
    id: uuid.UUID
    created_at: datetime
    last_seen: datetime
    volumes: List[StorageVolumeResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DeviceStatsResponse(BaseModel):
    total_devices: int
    online_devices: int
    stale_devices: int
    offline_devices: int
    by_category: Dict[str, int]
    by_os: Dict[str, int]
    by_media_type: Dict[str, int]
