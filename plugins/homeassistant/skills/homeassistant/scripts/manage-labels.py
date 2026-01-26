#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Label Registry Management Script

Create, update, and delete labels via WebSocket API.

Usage:
    uv run manage-labels.py create --name "Thread Devices" --color red --icon mdi:network
    uv run manage-labels.py update --label-id thread_devices --name "Thread" --color blue
    uv run manage-labels.py delete --label-id thread_devices --confirm
    uv run manage-labels.py --help
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


@click.group()
def cli() -> None:
    """Manage Home Assistant labels (create, update, delete)."""
    pass


@cli.command()
@click.option("--name", required=True, help="Label name")
@click.option("--color", type=str, help="Label color (e.g., red, blue, green)")
@click.option("--icon", type=str, help="Material Design icon (e.g., mdi:network)")
@click.option("--description", type=str, help="Label description")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def create(
    name: str,
    color: str | None,
    icon: str | None,
    description: str | None,
    output_json: bool,
) -> None:
    """Create a new label."""
    try:
        params: dict[str, Any] = {"name": name}
        if color:
            params["color"] = color
        if icon:
            params["icon"] = icon
        if description:
            params["description"] = description

        result = websocket_command_with_params("config/label_registry/create", params)

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            label_id = result.get("label_id", "")
            click.echo(f"✅ Created label: {name} (ID: {label_id})")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--label-id", required=True, help="Label ID to update")
@click.option("--name", type=str, help="New label name")
@click.option("--color", type=str, help="New label color")
@click.option("--icon", type=str, help="New icon (empty string to remove)")
@click.option("--description", type=str, help="New description (empty string to remove)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def update(
    label_id: str,
    name: str | None,
    color: str | None,
    icon: str | None,
    description: str | None,
    output_json: bool,
) -> None:
    """Update an existing label."""
    try:
        params: dict[str, Any] = {"label_id": label_id}
        if name is not None:
            params["name"] = name
        if color is not None:
            params["color"] = color
        if icon is not None:
            params["icon"] = icon if icon != "" else None
        if description is not None:
            params["description"] = description if description != "" else None

        result = websocket_command_with_params("config/label_registry/update", params)

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"✅ Updated label: {label_id}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--label-id", required=True, help="Label ID to delete")
@click.option("--confirm", is_flag=True, help="Confirm destructive operation")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def delete(
    label_id: str,
    confirm: bool,
    output_json: bool,
) -> None:
    """Delete a label (requires --confirm)."""
    try:
        if not confirm:
            click.echo("⚠️  This will permanently delete the label.", err=True)
            click.echo("   Run with --confirm to proceed.", err=True)
            sys.exit(1)

        params: dict[str, Any] = {"label_id": label_id}
        websocket_command_with_params("config/label_registry/delete", params)

        if output_json:
            click.echo(json.dumps({"deleted": label_id}, indent=2))
        else:
            click.echo(f"✅ Deleted label: {label_id}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
