#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Floor Registry Script

List all floors from Home Assistant's floor registry via WebSocket API.

Usage:
    uv run list-floors.py
    uv run list-floors.py --search "ground"
    uv run list-floors.py --json
    uv run list-floors.py --help
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


def format_floors(floors: list[dict[str, Any]]) -> str:
    """Format floors for human-readable output."""
    lines: list[str] = []

    if not floors:
        return "No floors found."

    lines.append("")
    lines.append("=" * 60)
    lines.append("🏢 Home Assistant Floors")
    lines.append("=" * 60)

    # Sort by level if available
    for floor in sorted(floors, key=lambda x: x.get("level", 0)):
        floor_id = floor.get("floor_id", "")
        name = floor.get("name", "")
        level = floor.get("level", 0)
        icon = floor.get("icon", "")
        aliases = floor.get("aliases", [])

        lines.append("")
        lines.append(f"🏠 {name}")
        lines.append(f"   ID: {floor_id}")
        lines.append(f"   Level: {level}")
        if icon:
            lines.append(f"   Icon: {icon}")
        if aliases:
            lines.append(f"   Aliases: {', '.join(aliases)}")

    lines.append("")
    lines.append("-" * 60)
    lines.append(f"Total: {len(floors)} floors")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--search",
    "-s",
    type=str,
    help="Filter floors by name (case-insensitive)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(
    search: str | None,
    output_json: bool,
) -> None:
    """
    List all floors from Home Assistant's floor registry.

    Floors organize areas vertically in multi-story buildings.

    Examples:

        uv run list-floors.py

        uv run list-floors.py --search "ground"

        uv run list-floors.py --json
    """
    try:
        result = websocket_command("config/floor_registry/list")

        # Result is a list of floors
        floors = result if isinstance(result, list) else []

        # Filter by search term if specified
        if search:
            search_lower = search.lower()
            floors = [floor for floor in floors if search_lower in floor.get("name", "").lower()]

        if output_json:
            click.echo(json.dumps(floors, indent=2))
        else:
            formatted = format_floors(floors)
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
