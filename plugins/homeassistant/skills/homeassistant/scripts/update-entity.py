#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Entity Registry Update Script

Update entity properties (name, icon, area, labels, disabled state) via WebSocket API.

Usage:
    uv run update-entity.py --entity-id light.bedroom --name "Bedroom Light"
    uv run update-entity.py --entity-id sensor.temp --area living_room
    uv run update-entity.py --entity-id switch.pump --labels pool,outdoor
    uv run update-entity.py --entity-id light.old --disabled-by user
    uv run update-entity.py --entity-id light.old --disabled-by ""  # Re-enable
    uv run update-entity.py --help
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


@click.command()
@click.option("--entity-id", required=True, help="Entity ID to update (e.g., light.bedroom)")
@click.option("--name", type=str, help="Custom friendly name (empty to use default)")
@click.option("--icon", type=str, help="Custom icon (e.g., mdi:lamp, empty to remove)")
@click.option("--area", type=str, help="Area ID (empty to remove)")
@click.option("--labels", type=str, help="Comma-separated label IDs (replaces existing)")
@click.option(
    "--disabled-by",
    type=click.Choice(["user", ""]),
    help="Disable entity ('user') or enable (empty string)",
)
@click.option("--hidden-by", type=click.Choice(["user", ""]), help="Hide entity ('user') or show (empty)")
@click.option("--new-entity-id", type=str, help="Rename entity to new ID")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def main(
    entity_id: str,
    name: str | None,
    icon: str | None,
    area: str | None,
    labels: str | None,
    disabled_by: str | None,
    hidden_by: str | None,
    new_entity_id: str | None,
    output_json: bool,
) -> None:
    """
    Update entity properties in Home Assistant's entity registry.

    Changes the metadata for an entity (name, icon, area, labels, etc.).
    Does NOT control the entity state - use call-service.py or toggle.py for that.

    Examples:

        uv run update-entity.py --entity-id light.bedroom --name "Main Light"

        uv run update-entity.py --entity-id sensor.temp --area living_room

        uv run update-entity.py --entity-id switch.pump --labels pool,outdoor

        uv run update-entity.py --entity-id light.old --disabled-by user

        uv run update-entity.py --entity-id light.old --disabled-by ""

        uv run update-entity.py --entity-id light.old_name --new-entity-id light.new_name
    """
    try:
        params: dict[str, Any] = {"entity_id": entity_id}

        if name is not None:
            params["name"] = name if name != "" else None
        if icon is not None:
            params["icon"] = icon if icon != "" else None
        if area is not None:
            params["area_id"] = area if area != "" else None
        if labels is not None:
            params["labels"] = [label.strip() for label in labels.split(",")] if labels else []
        if disabled_by is not None:
            params["disabled_by"] = disabled_by if disabled_by != "" else None
        if hidden_by is not None:
            params["hidden_by"] = hidden_by if hidden_by != "" else None
        if new_entity_id is not None:
            params["new_entity_id"] = new_entity_id

        result = websocket_command_with_params("config/entity_registry/update", params)

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            updated_id = result.get("entity_id", entity_id)
            if new_entity_id and new_entity_id != entity_id:
                click.echo(f"✅ Renamed entity: {entity_id} → {updated_id}")
            else:
                click.echo(f"✅ Updated entity: {updated_id}")

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
