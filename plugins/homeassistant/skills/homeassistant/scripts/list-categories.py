#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Category Registry Script

List all categories from Home Assistant's category registry via WebSocket API.

Usage:
    uv run list-categories.py --scope automation
    uv run list-categories.py --scope entity
    uv run list-categories.py --search "climate"
    uv run list-categories.py --json
    uv run list-categories.py --help
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


def websocket_command_with_params(command_type: str, params: dict[str, Any]) -> dict[str, Any]:
    """Execute WebSocket command with parameters and return result."""
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
        message = {"id": 1, "type": command_type, **params}
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


def format_categories(categories: list[dict[str, Any]], scope: str) -> str:
    """Format categories for human-readable output."""
    lines: list[str] = []

    if not categories:
        return f"No categories found for scope: {scope}"

    lines.append("")
    lines.append("=" * 60)
    lines.append(f"📂 Home Assistant Categories ({scope})")
    lines.append("=" * 60)

    for category in sorted(categories, key=lambda x: x.get("name", "")):
        category_id = category.get("category_id", "")
        name = category.get("name", "")
        icon = category.get("icon", "")

        lines.append("")
        lines.append(f"📁 {name}")
        lines.append(f"   ID: {category_id}")
        if icon:
            lines.append(f"   Icon: {icon}")

    lines.append("")
    lines.append("-" * 60)
    lines.append(f"Total: {len(categories)} categories")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--scope",
    required=True,
    type=click.Choice(["automation", "entity", "helper", "script", "scene"]),
    help="Category scope to list",
)
@click.option(
    "--search",
    "-s",
    type=str,
    help="Filter categories by name (case-insensitive)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(
    scope: str,
    search: str | None,
    output_json: bool,
) -> None:
    """
    List all categories from Home Assistant's category registry.

    Categories organize automations, entities, helpers, scripts, and scenes.

    Examples:

        uv run list-categories.py --scope automation

        uv run list-categories.py --scope entity --search "climate"

        uv run list-categories.py --scope helper --json
    """
    try:
        result = websocket_command_with_params("config/category_registry/list", {"scope": scope})

        # Result is a list of categories
        categories = result if isinstance(result, list) else []

        # Filter by search term if specified
        if search:
            search_lower = search.lower()
            categories = [cat for cat in categories if search_lower in cat.get("name", "").lower()]

        if output_json:
            click.echo(json.dumps(categories, indent=2))
        else:
            formatted = format_categories(categories, scope)
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
