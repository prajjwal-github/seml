"""Command-line interface for the read-only device detection agent."""

import argparse
import json
import socket
import sys
import time
from agent.wipe_agent.detect.base import detect_host_device
from agent.wipe_agent.transport import AgentTransport


def main():
    parser = argparse.ArgumentParser(
        prog="wipe-agent",
        description="Secure Data Wiping - Read-Only Device Detection Agent",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # detect command
    detect_parser = subparsers.add_parser("detect", help="Inspect local hardware in read-only mode")
    detect_parser.add_argument("--json", action="store_true", help="Print structured JSON output")

    # register command
    reg_parser = subparsers.add_parser("register", help="Register this machine with the server")
    reg_parser.add_argument("--server", default="http://localhost:8000", help="Platform server URL")

    # run command
    run_parser = subparsers.add_parser("run", help="Run detection, report inventory, and start heartbeat loop")
    run_parser.add_argument("--server", default="http://localhost:8000", help="Platform server URL")
    run_parser.add_argument("--key", required=True, help="Agent API Key (X-Agent-Key)")
    run_parser.add_argument("--interval", type=int, default=30, help="Heartbeat interval in seconds")

    args = parser.parse_args()

    if args.command == "detect":
        data = detect_host_device()
        if getattr(args, "json", False):
            print(json.dumps(data, indent=2))
        else:
            print(f"Device Category : {data.get('category')} (Confidence: {data.get('confidence')*100:.0f}%)")
            print(f"Hardware Model  : {data.get('manufacturer')} {data.get('model')}")
            print(f"Serial Number   : {data.get('serial_number')}")
            print(f"Operating System: {data.get('os_name')} {data.get('os_version')}")
            print(f"Storage Volumes : {len(data.get('volumes', []))} volume(s) discovered")
            for idx, v in enumerate(data.get("volumes", []), 1):
                size_gb = v.get("size_bytes", 0) / (1024**3)
                print(f"  [{idx}] {v.get('name')} | {v.get('media_type')} | {size_gb:.1f} GB | Enc: {v.get('encryption_status')}")

    elif args.command == "register":
        hostname = socket.gethostname()
        transport = AgentTransport(server_url=args.server)
        try:
            res = transport.register(hostname=hostname)
            print(f"Successfully registered agent for '{hostname}'!")
            print(f"Agent ID : {res['agent_id']}")
            print(f"Agent Key: {res['api_key']}")
            print("\nTo start reporting, run:")
            print(f"  wipe-agent run --server {args.server} --key {res['api_key']}")
        except Exception as e:
            print(f"Registration failed: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "run":
        transport = AgentTransport(server_url=args.server, api_key=args.key)
        print("Inspecting local hardware in read-only mode...")
        inventory = detect_host_device()
        try:
            res = transport.report(inventory)
            print(f"Report submitted successfully! Device ID: {res.get('device_id')}")
        except Exception as e:
            print(f"Failed to submit device inventory report: {e}", file=sys.stderr)
            sys.exit(1)

        print(f"Starting 30-second heartbeat loop (Press Ctrl+C to stop)...")
        try:
            while True:
                time.sleep(args.interval)
                ok = transport.heartbeat()
                status_str = "OK" if ok else "FAILED"
                print(f"[{time.strftime('%X')}] Heartbeat: {status_str}")
        except KeyboardInterrupt:
            print("\nAgent stopped.")


if __name__ == "__main__":
    main()
