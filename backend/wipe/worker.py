"""Asyncio in-process background worker executing simulated wipe jobs and event streams."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.certs.generator import generate_certificate
from backend.core.audit import log_audit_event
from backend.core.database import AsyncSessionLocal
from backend.core.security import compute_request_fingerprint
from backend.models import (
    Approval,
    ApprovalDecision,
    Certificate,
    Device,
    JobStatus,
    RequestStatus,
    StorageVolume,
    WipeJob,
    WipeJobEvent,
    WipeRequest,
)
from backend.services.wipe_planner import WipePlanner
from backend.wipe.adapter import SimulatedWipeAdapter
from backend.ws.manager import ws_manager

logger = logging.getLogger("securewipe.worker")


class WipeWorker:
    """In-process asyncio worker for simulated NIST SP 800-88 Rev. 1 wiping."""

    def __init__(self):
        self._running = False
        self._active_jobs: Dict[uuid.UUID, asyncio.Task] = {}
        self._cancel_events: Dict[uuid.UUID, asyncio.Event] = {}

    def start(self):
        """Starts background task runner loop."""
        self._running = True
        asyncio.create_task(self._worker_loop())
        logger.info("SecureWipe background worker started (SIMULATION MODE)")

    def stop(self):
        """Stops background worker gracefully."""
        self._running = False
        for task in self._active_jobs.values():
            task.cancel()

    def cancel_job(self, job_id: uuid.UUID) -> bool:
        """Signals cancellation to an actively executing job."""
        if job_id in self._cancel_events:
            self._cancel_events[job_id].set()
            return True
        return False

    async def _worker_loop(self):
        """Polls for QUEUED jobs and executes them."""
        while self._running:
            try:
                await self._process_queued_jobs()
            except Exception as e:
                logger.error(f"Worker loop error: {e}", exc_info=True)
            await asyncio.sleep(1.0)

    async def _process_queued_jobs(self):
        """Finds any pending or resumable QUEUED jobs in the database."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(WipeJob)
                .where(WipeJob.status == JobStatus.QUEUED)
                .order_by(WipeJob.created_at.asc())
            )
            res = await session.execute(stmt)
            queued_jobs = res.scalars().all()

            for job in queued_jobs:
                if job.id not in self._active_jobs:
                    cancel_evt = asyncio.Event()
                    self._cancel_events[job.id] = cancel_evt
                    task = asyncio.create_task(self._execute_job(job.id, cancel_evt))
                    self._active_jobs[job.id] = task

    async def _execute_job(self, job_id: uuid.UUID, cancel_event: asyncio.Event):
        """Executes a single sanitization job through simulated passes, verification, and certification."""
        adapter = SimulatedWipeAdapter()

        try:
            async with AsyncSessionLocal() as session:
                job = await session.get(WipeJob, job_id)
                if not job or job.status != JobStatus.QUEUED:
                    return

                request = await session.get(WipeRequest, job.request_id)
                approval = await session.get(Approval, job.approval_id)
                device = await session.get(Device, request.device_id)

                # 1. Re-validate approval & fingerprint at job start
                now = datetime.now(timezone.utc)
                appr_decision = approval.decision.value if hasattr(approval.decision, "value") else str(approval.decision)
                if appr_decision != "APPROVED" or approval.expires_at < now:
                    job.status = JobStatus.FAILED
                    request.status = RequestStatus.FAILED
                    job.result = {"error": "Approval expired or not approved"}
                    await session.commit()
                    await ws_manager.broadcast_job_progress(
                        str(job_id), 0.0, 1, 1, "Job failed: Approval invalid or expired", "FAILED"
                    )
                    return

                method_str = request.method.value if hasattr(request.method, "value") else str(request.method)
                expected_fp = compute_request_fingerprint(
                    device_id=request.device_id,
                    volume_ids=request.volume_ids,
                    method=method_str,
                    serial_number=device.serial_number,
                )
                if approval.request_fingerprint != expected_fp:
                    job.status = JobStatus.FAILED
                    request.status = RequestStatus.FAILED
                    job.result = {"error": "Request fingerprint mismatch detected at job execution"}
                    await session.commit()
                    await ws_manager.broadcast_job_progress(
                        str(job_id), 0.0, 1, 1, "Job failed: Fingerprint tampering detected", "FAILED"
                    )
                    return

                # Mark approval token used atomically
                approval.used_at = now

                # Fetch volumes
                vols_stmt = select(StorageVolume).where(StorageVolume.id.in_(request.volume_ids))
                vols_res = await session.execute(vols_stmt)
                volumes = vols_res.scalars().all()

                # Determine primary media plan
                vol_media = volumes[0].media_type.value if (volumes and hasattr(volumes[0].media_type, "value")) else (str(volumes[0].media_type) if volumes else str(device.category))
                plan = WipePlanner.create_plan(vol_media, method_str)

                # Transition status to RUNNING
                job.status = JobStatus.RUNNING
                request.status = RequestStatus.RUNNING
                job.started_at = now
                job.total_passes = plan.to_dict()["total_passes"]
                await session.commit()

                await log_audit_event(
                    session=session,
                    action="WIPE_STARTED",
                    entity_type="WIPE_JOB",
                    entity_id=str(job.id),
                    actor_id=request.requested_by,
                    details={"plan": plan.to_dict(), "mode": "simulation"},
                )
                await session.commit()

            # Execute Sanitization Passes
            total_passes = plan.to_dict()["total_passes"]
            pass_results = []

            for pass_def in plan.passes:
                pass_no = pass_def["pass_number"]
                pass_name = pass_def["name"]

                async def on_progress(pct: float, msg: str):
                    async with AsyncSessionLocal() as s:
                        j = await s.get(WipeJob, job_id)
                        if j:
                            # Overall progress calculated across passes
                            overall_pct = ((pass_no - 1) * 100.0 + pct) / (total_passes + 1)
                            j.progress = round(overall_pct, 1)
                            j.current_pass = pass_no

                            evt = WipeJobEvent(
                                job_id=job_id,
                                event_type="pass_progress",
                                message=msg,
                                pass_number=pass_no,
                                progress=j.progress,
                                payload={"step_progress": pct},
                            )
                            s.add(evt)
                            await s.commit()

                    await ws_manager.broadcast_job_progress(
                        job_id=str(job_id),
                        progress=round(((pass_no - 1) * 100.0 + pct) / (total_passes + 1), 1),
                        current_pass=pass_no,
                        total_passes=total_passes,
                        message=msg,
                        status="RUNNING",
                    )

                for vol in volumes:
                    vol_dict = {
                        "name": vol.name,
                        "media_type": vol.media_type.value if hasattr(vol.media_type, "value") else str(vol.media_type),
                        "size_bytes": vol.size_bytes,
                        "hidden_areas": vol.hidden_areas,
                    }
                    p_res = await adapter.execute_pass(
                        pass_number=pass_no,
                        total_passes=total_passes,
                        pass_name=pass_name,
                        volume_info=vol_dict,
                        on_progress=on_progress,
                        cancel_event=cancel_event,
                    )
                    pass_results.append(p_res)

            # Transition to VERIFYING
            async with AsyncSessionLocal() as session:
                job = await session.get(WipeJob, job_id)
                request = await session.get(WipeRequest, job.request_id)
                job.status = JobStatus.VERIFYING
                request.status = RequestStatus.VERIFYING
                await session.commit()

            async def on_verify_progress(pct: float, msg: str):
                overall_pct = (total_passes * 100.0 + pct) / (total_passes + 1)
                async with AsyncSessionLocal() as s:
                    j = await s.get(WipeJob, job_id)
                    if j:
                        j.progress = round(overall_pct, 1)
                        evt = WipeJobEvent(
                            job_id=job_id,
                            event_type="verification_progress",
                            message=msg,
                            pass_number=total_passes,
                            progress=j.progress,
                            payload={"verify_step": pct},
                        )
                        s.add(evt)
                        await s.commit()

                await ws_manager.broadcast_job_progress(
                    job_id=str(job_id),
                    progress=round(overall_pct, 1),
                    current_pass=total_passes,
                    total_passes=total_passes,
                    message=msg,
                    status="VERIFYING",
                )

            # Run hidden area checks & verification
            hidden_area_res = await adapter.check_hidden_areas(
                volume_info={"name": volumes[0].name if volumes else "Drive", "hidden_areas": {}},
                on_progress=on_verify_progress,
            )
            verify_res = await adapter.verify_wipe(
                volume_info={"name": volumes[0].name if volumes else "Drive"},
                sample_percentage=plan.verification_sample_pct,
                on_progress=on_verify_progress,
            )

            # Complete Job & Issue Certificate
            finish_time = datetime.now(timezone.utc)
            async with AsyncSessionLocal() as session:
                job = await session.get(WipeJob, job_id)
                request = await session.get(WipeRequest, job.request_id)

                job.status = JobStatus.COMPLETED
                request.status = RequestStatus.COMPLETED
                job.progress = 100.0
                job.finished_at = finish_time
                job.result = {
                    "mode": "simulation",
                    "plan": plan.to_dict(),
                    "passes": pass_results,
                    "hidden_areas": hidden_area_res,
                    "verification": verify_res,
                    "completed_at": finish_time.isoformat(),
                }

                # Generate cryptographically signed Certificate and ReportLab PDF
                cert = await generate_certificate(session, job)

                await log_audit_event(
                    session=session,
                    action="WIPE_COMPLETED",
                    entity_type="WIPE_JOB",
                    entity_id=str(job.id),
                    actor_id=request.requested_by,
                    details={"certificate_id": cert.certificate_id, "mode": "simulation"},
                )
                await log_audit_event(
                    session=session,
                    action="CERTIFICATE_ISSUED",
                    entity_type="CERTIFICATE",
                    entity_id=cert.certificate_id,
                    actor_id=request.requested_by,
                    details={"sha256": cert.payload_sha256, "key_id": cert.public_key_id},
                )
                await session.commit()

            await ws_manager.broadcast_job_progress(
                job_id=str(job_id),
                progress=100.0,
                current_pass=total_passes,
                total_passes=total_passes,
                message=f"Simulated wipe completed successfully. Certificate {cert.certificate_id} issued.",
                status="COMPLETED",
            )

        except asyncio.CancelledError:
            async with AsyncSessionLocal() as session:
                job = await session.get(WipeJob, job_id)
                if job:
                    job.status = JobStatus.CANCELLED
                    req = await session.get(WipeRequest, job.request_id)
                    if req:
                        req.status = RequestStatus.CANCELLED
                    await session.commit()
            await ws_manager.broadcast_job_progress(
                job_id=str(job_id),
                progress=0.0,
                current_pass=1,
                total_passes=1,
                message="Wipe job was cancelled by operator.",
                status="CANCELLED",
            )

        except Exception as exc:
            logger.error(f"Job {job_id} encountered error: {exc}", exc_info=True)
            async with AsyncSessionLocal() as session:
                job = await session.get(WipeJob, job_id)
                if job:
                    job.status = JobStatus.FAILED
                    req = await session.get(WipeRequest, job.request_id)
                    if req:
                        req.status = RequestStatus.FAILED
                    job.result = {"error": str(exc), "mode": "simulation"}
                    await session.commit()
            await ws_manager.broadcast_job_progress(
                job_id=str(job_id),
                progress=0.0,
                current_pass=1,
                total_passes=1,
                message=f"Wipe job failed: {str(exc)}",
                status="FAILED",
            )

        finally:
            self._active_jobs.pop(job_id, None)
            self._cancel_events.pop(job_id, None)


wipe_worker = WipeWorker()
