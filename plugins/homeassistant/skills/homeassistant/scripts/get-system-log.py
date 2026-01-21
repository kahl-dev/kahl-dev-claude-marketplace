#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant System Log Script

Query Home Assistant system logs via WebSocket API.

Usage:
    uv run get-system-log.py
    uv run get-system-log.py --level error
    uv run get-system-log.py --limit 10
    uv run get-system-log.py --json
    uv run get-system-log.py --help
"""

import json
import os
import sys
from datetime import datetime
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
    return urlunparse(parsed._replace(scheme=ws_scheme, path="/api/websocket"))


def websocket_command(command_type: str) -> dict[str, Any]:
    """Execute WebSocket command and return result."""
    ws_url = get_websocket_url(HA_URL)

    ws = create_connection(ws_url, timeout=WS_TIMEOUT)
    try:
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
        ws.close()


def format_log_entries(entries: list[dict[str, Any]], level: str | None, limit: int | None) -> str:
    """Format log entries for human-readable output."""
    lines: list[str] = []

    # Filter by level if specified
    if level:
        entries = [e for e in entries if e.get("level", "").lower() == level.lower()]

    # Sort by timestamp descending (newest first)
    entries = sorted(entries, key=lambda x: x.get("timestamp", 0), reverse=True)

    # Apply limit
    if limit:
        entries = entries[:limit]

    if not entries:
        return "No log entries found."

    lines.append("")
    lines.append("=" * 80)
    lines.append("📋 Home Assistant System Log")
    lines.append("=" * 80)

    for entry in entries:
        level_str = entry.get("level", "UNKNOWN").upper()
        name = entry.get("name", "unknown")
        message = entry.get("message", "")
        source = entry.get("source", [])
        timestamp = entry.get("timestamp", 0)
        count = entry.get("count", 1)

        # Level emoji
        level_emoji = "ℹ️"
        if level_str == "ERROR":
            level_emoji = "❌"
        elif level_str == "WARNING":
            level_emoji = "⚠️"
        elif level_str == "DEBUG":
            level_emoji = "🔍"

        # Format timestamp
        try:
            time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            time_str = "unknown"

        lines.append("")
        lines.append(f"{level_emoji} [{level_str}] {time_str}")
        lines.append(f"   Source: {name}")
        if source:
            source_str = ":".join(str(s) for s in source)
            lines.append(f"   File: {source_str}")
        if count > 1:
            lines.append(f"   Count: {count}x")
        lines.append(f"   Message: {message}")

    lines.append("")
    lines.append("-" * 80)
    lines.append(f"Total: {len(entries)} entries")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--level",
    "-l",
    type=click.Choice(["error", "warning", "info", "debug"], case_sensitive=False),
    help="Filter by log level",
)
@click.option(
    "--limit",
    "-n",
    type=int,
    help="Limit number of entries returned",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(
    level: str | None,
    limit: int | None,
    output_json: bool,
) -> None:
    """
    Query Home Assistant system logs via WebSocket API.

    Shows errors, warnings, and info messages from Home Assistant's internal logging.

    Examples:

        uv run get-system-log.py

        uv run get-system-log.py --level error

        uv run get-system-log.py --level warning --limit 5

        uv run get-system-log.py --json
    """
    try:
        result = websocket_command("system_log/list")

        # Result is a list of log entries
        entries = result if isinstance(result, list) else []

        # Filter by level if specified
        filtered = entries
        if level:
            filtered = [e for e in filtered if e.get("level", "").lower() == level.lower()]

        # Sort by timestamp descending
        filtered = sorted(filtered, key=lambda x: x.get("timestamp", 0), reverse=True)

        # Apply limit
        if limit:
            filtered = filtered[:limit]

        if output_json:
            click.echo(json.dumps(filtered, indent=2))
        else:
            formatted = format_log_entries(entries, level, limit)
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
