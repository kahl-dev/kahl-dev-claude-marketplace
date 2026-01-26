#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Integration Management Script

Manage config entries (integrations) via WebSocket API.

Usage:
    uv run manage-integrations.py reload --entry-id abc123
    uv run manage-integrations.py disable --entry-id abc123
    uv run manage-integrations.py enable --entry-id abc123
    uv run manage-integrations.py remove --entry-id abc123 --confirm
    uv run manage-integrations.py --help
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


@click.group()
def cli() -> None:
    """Manage Home Assistant integrations (reload, disable, enable, remove)."""
    pass


@cli.command()
@click.option("--entry-id", required=True, help="Config entry ID (get from list-integrations.py --json)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def reload(entry_id: str, output_json: bool) -> None:
    """Reload an integration."""
    try:
        result = websocket_command("config_entries/reload", {"entry_id": entry_id})

        if output_json:
            click.echo(json.dumps({"reloaded": entry_id, "result": result}, indent=2))
        else:
            click.echo(f"✅ Reloaded integration: {entry_id}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--entry-id", required=True, help="Config entry ID (get from list-integrations.py --json)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def disable(entry_id: str, output_json: bool) -> None:
    """Disable an integration."""
    try:
        result = websocket_command(
            "config_entries/disable",
            {
                "entry_id": entry_id,
                "disabled_by": "user",
            },
        )

        if output_json:
            click.echo(json.dumps({"disabled": entry_id, "result": result}, indent=2))
        else:
            click.echo(f"✅ Disabled integration: {entry_id}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--entry-id", required=True, help="Config entry ID (get from list-integrations.py --json)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def enable(entry_id: str, output_json: bool) -> None:
    """Enable a disabled integration."""
    try:
        result = websocket_command(
            "config_entries/disable",
            {
                "entry_id": entry_id,
                "disabled_by": None,
            },
        )

        if output_json:
            click.echo(json.dumps({"enabled": entry_id, "result": result}, indent=2))
        else:
            click.echo(f"✅ Enabled integration: {entry_id}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--entry-id", required=True, help="Config entry ID (get from list-integrations.py --json)")
@click.option("--confirm", is_flag=True, help="Confirm destructive operation")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def remove(entry_id: str, confirm: bool, output_json: bool) -> None:
    """Remove an integration (requires --confirm)."""
    try:
        if not confirm:
            click.echo("⚠️  This will permanently remove the integration.", err=True)
            click.echo("   All associated entities and devices will be removed.", err=True)
            click.echo("   Run with --confirm to proceed.", err=True)
            sys.exit(1)

        result = websocket_command("config_entries/delete", {"entry_id": entry_id})

        if output_json:
            click.echo(json.dumps({"removed": entry_id, "result": result}, indent=2))
        else:
            click.echo(f"✅ Removed integration: {entry_id}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
