"""HTTP transport client for communicating with the SecureWipe backend."""

from typing import Any, Dict, Optional
import httpx


class AgentTransport:
    """Manages secure HTTP communication with the platform server."""

    def __init__(self, server_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key

    def register(self, hostname: str) -> Dict[str, Any]:
        """Registers the agent with the server and obtains an X-Agent-Key."""
        url = f"{self.server_url}/api/v1/agent/register"
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json={"hostname": hostname})
            resp.raise_for_status()
            data = resp.json()
            self.api_key = data["api_key"]
            return data

    def report(self, inventory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sends the read-only hardware and storage detection report to the server."""
        if not self.api_key:
            raise ValueError("Agent is not authenticated. Please register first.")

        url = f"{self.server_url}/api/v1/agent/report"
        headers = {"X-Agent-Key": self.api_key}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=inventory_data, headers=headers)
            resp.raise_for_status()
            return resp.json()

    def heartbeat(self) -> bool:
        """Sends periodic 30-second heartbeat to maintain ONLINE status."""
        if not self.api_key:
            return False

        url = f"{self.server_url}/api/v1/agent/heartbeat"
        headers = {"X-Agent-Key": self.api_key}
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(url, headers=headers)
                return resp.status_code == 200
        except Exception:
            return False
