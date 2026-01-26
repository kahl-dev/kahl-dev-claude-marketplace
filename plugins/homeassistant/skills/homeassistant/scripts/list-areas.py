#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Area Registry Script

List all areas from Home Assistant's area registry via WebSocket API.

Usage:
    uv run list-areas.py
    uv run list-areas.py --search "living"
    uv run list-areas.py --floor ground_floor
    uv run list-areas.py --json
    uv run list-areas.py --help
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


def format_areas(areas: list[dict[str, Any]]) -> str:
    """Format areas for human-readable output."""
    lines: list[str] = []

    if not areas:
        return "No areas found."

    lines.append("")
    lines.append("=" * 60)
    lines.append("🏠 Home Assistant Areas")
    lines.append("=" * 60)

    for area in sorted(areas, key=lambda x: x.get("name", "")):
        area_id = area.get("area_id", "")
        name = area.get("name", "")
        floor_id = area.get("floor_id", "")
        icon = area.get("icon", "")
        aliases = area.get("aliases", [])
        labels = area.get("labels", [])

        lines.append("")
        lines.append(f"📍 {name}")
        lines.append(f"   ID: {area_id}")
        if floor_id:
            lines.append(f"   Floor: {floor_id}")
        if icon:
            lines.append(f"   Icon: {icon}")
        if aliases:
            lines.append(f"   Aliases: {', '.join(aliases)}")
        if labels:
            lines.append(f"   Labels: {', '.join(labels)}")

    lines.append("")
    lines.append("-" * 60)
    lines.append(f"Total: {len(areas)} areas")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--search",
    "-s",
    type=str,
    help="Filter areas by name (case-insensitive)",
)
@click.option(
    "--floor",
    "-f",
    type=str,
    help="Filter areas by floor ID",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(
    search: str | None,
    floor: str | None,
    output_json: bool,
) -> None:
    """
    List all areas from Home Assistant's area registry.

    Areas organize devices and entities by physical location.

    Examples:

        uv run list-areas.py

        uv run list-areas.py --search "living"

        uv run list-areas.py --floor ground_floor

        uv run list-areas.py --json
    """
    _validate_config()
    try:
        result = websocket_command("config/area_registry/list")

        # Result is a list of areas
        areas = result if isinstance(result, list) else []

        # Apply filters
        if search:
            search_lower = search.lower()
            areas = [area for area in areas if search_lower in area.get("name", "").lower()]

        if floor:
            areas = [area for area in areas if area.get("floor_id") == floor]

        if output_json:
            click.echo(json.dumps(areas, indent=2))
        else:
            formatted = format_areas(areas)
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
