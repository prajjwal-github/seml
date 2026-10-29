"""WebSocket connection manager for real-time progress events and approval notifications."""

import json
from typing import Any, Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    """Manages active WebSocket connections grouped by subscription channels."""

    def __init__(self):
        self.channel_subscribers: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "global"):
        """Accepts WebSocket connection and subscribes to specified channel."""
        await websocket.accept()
        if channel not in self.channel_subscribers:
            self.channel_subscribers[channel] = set()
        self.channel_subscribers[channel].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str = "global"):
        """Removes WebSocket connection from active subscriber sets."""
        if channel in self.channel_subscribers:
            self.channel_subscribers[channel].discard(websocket)
            if not self.channel_subscribers[channel]:
                del self.channel_subscribers[channel]

    async def broadcast(self, channel: str, message: Dict[str, Any]):
        """Broadcasts JSON payload to all active subscribers of a channel."""
        data_text = json.dumps(message)
        recipients = list(self.channel_subscribers.get(channel, set()))
        dead_connections = []

        for ws in recipients:
            try:
                await ws.send_text(data_text)
            except Exception:
                dead_connections.append(ws)

        for dead in dead_connections:
            self.disconnect(dead, channel)

        # Also broadcast to global channel if channel wasn't global
        if channel != "global":
            global_recipients = list(self.channel_subscribers.get("global", set()))
            for ws in global_recipients:
                try:
                    await ws.send_text(data_text)
                except Exception:
                    self.disconnect(ws, "global")

    async def broadcast_job_progress(
        self,
        job_id: str,
        progress: float,
        current_pass: int,
        total_passes: int,
        message: str,
        status: str,
        event_type: str = "job.progress",
    ):
        """Broadcasts real-time job progress event."""
        payload = {
            "type": event_type,
            "job_id": str(job_id),
            "progress": progress,
            "current_pass": current_pass,
            "total_passes": total_passes,
            "message": message,
            "status": status,
        }
        await self.broadcast(f"job:{job_id}", payload)

    async def broadcast_approval_alert(
        self,
        request_id: str,
        device_name: str,
        requester_name: str,
        risk_level: str,
    ):
        """Broadcasts real-time notification to approvers."""
        payload = {
            "type": "approval.created",
            "request_id": str(request_id),
            "device_name": device_name,
            "requester_name": requester_name,
            "risk_level": risk_level,
        }
        await self.broadcast("approvals", payload)


ws_manager = ConnectionManager()
