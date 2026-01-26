#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Device Registry Script

List all devices from Home Assistant's device registry via WebSocket API.

Usage:
    uv run list-devices.py
    uv run list-devices.py --search "Eve"
    uv run list-devices.py --label thread
    uv run list-devices.py --area living_room
    uv run list-devices.py --json
    uv run list-devices.py --help
"""

import json
import os
import sys
from typing import Any
from urllib.parse import urlparse, urlunparse

import click
from websocket import WebSocketTimeoutException, create_connection


def get_required_env(name: str, help_text: str = "") -> str:
    """Get required environment variable or fail fast."""
    value = os.getenv(name)
    if not value:
        click.echo(f"❌ Error: {name} not set.", err=True)
        if help_text:
            click.echo(f"   {help_text}", err=True)
        click.echo(f'   Set: export {name}="<value>"', err=True)
        sys.exit(1)
    return value


# Configuration from environment
HA_URL = get_required_env(
    "HOMEASSISTANT_URL",
    "Your HA instance URL, e.g., http://homeassistant.local:8123",
)
HA_TOKEN = get_required_env(
    "HOMEASSISTANT_TOKEN",
    "Get from: HA → Profile → Security → Long-Lived Access Tokens",
)
WS_TIMEOUT = 30


def get_websocket_url(base_url: str) -> str:
    """Convert HTTP(S) URL to WebSocket URL using proper parsing."""
    parsed = urlparse(base_url)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    base_path = parsed.path.rstrip("/")
    ws_path = f"{base_path}/api/websocket"
    return urlunparse(parsed._replace(scheme=ws_scheme, path=ws_path))


def websocket_command(command_type: str) -> dict[str, Any]:
    """Execute WebSocket command and return result."""
    ws_url = get_websocket_url(HA_URL)
    ws = None
    try:
        ws = create_connection(ws_url, timeout=WS_TIMEOUT)
        # Auth phase
        ws.recv()  # auth_required
        ws.send(json.dumps({"type": "auth", "access_token": HA_TOKEN}))
        auth_result = json.loads(ws.recv())

        if auth_result.get("type") != "auth_ok":
            raise Exception(f"Authentication failed: {auth_result}")

        # Command phase
        ws.send(json.dumps({"id": 1, "type": command_type}))
        result = json.loads(ws.recv())

        if not result.get("success"):
            error = result.get("error", {})
            error_code = error.get("code", "unknown")
            if error_code == "unknown_command":
                raise Exception(f"Command '{command_type}' not supported (HA version may be incompatible)")
            raise Exception(f"Command failed: {error.get('message', 'Unknown error')}")

        return result.get("result", {})
    except WebSocketTimeoutException as error:
        raise Exception(f"WebSocket timeout after {WS_TIMEOUT}s") from error
    finally:
        if ws:
            ws.close()


def format_devices(devices: list[dict[str, Any]]) -> str:
    """Format devices for human-readable output."""
    lines: list[str] = []

    if not devices:
        return "No devices found."

    lines.append("")
    lines.append("=" * 70)
    lines.append("📱 Home Assistant Devices")
    lines.append("=" * 70)

    for device in sorted(devices, key=lambda x: x.get("name") or x.get("name_by_user") or ""):
        device_id = device.get("id", "")
        name = device.get("name_by_user") or device.get("name") or "(unnamed)"
        manufacturer = device.get("manufacturer", "")
        model = device.get("model", "")
        area_id = device.get("area_id", "")
        labels = device.get("labels", [])
        via_device_id = device.get("via_device_id", "")
        disabled_by = device.get("disabled_by")
        entry_type = device.get("entry_type", "")

        lines.append("")
        status_icon = "⚫" if disabled_by else "🟢"
        lines.append(f"{status_icon} {name}")
        lines.append(f"   ID: {device_id}")
        if manufacturer or model:
            lines.append(f"   Device: {manufacturer} {model}".strip())
        if area_id:
            lines.append(f"   Area: {area_id}")
        if labels:
            lines.append(f"   Labels: {', '.join(labels)}")
        if via_device_id:
            lines.append(f"   Via: {via_device_id}")
        if entry_type:
            lines.append(f"   Type: {entry_type}")
        if disabled_by:
            lines.append(f"   Disabled by: {disabled_by}")

    lines.append("")
    lines.append("-" * 70)
    lines.append(f"Total: {len(devices)} devices")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--search",
    "-s",
    type=str,
    help="Filter devices by name (case-insensitive)",
)
@click.option(
    "--label",
    "-l",
    type=str,
    help="Filter devices by label ID",
)
@click.option(
    "--area",
    "-a",
    type=str,
    help="Filter devices by area ID",
)
@click.option(
    "--manufacturer",
    "-m",
    type=str,
    help="Filter devices by manufacturer (case-insensitive)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(
    search: str | None,
    label: str | None,
    area: str | None,
    manufacturer: str | None,
    output_json: bool,
) -> None:
    """
    List all devices from Home Assistant's device registry.

    Devices represent physical or virtual hardware in your smart home.

    Examples:

        uv run list-devices.py

        uv run list-devices.py --search "Eve"

        uv run list-devices.py --label thread

        uv run list-devices.py --area living_room

        uv run list-devices.py --manufacturer "Apple" --json
    """
    try:
        result = websocket_command("config/device_registry/list")

        # Result is a list of devices
        devices = result if isinstance(result, list) else []

        # Apply filters
        if search:
            search_lower = search.lower()
            devices = [
                device
                for device in devices
                if search_lower in (device.get("name_by_user") or device.get("name") or "").lower()
            ]

        if label:
            devices = [device for device in devices if label in device.get("labels", [])]

        if area:
            devices = [device for device in devices if device.get("area_id") == area]

        if manufacturer:
            manufacturer_lower = manufacturer.lower()
            devices = [device for device in devices if manufacturer_lower in (device.get("manufacturer") or "").lower()]

        if output_json:
            click.echo(json.dumps(devices, indent=2))
        else:
            formatted = format_devices(devices)
            click.echo(formatted)

        sys.exit(0)

    except Exception as error:
        error_data = {"error": str(error)}
        if output_json:
            click.echo(json.dumps(error_data, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
