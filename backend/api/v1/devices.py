"""Device inventory, storage volumes, and search API endpoints."""

import csv
import io
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.api.deps import get_current_user, get_db, require_roles
from backend.core.audit import log_audit_event
from backend.models import (
    Device,
    DeviceCategory,
    DeviceStatus,
    EncryptionStatus,
    MediaType,
    StorageVolume,
    User,
    UserRole,
)
from backend.schemas.device import (
    DeviceCreate,
    DeviceDetailResponse,
    DeviceResponse,
    DeviceStatsResponse,
    DeviceUpdate,
    StorageVolumeResponse,
)

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("", response_model=List[DeviceResponse])
async def list_devices(
    search: Optional[str] = Query(None, description="Search model, manufacturer, serial"),
    category: Optional[DeviceCategory] = None,
    status: Optional[DeviceStatus] = None,
    media_type: Optional[MediaType] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Lists registered devices with multifaceted filtering and volume counts."""
    stmt = select(Device).order_by(Device.last_seen.desc())

    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Device.manufacturer.ilike(term),
                Device.model.ilike(term),
                Device.serial_number.ilike(term),
                Device.os_name.ilike(term),
            )
        )

    if category:
        stmt = stmt.where(Device.category == category)
    if status:
        stmt = stmt.where(Device.status == status)

    if media_type:
        stmt = stmt.join(Device.volumes).where(StorageVolume.media_type == media_type).distinct()

    res = await session.execute(stmt)
    devices = res.scalars().all()

    # Populate volume counts
    responses = []
    for d in devices:
        count_stmt = select(func.count(StorageVolume.id)).where(StorageVolume.device_id == d.id)
        cnt = (await session.execute(count_stmt)).scalar() or 0
        resp = DeviceResponse.model_validate(d)
        resp.volumes_count = cnt
        responses.append(resp)

    return responses


@router.get("/stats", response_model=DeviceStatsResponse)
async def get_device_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Computes real-time inventory statistics across categories, operating systems, and media."""
    devices = (await session.execute(select(Device))).scalars().all()
    volumes = (await session.execute(select(StorageVolume))).scalars().all()

    by_cat = {}
    by_os = {}
    online_cnt = 0
    stale_cnt = 0
    offline_cnt = 0

    for d in devices:
        c = d.category.value
        by_cat[c] = by_cat.get(c, 0) + 1

        os_key = d.os_name or "Unknown"
        by_os[os_key] = by_os.get(os_key, 0) + 1

        if d.status == DeviceStatus.ONLINE:
            online_cnt += 1
        elif d.status == DeviceStatus.STALE:
            stale_cnt += 1
        else:
            offline_cnt += 1

    by_media = {}
    for v in volumes:
        m = v.media_type.value
        by_media[m] = by_media.get(m, 0) + 1

    return DeviceStatsResponse(
        total_devices=len(devices),
        online_devices=online_cnt,
        stale_devices=stale_cnt,
        offline_devices=offline_cnt,
        by_category=by_cat,
        by_os=by_os,
        by_media_type=by_media,
    )


@router.post("", response_model=DeviceDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    req: DeviceCreate,
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Registers a new IT asset device along with its initial storage volume inventory."""
    device = Device(
        category=req.category,
        manufacturer=req.manufacturer,
        model=req.model,
        serial_number=req.serial_number.strip(),
        system_uuid=req.system_uuid,
        os_name=req.os_name,
        os_version=req.os_version,
        os_build=req.os_build,
        arch=req.arch,
        bios_vendor=req.bios_vendor,
        bios_version=req.bios_version,
        boot_mode=req.boot_mode,
        status=req.status,
        confidence=req.confidence,
        detected_by=req.detected_by,
        specs=req.specs,
        last_seen=datetime.now(timezone.utc),
    )
    session.add(device)
    await session.flush()

    for v in req.volumes:
        vol = StorageVolume(
            device_id=device.id,
            name=v.name,
            mount_point=v.mount_point,
            size_bytes=v.size_bytes,
            media_type=v.media_type,
            bus_type=v.bus_type,
            removable=v.removable,
            partition_table=v.partition_table,
            is_boot=v.is_boot,
            is_system=v.is_system,
            encryption_status=v.encryption_status,
            hidden_areas=v.hidden_areas,
            smart=v.smart,
        )
        session.add(vol)

    await log_audit_event(
        session=session,
        action="DEVICE_CREATED",
        entity_type="DEVICE",
        entity_id=str(device.id),
        actor_id=current_user.id,
        details={"category": device.category.value, "model": device.model},
    )
    await session.commit()
    await session.refresh(device)
    return DeviceDetailResponse.model_validate(device)


@router.get("/{device_id}", response_model=DeviceDetailResponse)
async def get_device(
    device_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieves full device specifications, hardware volumes, and encryption status."""
    stmt = select(Device).where(Device.id == device_id).options(selectinload(Device.volumes))
    res = await session.execute(stmt)
    device = res.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return DeviceDetailResponse.model_validate(device)


@router.post("/import-csv", response_model=List[DeviceResponse])
async def import_devices_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Bulk imports devices and default volumes from a CSV file."""
    content = (await file.read()).decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(content))

    created_devices = []
    for row in reader:
        serial = row.get("serial_number", "").strip() or f"SN-IMP-{uuid.uuid4().hex[:8]}"
        category_str = row.get("category", "DESKTOP").upper()
        try:
            category = DeviceCategory[category_str]
        except KeyError:
            category = DeviceCategory.OTHER

        dev = Device(
            category=category,
            manufacturer=row.get("manufacturer", "Generic").strip(),
            model=row.get("model", "Imported Device").strip(),
            serial_number=serial,
            os_name=row.get("os_name", "Unknown").strip(),
            os_version=row.get("os_version", "Unknown").strip(),
            status=DeviceStatus.ONLINE,
            detected_by="csv-import",
            confidence=1.0,
            specs={"imported": True},
            last_seen=datetime.now(timezone.utc),
        )
        session.add(dev)
        await session.flush()

        # Add primary volume
        vol_size = int(row.get("size_gb", 256)) * 1024 * 1024 * 1024
        vol = StorageVolume(
            device_id=dev.id,
            name="Primary Storage",
            mount_point="/",
            size_bytes=vol_size,
            media_type=MediaType.SATA_SSD,
            bus_type="SATA",
            is_boot=True,
            is_system=True,
        )
        session.add(vol)
        created_devices.append(dev)

    await log_audit_event(
        session=session,
        action="DEVICES_BULK_IMPORTED",
        entity_type="DEVICE",
        entity_id="BULK",
        actor_id=current_user.id,
        details={"count": len(created_devices)},
    )
    await session.commit()
    return [DeviceResponse.model_validate(d) for d in created_devices]
