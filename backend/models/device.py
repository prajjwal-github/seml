"""Device and StorageVolume database models."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from backend.models.enums import DeviceCategory, DeviceStatus, EncryptionStatus, MediaType


class Device(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "devices"

    category: Mapped[DeviceCategory] = mapped_column(String(50), nullable=False, default=DeviceCategory.OTHER)
    manufacturer: Mapped[str] = mapped_column(String(255), nullable=False, default="Unknown")
    model: Mapped[str] = mapped_column(String(255), nullable=False, default="Unknown")
    serial_number: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    system_uuid: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    os_name: Mapped[str] = mapped_column(String(100), nullable=False, default="Unknown")
    os_version: Mapped[str] = mapped_column(String(100), nullable=False, default="Unknown")
    os_build: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    arch: Mapped[str] = mapped_column(String(50), nullable=False, default="x86_64")

    bios_vendor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bios_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    boot_mode: Mapped[str] = mapped_column(String(50), nullable=False, default="UEFI")

    status: Mapped[DeviceStatus] = mapped_column(String(50), nullable=False, default=DeviceStatus.ONLINE)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    detected_by: Mapped[str] = mapped_column(String(100), nullable=False, default="manual")
    specs: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    volumes: Mapped[List["StorageVolume"]] = relationship(
        "StorageVolume",
        back_populates="device",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    wipe_requests: Mapped[List["WipeRequest"]] = relationship(
        "WipeRequest",
        back_populates="device",
        cascade="all, delete-orphan",
    )


class StorageVolume(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "storage_volumes"

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mount_point: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    media_type: Mapped[MediaType] = mapped_column(String(50), nullable=False, default=MediaType.HDD)
    bus_type: Mapped[str] = mapped_column(String(50), nullable=False, default="SATA")
    removable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    partition_table: Mapped[str] = mapped_column(String(50), nullable=False, default="GPT")

    is_boot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    encryption_status: Mapped[EncryptionStatus] = mapped_column(
        String(50), nullable=False, default=EncryptionStatus.NONE
    )

    hidden_areas: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    smart: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    device: Mapped["Device"] = relationship("Device", back_populates="volumes")
