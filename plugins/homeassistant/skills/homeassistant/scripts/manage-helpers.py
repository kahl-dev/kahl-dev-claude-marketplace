#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Helper Management Script

Unified CRUD for all helper types via WebSocket API.

Supported types: input_boolean, input_number, input_text, input_select,
input_datetime, input_button, counter, timer, schedule, todo, date, time

Usage:
    uv run manage-helpers.py list --type input_boolean
    uv run manage-helpers.py create --type input_number --name "Target Temp" --min 15 --max 30
    uv run manage-helpers.py update --type input_number --id input_number.target_temp --max 35
    uv run manage-helpers.py delete --type input_number --id input_number.target_temp --confirm
    uv run manage-helpers.py --help
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

HELPER_TYPES = [
    "input_boolean",
    "input_number",
    "input_text",
    "input_select",
    "input_datetime",
    "input_button",
    "counter",
    "timer",
    "schedule",
    "todo",
    "date",
    "time",
]


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


def format_helpers(helpers: list[dict[str, Any]], helper_type: str) -> str:
    """Format helpers for human-readable output."""
    lines: list[str] = []

    if not helpers:
        return f"No {helper_type} helpers found."

    lines.append("")
    lines.append("=" * 70)
    lines.append(f"🔧 Home Assistant Helpers ({helper_type})")
    lines.append("=" * 70)

    for helper in sorted(helpers, key=lambda x: x.get("name", "")):
        helper_id = helper.get("id", "")
        name = helper.get("name", "")
        icon = helper.get("icon", "")

        lines.append("")
        lines.append(f"📌 {name}")
        lines.append(f"   ID: {helper_type}.{helper_id}")
        if icon:
            lines.append(f"   Icon: {icon}")

        # Type-specific fields
        if helper_type == "input_number":
            lines.append(
                f"   Min: {helper.get('min', 0)}, Max: {helper.get('max', 100)}, Step: {helper.get('step', 1)}"
            )
            lines.append(f"   Mode: {helper.get('mode', 'slider')}, Unit: {helper.get('unit_of_measurement', '')}")
        elif helper_type == "input_text":
            lines.append(
                f"   Min: {helper.get('min', 0)}, Max: {helper.get('max', 100)}, Pattern: {helper.get('pattern', '')}"
            )
            lines.append(f"   Mode: {helper.get('mode', 'text')}")
        elif helper_type == "input_select":
            options = helper.get("options", [])
            lines.append(f"   Options: {', '.join(options)}")
        elif helper_type == "input_datetime":
            has_date = helper.get("has_date", False)
            has_time = helper.get("has_time", False)
            lines.append(f"   Date: {has_date}, Time: {has_time}")
        elif helper_type == "counter":
            lines.append(
                f"   Initial: {helper.get('initial', 0)}, Min: {helper.get('minimum', 0)}, Max: {helper.get('maximum', '')}, Step: {helper.get('step', 1)}"
            )
        elif helper_type == "timer":
            lines.append(f"   Duration: {helper.get('duration', '0:00:00')}, Restore: {helper.get('restore', False)}")

    lines.append("")
    lines.append("-" * 70)
    lines.append(f"Total: {len(helpers)} helpers")
    lines.append("")

    return "\n".join(lines)


@click.group()
def cli() -> None:
    """Manage Home Assistant helpers (list, create, update, delete).

    Supported types: input_boolean, input_number, input_text, input_select,
    input_datetime, input_button, counter, timer, schedule, todo, date, time
    """
    pass


