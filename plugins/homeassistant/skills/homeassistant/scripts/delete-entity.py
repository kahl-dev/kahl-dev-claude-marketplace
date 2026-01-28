#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Delete Entity Script

Delete orphaned entities from the entity registry via WebSocket API.
Dry-run by default. Requires --confirm for actual deletion.

Usage:
    uv run delete-entity.py automation.old_test
    uv run delete-entity.py automation.old_test --confirm
    uv run delete-entity.py --help
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


def websocket_command(command_type: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
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
        message = {"id": 1, "type": command_type}
        if data:
            message.update(data)
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


def get_entity_registry_entry(entity_id: str) -> dict[str, Any] | None:
    """Get entity registry entry for an entity_id, or None if not in registry."""
    result = websocket_command("config/entity_registry/list")
    entries = result if isinstance(result, list) else []

    for entry in entries:
        if entry.get("entity_id") == entity_id:
            return entry

    return None


@click.command()
@click.argument("entity_id")
@click.option(
    "--confirm",
    is_flag=True,
    help="Actually delete the entity (without this flag, only shows what would happen)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(
    entity_id: str,
    confirm: bool,
    output_json: bool,
) -> None:
    """
    Delete an entity from the Home Assistant entity registry.

    By default runs in dry-run mode (shows what would be deleted).
    Use --confirm to actually delete the entity.

    Note: Only entities in the entity registry can be deleted via API.
    YAML-defined entities must be removed from configuration files.

    Examples:

        uv run delete-entity.py automation.old_test

        uv run delete-entity.py automation.old_test --confirm

        uv run delete-entity.py sensor.orphaned --json
    """
    _validate_config()

    try:
        # Check if entity exists in registry
        entry = get_entity_registry_entry(entity_id)

        if entry is None:
            # Entity not in registry - likely YAML-defined
            error_msg = f"Entity '{entity_id}' is not in the entity registry.\n\n"
            error_msg += "This usually means:\n"
            error_msg += "1. The entity is defined in YAML configuration (edit config files and restart HA)\n"
            error_msg += "2. The entity_id is misspelled\n"
            error_msg += "3. The entity was already deleted\n\n"
            error_msg += "Tip: Use list-entities.py to verify the entity_id exists."

            if output_json:
                click.echo(json.dumps({"error": error_msg, "entity_id": entity_id, "in_registry": False}, indent=2))
            else:
                click.echo(f"❌ {error_msg}", err=True)
            sys.exit(1)

        # Extract entity info
        platform = entry.get("platform", "unknown")
        name = entry.get("name") or entry.get("original_name", "unnamed")
        device_id = entry.get("device_id")
        disabled_by = entry.get("disabled_by")
        hidden_by = entry.get("hidden_by")

        # Build info dict
        info = {
            "entity_id": entity_id,
            "name": name,
            "platform": platform,
            "device_id": device_id,
            "disabled_by": disabled_by,
            "hidden_by": hidden_by,
            "in_registry": True,
        }

        # Check if integration-managed (has device_id usually means integration)
        is_integration_managed = device_id is not None

        if not confirm:
            # Dry-run mode
            if output_json:
                info["action"] = "dry_run"
                info["would_delete"] = True
                info["integration_managed"] = is_integration_managed
                click.echo(json.dumps(info, indent=2))
            else:
                click.echo("")
                click.echo("=" * 60)
                click.echo("🗑️  Delete Entity (DRY RUN)")
                click.echo("=" * 60)
                click.echo("")
                click.echo(f"   Entity ID: {entity_id}")
                click.echo(f"   Name: {name}")
                click.echo(f"   Platform: {platform}")
                if device_id:
                    click.echo(f"   Device ID: {device_id}")
                if disabled_by:
                    click.echo(f"   Disabled by: {disabled_by}")

                if is_integration_managed:
                    click.echo("")
                    click.echo(f"⚠️  Warning: This entity is managed by integration '{platform}'.")
                    click.echo("   It may be recreated automatically after HA restart.")
                    click.echo("   Consider disabling/removing the integration instead.")

                click.echo("")
                click.echo("-" * 60)
                click.echo("This is a DRY RUN. No changes made.")
                click.echo("Use --confirm to actually delete the entity.")
                click.echo("")

            sys.exit(0)

        # Actual deletion
        if is_integration_managed and not output_json:
            click.echo(f"⚠️  Warning: Entity is managed by integration '{platform}'.")
            click.echo("   It may be recreated after HA restart.")
            click.echo("")

        # Execute deletion
        websocket_command("config/entity_registry/remove", {"entity_id": entity_id})

        if output_json:
            info["action"] = "deleted"
            info["success"] = True
            click.echo(json.dumps(info, indent=2))
        else:
            click.echo(f"✅ Deleted entity: {entity_id}")
            if is_integration_managed:
                click.echo(f"   Note: May reappear if integration '{platform}' recreates it.")

        sys.exit(0)

    except Exception as error:
        error_data = {"error": str(error), "entity_id": entity_id}
        if output_json:
            click.echo(json.dumps(error_data, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
