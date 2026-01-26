#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Zone Management Script

List, create, update, and delete zones via WebSocket API.

Usage:
    uv run manage-zones.py list
    uv run manage-zones.py create --name "Office" --latitude 52.52 --longitude 13.405 --radius 100
    uv run manage-zones.py update --zone-id office --radius 200
    uv run manage-zones.py delete --zone-id office --confirm
    uv run manage-zones.py --help
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


# Configuration from environment (validated at runtime for --help support)
HA_URL: str = ""
HA_TOKEN: str = ""
WS_TIMEOUT = 30


def _validate_config() -> None:
    """Validate required environment variables."""
    global HA_URL, HA_TOKEN
    HA_URL = get_required_env(
        "HOMEASSISTANT_URL",
        "Your HA instance URL, e.g., http://homeassistant.local:8123",
    )
    HA_TOKEN = get_required_env(
        "HOMEASSISTANT_TOKEN",
        "Get from: HA → Profile → Security → Long-Lived Access Tokens",
    )


def get_websocket_url(base_url: str) -> str:
    """Convert HTTP(S) URL to WebSocket URL using proper parsing."""
    parsed = urlparse(base_url)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    base_path = parsed.path.rstrip("/")
    ws_path = f"{base_path}/api/websocket"
    return urlunparse(parsed._replace(scheme=ws_scheme, path=ws_path))


def websocket_command(command_type: str, params: dict[str, Any] | None = None) -> Any:
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
        message: dict[str, Any] = {"id": 1, "type": command_type}
        if params:
            message.update(params)
        ws.send(json.dumps(message))
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


def format_zones(zones: list[dict[str, Any]]) -> str:
    """Format zones for human-readable output."""
    lines: list[str] = []

    if not zones:
        return "No zones found."

    lines.append("")
    lines.append("=" * 60)
    lines.append("📍 Home Assistant Zones")
    lines.append("=" * 60)

    for zone in sorted(zones, key=lambda x: x.get("name", "")):
        zone_id = zone.get("id", "")
        name = zone.get("name", "")
        latitude = zone.get("latitude", 0)
        longitude = zone.get("longitude", 0)
        radius = zone.get("radius", 100)
        icon = zone.get("icon", "")
        passive = zone.get("passive", False)

        lines.append("")
        lines.append(f"📍 {name}")
        lines.append(f"   ID: {zone_id}")
        lines.append(f"   Location: {latitude}, {longitude}")
        lines.append(f"   Radius: {radius}m")
        if icon:
            lines.append(f"   Icon: {icon}")
        if passive:
            lines.append("   Passive: Yes (won't trigger zone events)")

    lines.append("")
    lines.append("-" * 60)
    lines.append(f"Total: {len(zones)} zones")
    lines.append("")

    return "\n".join(lines)


@click.group()
def cli() -> None:
    """Manage Home Assistant zones (list, create, update, delete)."""
    pass


@cli.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def list_zones(output_json: bool) -> None:
    """List all zones."""
    _validate_config()
    try:
        result = websocket_command("zone/list")
        zones = result if isinstance(result, list) else []

        if output_json:
            click.echo(json.dumps(zones, indent=2))
        else:
            formatted = format_zones(zones)
            click.echo(formatted)

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--name", required=True, help="Zone name")
@click.option("--latitude", required=True, type=float, help="Latitude")
@click.option("--longitude", required=True, type=float, help="Longitude")
@click.option("--radius", type=float, default=100, help="Radius in meters (default: 100)")
@click.option("--icon", type=str, help="Material Design icon (e.g., mdi:office-building)")
@click.option("--passive", is_flag=True, help="Passive zone (won't trigger zone events)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def create(
    name: str,
    latitude: float,
    longitude: float,
    radius: float,
    icon: str | None,
    passive: bool,
    output_json: bool,
) -> None:
    """Create a new zone."""
    try:
        params: dict[str, Any] = {
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius,
        }
        if icon:
            params["icon"] = icon
        if passive:
            params["passive"] = passive

        result = websocket_command("zone/create", params)

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            zone_id = result.get("id", "")
            click.echo(f"✅ Created zone: {name} (ID: {zone_id})")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--zone-id", required=True, help="Zone ID to update")
@click.option("--name", type=str, help="New name")
@click.option("--latitude", type=float, help="New latitude")
@click.option("--longitude", type=float, help="New longitude")
@click.option("--radius", type=float, help="New radius in meters")
@click.option("--icon", type=str, help="New icon (empty to remove)")
@click.option("--passive", type=bool, help="Passive zone setting")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def update(
    zone_id: str,
    name: str | None,
    latitude: float | None,
    longitude: float | None,
    radius: float | None,
    icon: str | None,
    passive: bool | None,
    output_json: bool,
) -> None:
    """Update an existing zone."""
    try:
        params: dict[str, Any] = {"zone_id": zone_id}

        if name is not None:
            params["name"] = name
        if latitude is not None:
            params["latitude"] = latitude
        if longitude is not None:
            params["longitude"] = longitude
        if radius is not None:
            params["radius"] = radius
        if icon is not None:
            params["icon"] = icon if icon != "" else None
        if passive is not None:
            params["passive"] = passive

        result = websocket_command("zone/update", params)

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"✅ Updated zone: {zone_id}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--zone-id", required=True, help="Zone ID to delete")
@click.option("--confirm", is_flag=True, help="Confirm destructive operation")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def delete(
    zone_id: str,
    confirm: bool,
    output_json: bool,
) -> None:
    """Delete a zone (requires --confirm)."""
    try:
        if not confirm:
            click.echo("⚠️  This will permanently delete the zone.", err=True)
            click.echo("   Automations using this zone may break.", err=True)
            click.echo("   Run with --confirm to proceed.", err=True)
            sys.exit(1)

        params: dict[str, Any] = {"zone_id": zone_id}
        websocket_command("zone/delete", params)

        if output_json:
            click.echo(json.dumps({"deleted": zone_id}, indent=2))
        else:
            click.echo(f"✅ Deleted zone: {zone_id}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
