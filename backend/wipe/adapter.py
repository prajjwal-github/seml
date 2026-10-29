"""WipeAdapter interface and SimulatedWipeAdapter implementation.

CRITICAL RULE: SIMULATION ONLY.
Wiping goes through an interface WipeAdapter with exactly ONE implementation, SimulatedWipeAdapter.
It only sleeps, emits progress events (pass 1/3, 37%...), writes DB rows and returns a result.
It NEVER touches a block device or any file outside the app's own storage dir.
"""

import asyncio
import random
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional
from backend.core.config import settings


class WipeAdapter(ABC):
    """Abstract interface for storage media sanitization adapters."""

    @abstractmethod
    async def execute_pass(
        self,
        pass_number: int,
        total_passes: int,
        pass_name: str,
        volume_info: Dict[str, Any],
        on_progress: Callable[[float, str], Coroutine[Any, Any, None]],
        cancel_event: Optional[asyncio.Event] = None,
    ) -> Dict[str, Any]:
        """Executes a single sanitization pass with progress callbacks."""
        pass

    @abstractmethod
    async def check_hidden_areas(
        self,
        volume_info: Dict[str, Any],
        on_progress: Callable[[float, str], Coroutine[Any, Any, None]],
    ) -> Dict[str, Any]:
        """Inspects and clears hidden storage areas (HPA, DCO, remapped blocks, over-provisioning)."""
        pass

    @abstractmethod
    async def verify_wipe(
        self,
        volume_info: Dict[str, Any],
        sample_percentage: float,
        on_progress: Callable[[float, str], Coroutine[Any, Any, None]],
    ) -> Dict[str, Any]:
        """Verifies sanitization through pseudo-random block read-backs."""
        pass


class SimulatedWipeAdapter(WipeAdapter):
    """Safe, non-destructive simulated wipe adapter complying strictly with NIST SP 800-88 Rev. 1.

    Guarantees:
    - Never executes destructive system commands.
    - Never touches physical disks, partitions, or block devices.
    - Strictly simulates pass execution via asyncio sleeps and progress broadcasts.
    """

    def __init__(self, failure_rate: float = 0.0, step_sleep_ms: Optional[int] = None):
        self.failure_rate = failure_rate if failure_rate >= 0.0 else settings.SIM_FAILURE_RATE
        self.step_sleep_ms = step_sleep_ms or settings.SIM_PASS_SLEEP_MS

    async def execute_pass(
        self,
        pass_number: int,
        total_passes: int,
        pass_name: str,
        volume_info: Dict[str, Any],
        on_progress: Callable[[float, str], Coroutine[Any, Any, None]],
        cancel_event: Optional[asyncio.Event] = None,
    ) -> Dict[str, Any]:
        """Simulates pass execution in increments from 0% to 100%."""
        vol_name = volume_info.get("name", "Volume")
        media_type = volume_info.get("media_type", "Unknown")

        # Check for simulated failure trigger
        if self.failure_rate > 0.0 and random.random() < self.failure_rate:
            raise RuntimeError(
                f"Simulated hardware I/O error on {vol_name} during pass {pass_number} ({pass_name})"
            )

        # 10 progress steps (10% to 100%)
        for pct in range(10, 101, 10):
            if cancel_event and cancel_event.is_set():
                raise asyncio.CancelledError(f"Simulated wipe of {vol_name} cancelled by operator")

            # Sleep briefly to simulate work
            await asyncio.sleep(self.step_sleep_ms / 1000.0)

            msg = f"Pass {pass_number}/{total_passes}: {pass_name} on {vol_name} ({media_type}) - {pct}% complete"
            await on_progress(float(pct), msg)

        return {
            "pass_number": pass_number,
            "pass_name": pass_name,
            "volume": vol_name,
            "status": "COMPLETED",
            "mode": "simulation",
            "bytes_simulated": volume_info.get("size_bytes", 0),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def check_hidden_areas(
        self,
        volume_info: Dict[str, Any],
        on_progress: Callable[[float, str], Coroutine[Any, Any, None]],
    ) -> Dict[str, Any]:
        """Simulates inspection and clearing of HPA, DCO, and remapped sectors."""
        vol_name = volume_info.get("name", "Volume")
        hidden_info = volume_info.get("hidden_areas", {})

        await on_progress(25.0, f"Inspecting Host Protected Area (HPA) and DCO on {vol_name}...")
        await asyncio.sleep(self.step_sleep_ms / 1000.0)

        await on_progress(60.0, f"Evaluating remapped sector table and wear-leveling reserves on {vol_name}...")
        await asyncio.sleep(self.step_sleep_ms / 1000.0)

        await on_progress(100.0, f"Hidden areas checked and verified safe on {vol_name}.")
        return {
            "hpa_detected": hidden_info.get("hpa_present", False),
            "hpa_cleared": True,
            "dco_detected": hidden_info.get("dco_present", False),
            "dco_cleared": True,
            "remapped_sectors_checked": True,
            "over_provisioning_addressed": True,
            "mode": "simulation",
        }

    async def verify_wipe(
        self,
        volume_info: Dict[str, Any],
        sample_percentage: float,
        on_progress: Callable[[float, str], Coroutine[Any, Any, None]],
    ) -> Dict[str, Any]:
        """Simulates cryptographic sample verification of sanitized blocks."""
        vol_name = volume_info.get("name", "Volume")
        steps = [30.0, 70.0, 100.0]

        for s in steps:
            await asyncio.sleep(self.step_sleep_ms / 1000.0)
            await on_progress(s, f"Verifying {sample_percentage:.1f}% sample of {vol_name}: {s:.0f}% read-back verified")

        return {
            "verified": True,
            "sample_percentage": sample_percentage,
            "mode": "simulation",
            "hash_verification": "ZERO_PATTERN_CONFIRMED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
