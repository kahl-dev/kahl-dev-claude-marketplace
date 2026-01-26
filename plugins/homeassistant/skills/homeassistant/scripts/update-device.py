#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Device Registry Update Script

Update device properties (labels, area, name) via WebSocket API.
Supports bulk operations with continue-all default behavior.

Usage:
    uv run update-device.py --device-id abc123 --labels thread,heizung
    uv run update-device.py --device-ids abc,def,ghi --labels thread,heizung
    uv run update-device.py --device-id abc123 --area living_room
    uv run update-device.py --device-id abc123 --name "My Device"
    uv run update-device.py --from-json device-updates.json
    uv run update-device.py --help
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


def update_single_device(
    device_id: str,
    labels: list[str] | None,
    area_id: str | None,
    name_by_user: str | None,
    disabled_by: str | None,
) -> dict[str, Any]:
    """Update a single device and return the result."""
    params: dict[str, Any] = {"device_id": device_id}

    if labels is not None:
        params["labels"] = labels
    if area_id is not None:
        params["area_id"] = area_id if area_id != "" else None
    if name_by_user is not None:
        params["name_by_user"] = name_by_user if name_by_user != "" else None
    if disabled_by is not None:
        params["disabled_by"] = disabled_by if disabled_by != "" else None

    return websocket_command_with_params("config/device_registry/update", params)


def format_results(results: dict[str, Any]) -> str:
    """Format bulk update results for human-readable output."""
    lines: list[str] = []
    succeeded = results.get("succeeded", [])
    failed = results.get("failed", [])

    lines.append("")
    lines.append("=" * 60)
    lines.append("📱 Device Update Results")
    lines.append("=" * 60)

    if succeeded:
        lines.append("")
        lines.append(f"✅ Succeeded: {len(succeeded)}")
        for item in succeeded:
            device_id = item.get("device_id", "")
            name = item.get("name", "")
            lines.append(f"   • {name} ({device_id})")

    if failed:
        lines.append("")
        lines.append(f"❌ Failed: {len(failed)}")
        for item in failed:
            device_id = item.get("device_id", "")
            error = item.get("error", "Unknown error")
            lines.append(f"   • {device_id}: {error}")

    lines.append("")
    lines.append("-" * 60)
    total = len(succeeded) + len(failed)
    lines.append(f"Total: {len(succeeded)}/{total} succeeded")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--device-id",
    type=str,
    help="Single device ID to update (get from list-devices.py --json)",
)
@click.option(
    "--device-ids",
    type=str,
    help="Comma-separated device IDs for bulk update (get IDs from list-devices.py)",
)
@click.option(
    "--from-json",
    "from_json_file",
    type=click.Path(exists=True),
    help="JSON file with device updates: [{device_id, labels?, area_id?, name?}, ...]",
)
@click.option(
    "--labels",
    type=str,
    help="Comma-separated label IDs to assign (replaces existing labels)",
)
@click.option(
    "--area",
    type=str,
    help="Area ID to assign (empty string to remove)",
)
@click.option(
    "--name",
    type=str,
    help="Custom name (empty string to remove)",
)
@click.option(
    "--disabled-by",
    type=click.Choice(["user", ""]),
    help="Disable device ('user') or enable (empty string)",
)
@click.option(
    "--fail-fast",
    is_flag=True,
    help="Stop on first error (default: continue all)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(
    device_id: str | None,
    device_ids: str | None,
    from_json_file: str | None,
    labels: str | None,
    area: str | None,
    name: str | None,
    disabled_by: str | None,
    fail_fast: bool,
    output_json: bool,
) -> None:
    """
    Update device properties in Home Assistant's device registry.

    Supports single device, multiple devices, or JSON file input.
    Default behavior: continue on errors, report summary at end.

    Examples:

        uv run update-device.py --device-id abc123 --labels thread,heizung

        uv run update-device.py --device-ids abc,def,ghi --labels thread,batterie

        uv run update-device.py --device-id abc123 --area living_room

        uv run update-device.py --device-id abc123 --name "My Custom Name"

        uv run update-device.py --from-json device-updates.json

    JSON file format:

        [
          {"device_id": "abc123", "labels": ["thread", "heizung"]},
          {"device_id": "def456", "area_id": "living_room", "name_by_user": "TV"}
        ]
    """
    try:
        # Parse input
        updates: list[dict[str, Any]] = []

        if from_json_file:
            with open(from_json_file) as file:
                updates = json.load(file)
                if not isinstance(updates, list):
                    raise ValueError("JSON file must contain a list of device updates")

        elif device_ids:
            # Bulk update with same labels/area/name for all
            ids = [device_id.strip() for device_id in device_ids.split(",")]
            label_list = [label.strip() for label in labels.split(",")] if labels else None
            for device_id_item in ids:
                update: dict[str, Any] = {"device_id": device_id_item}
                if label_list is not None:
                    update["labels"] = label_list
                if area is not None:
                    update["area_id"] = area
                if name is not None:
                    update["name_by_user"] = name
                if disabled_by is not None:
                    update["disabled_by"] = disabled_by
                updates.append(update)

        elif device_id:
            # Single device update
            label_list = [label.strip() for label in labels.split(",")] if labels else None
            update = {"device_id": device_id}
            if label_list is not None:
                update["labels"] = label_list
            if area is not None:
                update["area_id"] = area
            if name is not None:
                update["name_by_user"] = name
            if disabled_by is not None:
                update["disabled_by"] = disabled_by
            updates.append(update)

        else:
            raise click.UsageError("Provide --device-id, --device-ids, or --from-json")

        if not updates:
            raise click.UsageError("No device updates specified")

        # Execute updates
        results: dict[str, list[dict[str, Any]]] = {"succeeded": [], "failed": []}

        for update in updates:
            update_device_id = update.get("device_id")
            if not update_device_id:
                results["failed"].append({"device_id": "(missing)", "error": "No device_id in update"})
                if fail_fast:
                    break
                continue

            try:
                result = update_single_device(
                    device_id=update_device_id,
                    labels=update.get("labels"),
                    area_id=update.get("area_id"),
                    name_by_user=update.get("name_by_user"),
                    disabled_by=update.get("disabled_by"),
                )
                device_result = result if isinstance(result, dict) else {}
                results["succeeded"].append(
                    {
                        "device_id": update_device_id,
                        "name": device_result.get("name_by_user") or device_result.get("name") or "(unnamed)",
                    }
                )
            except Exception as error:
                results["failed"].append({"device_id": update_device_id, "error": str(error)})
                if fail_fast:
                    break

        if output_json:
            click.echo(json.dumps(results, indent=2))
        else:
            formatted = format_results(results)
            click.echo(formatted)

        # Exit code based on results
        if results["failed"]:
            sys.exit(1)
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
