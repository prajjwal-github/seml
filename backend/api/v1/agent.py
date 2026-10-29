"""Detection Agent API endpoints (register, report inventory, heartbeat)."""

import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_agent_from_key, get_db
from backend.core.audit import log_audit_event
from backend.core.security import sha256_hex
from backend.models import (
    Agent,
    Device,
    DeviceCategory,
    DeviceStatus,
    EncryptionStatus,
    MediaType,
    StorageVolume,
)

router = APIRouter(prefix="/agent", tags=["Agent"])


class AgentRegisterRequest(BaseModel):
    hostname: str
    ip_address: str = "127.0.0.1"


class AgentRegisterResponse(BaseModel):
    agent_id: uuid.UUID
    api_key: str  # Only returned once upon registration


class AgentReportRequest(BaseModel):
    category: DeviceCategory
    manufacturer: str
    model: str
    serial_number: str
    system_uuid: str = ""
    os_name: str
    os_version: str
    os_build: str = ""
    arch: str
    bios_vendor: str = ""
    bios_version: str = ""
    boot_mode: str = "UEFI"
    confidence: float = 1.0
    detected_by: str = "wipe-agent"
    specs: Dict[str, Any] = {}
    volumes: List[Dict[str, Any]] = []


@router.post("/register", response_model=AgentRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(req: AgentRegisterRequest, session: AsyncSession = Depends(get_db)):
    """Registers a new device detection agent and returns a secure X-Agent-Key."""
    raw_key = secrets.token_urlsafe(32)
    key_hash = sha256_hex(raw_key)

    agent = Agent(
        api_key_hash=key_hash,
        hostname=req.hostname,
        ip_address=req.ip_address,
        last_seen=datetime.now(timezone.utc),
        is_active=True,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)

    return AgentRegisterResponse(agent_id=agent.id, api_key=raw_key)


@router.post("/report")
async def report_device_inventory(
    req: AgentReportRequest,
    agent: Agent = Depends(get_agent_from_key),
    session: AsyncSession = Depends(get_db),
):
    """Receives read-only hardware and storage volume detection report from agent."""
    now = datetime.now(timezone.utc)

    # Check if device with this serial number already exists
    stmt = select(Device).where(Device.serial_number == req.serial_number.strip())
    res = await session.execute(stmt)
    device = res.scalar_one_or_none()

    if not device:
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
            status=DeviceStatus.ONLINE,
            confidence=req.confidence,
            detected_by=req.detected_by,
            specs=req.specs,
            last_seen=now,
        )
        session.add(device)
        await session.flush()
    else:
        # Update device specs & status
        device.category = req.category
        device.manufacturer = req.manufacturer
        device.model = req.model
        device.os_name = req.os_name
        device.os_version = req.os_version
        device.status = DeviceStatus.ONLINE
        device.confidence = req.confidence
        device.specs = req.specs
        device.last_seen = now

    agent.device_id = device.id
    agent.last_seen = now

    # Upsert storage volumes
    for vol_dict in req.volumes:
        v_name = vol_dict.get("name", "Drive 0")
        v_stmt = select(StorageVolume).where(
            StorageVolume.device_id == device.id,
            StorageVolume.name == v_name,
        )
        v_res = await session.execute(v_stmt)
        vol = v_res.scalar_one_or_none()

        m_type = vol_dict.get("media_type", "HDD")
        try:
            media_type = MediaType[m_type]
        except KeyError:
            media_type = MediaType.OTHER

        enc_str = vol_dict.get("encryption_status", "NONE")
        try:
            enc_status = EncryptionStatus[enc_str]
        except KeyError:
            enc_status = EncryptionStatus.NONE

        if not vol:
            vol = StorageVolume(
                device_id=device.id,
                name=v_name,
                mount_point=vol_dict.get("mount_point"),
                size_bytes=int(vol_dict.get("size_bytes", 0)),
                media_type=media_type,
                bus_type=vol_dict.get("bus_type", "SATA"),
                removable=bool(vol_dict.get("removable", False)),
                partition_table=vol_dict.get("partition_table", "GPT"),
                is_boot=bool(vol_dict.get("is_boot", False)),
                is_system=bool(vol_dict.get("is_system", False)),
                encryption_status=enc_status,
                hidden_areas=vol_dict.get("hidden_areas", {}),
                smart=vol_dict.get("smart", {}),
            )
            session.add(vol)
        else:
            vol.size_bytes = int(vol_dict.get("size_bytes", vol.size_bytes))
            vol.media_type = media_type
            vol.encryption_status = enc_status
            vol.hidden_areas = vol_dict.get("hidden_areas", vol.hidden_areas)
            vol.smart = vol_dict.get("smart", vol.smart)

    await log_audit_event(
        session=session,
        action="AGENT_REPORT_PROCESSED",
        entity_type="DEVICE",
        entity_id=str(device.id),
        details={"agent_id": str(agent.id), "volumes_reported": len(req.volumes)},
    )
    await session.commit()
    return {"status": "success", "device_id": str(device.id)}


@router.post("/heartbeat")
async def agent_heartbeat(
    agent: Agent = Depends(get_agent_from_key),
    session: AsyncSession = Depends(get_db),
):
    """Refreshes last_seen timestamp for agent and associated device."""
    now = datetime.now(timezone.utc)
    agent.last_seen = now

    if agent.device_id:
        dev = await session.get(Device, agent.device_id)
        if dev:
            dev.last_seen = now
            dev.status = DeviceStatus.ONLINE

    await session.commit()
    return {"status": "ok", "timestamp": now.isoformat()}
