#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Get Logbook Script

Query logbook entries via WebSocket API with time and entity filters.
Default: last 3 hours, limit 100 entries.

Usage:
    uv run get-logbook.py
    uv run get-logbook.py --hours 24
    uv run get-logbook.py --entity automation.my_automation
    uv run get-logbook.py --entity sensor.temp,sensor.humidity
    uv run get-logbook.py --device abc123
    uv run get-logbook.py --limit 500
    uv run get-logbook.py --json
    uv run get-logbook.py --help
"""

import json
import os
import sys
from datetime import UTC, datetime, timedelta
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


def format_logbook_entries(entries: list[dict[str, Any]], limit: int) -> str:
    """Format logbook entries for human-readable output."""
    lines: list[str] = []

    if not entries:
        return "No logbook entries found for the specified time range and filters."

    lines.append("")
    lines.append("=" * 80)
    lines.append("📋 Home Assistant Logbook")
    lines.append("=" * 80)

    # Apply limit
    display_entries = entries[:limit]
    truncated = len(entries) > limit

    for entry in display_entries:
        when = entry.get("when", "")
        name = entry.get("name", "unknown")
        entity_id = entry.get("entity_id", "")
        state = entry.get("state", "")
        message = entry.get("message", "")
        domain = entry.get("domain", "")
        context_user_id = entry.get("context_user_id", "")

        # Format timestamp
        try:
            if when:
                when_dt = datetime.fromisoformat(when.replace("Z", "+00:00"))
                time_str = when_dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = "unknown"
        except (ValueError, AttributeError):
            time_str = when or "unknown"

        # Domain emoji
        domain_emoji = "📝"
        if domain == "automation":
            domain_emoji = "⚡"
        elif domain == "script":
            domain_emoji = "📜"
        elif domain == "light":
            domain_emoji = "💡"
        elif domain == "switch":
            domain_emoji = "🔌"
        elif domain == "climate":
            domain_emoji = "🌡️"
        elif domain == "sensor":
            domain_emoji = "📊"
        elif domain == "binary_sensor":
            domain_emoji = "🔘"

        lines.append("")
        lines.append(f"{domain_emoji} {time_str}")
        lines.append(f"   Entity: {entity_id or name}")
        if state:
            lines.append(f"   State: {state}")
        if message:
            lines.append(f"   Message: {message}")
        if context_user_id:
            lines.append(f"   User: {context_user_id}")

    lines.append("")
    lines.append("-" * 80)
    if truncated:
        lines.append(f"Showing {limit} of {len(entries)} entries (use --limit to see more)")
    else:
        lines.append(f"Total: {len(entries)} entries")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--start",
    "-s",
    type=str,
    help="Start time (ISO 8601 format, e.g., 2026-01-28T10:00:00)",
)
@click.option(
    "--end",
    "-e",
    type=str,
    help="End time (ISO 8601 format). Default: now",
)
@click.option(
    "--hours",
    "-h",
    type=float,
    default=3.0,
    help="Hours to look back from end time (default: 3)",
)
@click.option(
    "--limit",
    "-n",
    type=int,
    default=100,
    help="Maximum entries to display (default: 100)",
)
@click.option(
    "--entity",
    type=str,
    help="Filter by entity_id (comma-separated for multiple)",
)
@click.option(
    "--device",
    type=str,
    help="Filter by device_id",
)
@click.option(
    "--context-id",
    type=str,
    help="Filter by context_id (trace related events)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output raw JSON instead of formatted output",
)
def main(
    start: str | None,
    end: str | None,
    hours: float,
    limit: int,
    entity: str | None,
    device: str | None,
    context_id: str | None,
    output_json: bool,
) -> None:
    """
    Query Home Assistant logbook entries.

    Default: last 3 hours, limit 100 entries.
    Use filters to narrow results by entity, device, or time range.

    Examples:

        uv run get-logbook.py

        uv run get-logbook.py --hours 24

        uv run get-logbook.py --entity automation.my_automation

        uv run get-logbook.py --entity sensor.temp,sensor.humidity --hours 12

        uv run get-logbook.py --device abc123

        uv run get-logbook.py --start "2026-01-28T10:00:00" --hours 2

        uv run get-logbook.py --limit 500 --json
    """
    _validate_config()

    try:
        # Calculate time range
        now = datetime.now(UTC)

        if end:
            try:
                end_time = datetime.fromisoformat(end.replace("Z", "+00:00"))
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=UTC)
            except ValueError as parse_error:
                raise Exception(f"Invalid end time format: {end}") from parse_error
        else:
            end_time = now

        if start:
            try:
                start_time = datetime.fromisoformat(start.replace("Z", "+00:00"))
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=UTC)
            except ValueError as parse_error:
                raise Exception(f"Invalid start time format: {start}") from parse_error
        else:
            start_time = end_time - timedelta(hours=hours)

        # Build request data
        data: dict[str, Any] = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }

        # Add filters
        if entity:
            entity_ids = [e.strip() for e in entity.split(",")]
            data["entity_ids"] = entity_ids

        if device:
            data["device_ids"] = [device]

        if context_id:
            data["context_id"] = context_id

        # Fetch logbook entries
        result = websocket_command("logbook/get_events", data)

        # Result is a list of entries
        entries = result if isinstance(result, list) else []

        # Warn if many entries
        if len(entries) > 500 and not output_json:
            click.echo(
                f"⚠️  Warning: {len(entries)} entries found. Consider narrowing your query with --entity or shorter --hours.",
                err=True,
            )

        if output_json:
            # Apply limit to JSON output too
            output_entries = entries[:limit] if limit else entries
            click.echo(json.dumps(output_entries, indent=2))
        else:
            formatted = format_logbook_entries(entries, limit)
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
