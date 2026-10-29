"""Device inventory, storage volumes, and search API endpoints."""

import csv
import io
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import delete as sa_delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.api.deps import get_current_user, get_db, require_roles
from backend.core.audit import log_audit_event
from backend.models import (
    Certificate,
    Device,
    DeviceCategory,
    DeviceStatus,
    EncryptionStatus,
    MediaType,
    StorageVolume,
    User,
    UserRole,
    WipeJob,
    WipeRequest,
)
from backend.ws.manager import ws_manager
from backend.schemas.device import (
    DeviceCreate,
    DeviceDetailResponse,
    DeviceResponse,
    DeviceStatsResponse,
    DeviceUpdate,
    StorageVolumeResponse,
)

router = APIRouter(prefix="/devices", tags=["Devices"])


async def _attach_wipe_state(session: AsyncSession, responses: List[DeviceResponse]) -> None:
    """Fills each device's certificate lifecycle from its most recent wipe request."""
    if not responses:
        return
    ids = [r.id for r in responses]
    reqs = (
        await session.execute(
            select(WipeRequest).where(WipeRequest.device_id.in_(ids)).order_by(WipeRequest.created_at.asc())
        )
    ).scalars().all()
    latest = {}
    for r in reqs:
        latest[r.device_id] = r

    req_ids = [r.id for r in latest.values()]
    cert_by_req = {}
    if req_ids:
        rows = await session.execute(
            select(WipeJob.request_id, Certificate.certificate_id)
            .join(Certificate, Certificate.job_id == WipeJob.id)
            .where(WipeJob.request_id.in_(req_ids))
        )
        cert_by_req = {row[0]: row[1] for row in rows.all()}

    for resp in responses:
        r = latest.get(resp.id)
        if r:
            resp.wipe_status = r.status.value if hasattr(r.status, "value") else str(r.status)
            resp.latest_request_id = r.id
            resp.certificate_id = cert_by_req.get(r.id)


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

    # Populate volume counts (volumes are eagerly loaded) and certificate lifecycle
    responses = []
    for d in devices:
        resp = DeviceResponse.model_validate(d)
        resp.volumes_count = len(d.volumes)
        responses.append(resp)

    await _attach_wipe_state(session, responses)
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
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Admin registers a new office device along with its storage volume inventory."""
    serial = req.serial_number.strip()
    if not serial:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Serial number is required")
    dup = (await session.execute(select(Device).where(func.lower(Device.serial_number) == serial.lower()))).scalars().first()
    if dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A device with serial number '{serial}' is already registered.",
        )
    if not req.volumes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add at least one storage volume so the device can be sanitized.",
        )

    device = Device(
        category=req.category,
        manufacturer=req.manufacturer,
        model=req.model,
        serial_number=serial,
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
    device = (
        await session.execute(select(Device).where(Device.id == device.id).options(selectinload(Device.volumes)))
    ).scalar_one()
    await ws_manager.broadcast_global({"type": "device.updated", "device_id": str(device.id)})
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
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Bulk imports devices and default volumes from a CSV file."""
    content = (await file.read()).decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(content))

    created_devices = []
    for row in reader:
        serial = (row.get("serial_number") or "").strip() or f"SN-IMP-{uuid.uuid4().hex[:8]}"
        exists = (
            await session.execute(select(Device.id).where(func.lower(Device.serial_number) == serial.lower()))
        ).first()
        if exists:
            continue
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
        try:
            size_gb = row.get("storage_size_gb") or row.get("size_gb") or 256
            vol_size = int(float(size_gb)) * 1024 * 1024 * 1024
        except ValueError:
            vol_size = 256 * 1024 * 1024 * 1024
        media_str = (row.get("storage_media_type") or row.get("media_type") or "SATA_SSD").strip().upper().replace(" ", "_")
        media_str = {"NVME": "NVME_SSD", "SSD": "SATA_SSD", "USB": "USB_FLASH", "SD": "SD_CARD"}.get(media_str, media_str)
        try:
            media = MediaType[media_str]
        except KeyError:
            media = MediaType.OTHER
        vol = StorageVolume(
            device_id=dev.id,
            name="Primary Storage",
            mount_point="/",
            size_bytes=vol_size,
            media_type=media,
            bus_type="NVMe" if media == MediaType.NVME_SSD else "SATA",
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
    await ws_manager.broadcast_global({"type": "device.updated", "device_id": "BULK"})
    return [DeviceResponse.model_validate(d) for d in created_devices]


@router.patch("/{device_id}", response_model=DeviceDetailResponse)
async def update_device(
    device_id: uuid.UUID,
    req: DeviceUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Admin edits a registered device's descriptive details."""
    device = (
        await session.execute(select(Device).where(Device.id == device_id).options(selectinload(Device.volumes)))
    ).scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    changes = req.model_dump(exclude_none=True)
    for field, value in changes.items():
        setattr(device, field, value)

    await log_audit_event(
        session=session,
        action="DEVICE_UPDATED",
        entity_type="DEVICE",
        entity_id=str(device.id),
        actor_id=current_user.id,
        details={"updated_fields": list(changes.keys())},
    )
    await session.commit()
    await session.refresh(device)
    await ws_manager.broadcast_global({"type": "device.updated", "device_id": str(device.id)})
    return DeviceDetailResponse.model_validate(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: uuid.UUID,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    """Admin removes a device that has never had a certificate request."""
    device = await session.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    has_requests = (
        await session.execute(select(WipeRequest.id).where(WipeRequest.device_id == device_id).limit(1))
    ).first()
    if has_requests:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This device has certificate history and cannot be removed.",
        )

    await log_audit_event(
        session=session,
        action="DEVICE_DELETED",
        entity_type="DEVICE",
        entity_id=str(device.id),
        actor_id=current_user.id,
        details={"serial_number": device.serial_number, "model": device.model},
    )
    await session.execute(sa_delete(Device).where(Device.id == device_id))
    await session.commit()
    await ws_manager.broadcast_global({"type": "device.updated", "device_id": str(device_id)})
