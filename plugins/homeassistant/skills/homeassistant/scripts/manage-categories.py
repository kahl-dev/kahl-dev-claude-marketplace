#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Category Registry Management Script

Create, update, and delete categories via WebSocket API.

Usage:
    uv run manage-categories.py create --scope automation --name "Climate Control" --icon mdi:thermostat
    uv run manage-categories.py update --scope automation --category-id climate_control --name "HVAC"
    uv run manage-categories.py delete --scope automation --category-id climate_control --confirm
    uv run manage-categories.py --help
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

VALID_SCOPES = ["automation", "entity", "helper", "script", "scene"]


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
    """Manage Home Assistant categories (create, update, delete)."""
    pass


@cli.command()
@click.option(
    "--scope",
    required=True,
    type=click.Choice(VALID_SCOPES),
    help="Category scope",
)
@click.option("--name", required=True, help="Category name")
@click.option("--icon", type=str, help="Material Design icon (e.g., mdi:thermostat)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def create(
    scope: str,
    name: str,
    icon: str | None,
    output_json: bool,
) -> None:
    """Create a new category."""
    try:
        params: dict[str, Any] = {"scope": scope, "name": name}
        if icon:
            params["icon"] = icon

        result = websocket_command_with_params("config/category_registry/create", params)

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            category_id = result.get("category_id", "")
            click.echo(f"✅ Created category: {name} (ID: {category_id}, Scope: {scope})")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--scope",
    required=True,
    type=click.Choice(VALID_SCOPES),
    help="Category scope",
)
@click.option("--category-id", required=True, help="Category ID to update (ULID from create output, not the name)")
@click.option("--name", type=str, help="New category name")
@click.option("--icon", type=str, help="New icon (empty to remove)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def update(
    scope: str,
    category_id: str,
    name: str | None,
    icon: str | None,
    output_json: bool,
) -> None:
    """Update an existing category."""
    try:
        params: dict[str, Any] = {"scope": scope, "category_id": category_id}
        if name is not None:
            params["name"] = name
        if icon is not None:
            params["icon"] = icon if icon != "" else None

        result = websocket_command_with_params("config/category_registry/update", params)

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"✅ Updated category: {category_id}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--scope",
    required=True,
    type=click.Choice(VALID_SCOPES),
    help="Category scope",
)
@click.option("--category-id", required=True, help="Category ID to delete (ULID from create/list output, not the name)")
@click.option("--confirm", is_flag=True, help="Confirm destructive operation")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def delete(
    scope: str,
    category_id: str,
    confirm: bool,
    output_json: bool,
) -> None:
    """Delete a category (requires --confirm)."""
    try:
        if not confirm:
            click.echo("⚠️  This will permanently delete the category.", err=True)
            click.echo("   Items in this category will become uncategorized.", err=True)
            click.echo("   Run with --confirm to proceed.", err=True)
            sys.exit(1)

        params: dict[str, Any] = {"scope": scope, "category_id": category_id}
        websocket_command_with_params("config/category_registry/delete", params)

        if output_json:
            click.echo(json.dumps({"deleted": category_id, "scope": scope}, indent=2))
        else:
            click.echo(f"✅ Deleted category: {category_id} (Scope: {scope})")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