@cli.command("list")
@click.option(
    "--type",
    "helper_type",
    required=True,
    type=click.Choice(HELPER_TYPES),
    help="Helper type to list",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def list_helpers(helper_type: str, output_json: bool) -> None:
    """List all helpers of a specific type."""
    try:
        result = websocket_command(f"{helper_type}/list")
        helpers = result if isinstance(result, list) else []

        if output_json:
            click.echo(json.dumps(helpers, indent=2))
        else:
            formatted = format_helpers(helpers, helper_type)
            click.echo(formatted)

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--type",
    "helper_type",
    required=True,
    type=click.Choice(HELPER_TYPES),
    help="Helper type to create",
)
@click.option("--name", required=True, help="Helper name")
@click.option("--icon", type=str, help="Material Design icon (e.g., mdi:thermometer)")
# input_number options
@click.option("--min", "min_value", type=float, help="Minimum value (input_number, counter)")
@click.option("--max", "max_value", type=float, help="Maximum value (input_number, input_text, counter)")
@click.option("--step", type=float, help="Step value (input_number, counter)")
@click.option("--unit", "unit_of_measurement", type=str, help="Unit of measurement (input_number)")
@click.option("--mode", type=str, help="Display mode: slider/box (input_number) or text/password (input_text)")
# input_text options
@click.option("--pattern", type=str, help="Regex pattern (input_text)")
# input_select options
@click.option("--options", type=str, help="Comma-separated options (input_select)")
# input_datetime options
@click.option("--has-date", is_flag=True, help="Include date (input_datetime)")
@click.option("--has-time", is_flag=True, help="Include time (input_datetime)")
# counter options
@click.option("--initial", type=int, help="Initial value (counter)")
# timer options
@click.option("--duration", type=str, help="Duration HH:MM:SS (timer)")
@click.option("--restore", is_flag=True, help="Restore on restart (timer)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def create(
    helper_type: str,
    name: str,
    icon: str | None,
    min_value: float | None,
    max_value: float | None,
    step: float | None,
    unit_of_measurement: str | None,
    mode: str | None,
    pattern: str | None,
    options: str | None,
    has_date: bool,
    has_time: bool,
    initial: int | None,
    duration: str | None,
    restore: bool,
    output_json: bool,
) -> None:
    """Create a new helper."""
    try:
        params: dict[str, Any] = {"name": name}
        if icon:
            params["icon"] = icon

        # Type-specific parameters
        if helper_type == "input_number":
            params["min"] = min_value if min_value is not None else 0
            params["max"] = max_value if max_value is not None else 100
            if step is not None:
                params["step"] = step
            if unit_of_measurement:
                params["unit_of_measurement"] = unit_of_measurement
            if mode:
                params["mode"] = mode

        elif helper_type == "input_text":
            if min_value is not None:
                params["min"] = int(min_value)
            if max_value is not None:
                params["max"] = int(max_value)
            if pattern:
                params["pattern"] = pattern
            if mode:
                params["mode"] = mode

        elif helper_type == "input_select":
            if options:
                params["options"] = [opt.strip() for opt in options.split(",")]
            else:
                raise click.UsageError("--options required for input_select")

        elif helper_type == "input_datetime":
            params["has_date"] = has_date
            params["has_time"] = has_time
            if not has_date and not has_time:
                raise click.UsageError("Specify --has-date and/or --has-time for input_datetime")

        elif helper_type == "counter":
            if initial is not None:
                params["initial"] = initial
            if min_value is not None:
                params["minimum"] = int(min_value)
            if max_value is not None:
                params["maximum"] = int(max_value)
            if step is not None:
                params["step"] = int(step)

        elif helper_type == "timer":
            if duration:
                params["duration"] = duration
            if restore:
                params["restore"] = restore

        result = websocket_command(f"{helper_type}/create", params)

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            helper_id = result.get("id", "")
            click.echo(f"✅ Created {helper_type}: {name} (ID: {helper_type}.{helper_id})")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--type",
    "helper_type",
    required=True,
    type=click.Choice(HELPER_TYPES),
    help="Helper type",
)
@click.option("--id", "helper_id", required=True, help="Helper ID (e.g., input_number.target_temp or just target_temp)")
@click.option("--name", type=str, help="New name")
@click.option("--icon", type=str, help="New icon (empty to remove)")
# Same options as create for updates
@click.option("--min", "min_value", type=float, help="New minimum value")
@click.option("--max", "max_value", type=float, help="New maximum value")
@click.option("--step", type=float, help="New step value")
@click.option("--unit", "unit_of_measurement", type=str, help="New unit of measurement")
@click.option("--mode", type=str, help="New display mode")
@click.option("--pattern", type=str, help="New regex pattern")
@click.option("--options", type=str, help="New comma-separated options (replaces existing)")
@click.option("--has-date", type=bool, help="Include date")
@click.option("--has-time", type=bool, help="Include time")
@click.option("--initial", type=int, help="New initial value")
@click.option("--duration", type=str, help="New duration")
@click.option("--restore", type=bool, help="Restore on restart")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def update(
    helper_type: str,
    helper_id: str,
    name: str | None,
    icon: str | None,
    min_value: float | None,
    max_value: float | None,
    step: float | None,
    unit_of_measurement: str | None,
    mode: str | None,
    pattern: str | None,
    options: str | None,
    has_date: bool | None,
    has_time: bool | None,
    initial: int | None,
    duration: str | None,
    restore: bool | None,
    output_json: bool,
) -> None:
    """Update an existing helper."""
    try:
        # Extract just the ID part if full entity_id provided
        if "." in helper_id:
            helper_id = helper_id.split(".", 1)[1]

        params: dict[str, Any] = {f"{helper_type}_id": helper_id}

        if name is not None:
            params["name"] = name
        if icon is not None:
            params["icon"] = icon if icon != "" else None

        # Type-specific parameters
        if helper_type == "input_number":
            if min_value is not None:
                params["min"] = min_value
            if max_value is not None:
                params["max"] = max_value
            if step is not None:
                params["step"] = step
            if unit_of_measurement is not None:
                params["unit_of_measurement"] = unit_of_measurement
            if mode is not None:
                params["mode"] = mode

        elif helper_type == "input_text":
            if min_value is not None:
                params["min"] = int(min_value)
            if max_value is not None:
                params["max"] = int(max_value)
            if pattern is not None:
                params["pattern"] = pattern
            if mode is not None:
                params["mode"] = mode

        elif helper_type == "input_select":
            if options is not None:
                params["options"] = [opt.strip() for opt in options.split(",")]

        elif helper_type == "input_datetime":
            if has_date is not None:
                params["has_date"] = has_date
            if has_time is not None:
                params["has_time"] = has_time

        elif helper_type == "counter":
            if initial is not None:
                params["initial"] = initial
            if min_value is not None:
                params["minimum"] = int(min_value)
            if max_value is not None:
                params["maximum"] = int(max_value)
            if step is not None:
                params["step"] = int(step)

        elif helper_type == "timer":
            if duration is not None:
                params["duration"] = duration
            if restore is not None:
                params["restore"] = restore

        result = websocket_command(f"{helper_type}/update", params)

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"✅ Updated {helper_type}: {helper_id}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--type",
    "helper_type",
    required=True,
    type=click.Choice(HELPER_TYPES),
    help="Helper type",
)
@click.option("--id", "helper_id", required=True, help="Helper ID to delete")
@click.option("--confirm", is_flag=True, help="Confirm destructive operation")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def delete(
    helper_type: str,
    helper_id: str,
    confirm: bool,
    output_json: bool,
) -> None:
    """Delete a helper (requires --confirm)."""
    try:
        if not confirm:
            click.echo("⚠️  This will permanently delete the helper.", err=True)
            click.echo("   Any automations using this helper may break.", err=True)
            click.echo("   Run with --confirm to proceed.", err=True)
            sys.exit(1)

        # Extract just the ID part if full entity_id provided
        if "." in helper_id:
            helper_id = helper_id.split(".", 1)[1]

        params: dict[str, Any] = {f"{helper_type}_id": helper_id}
        websocket_command(f"{helper_type}/delete", params)

        if output_json:
            click.echo(json.dumps({"deleted": f"{helper_type}.{helper_id}"}, indent=2))
        else:
            click.echo(f"✅ Deleted {helper_type}: {helper_id}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
