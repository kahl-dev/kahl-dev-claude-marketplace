#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant List Traces Script

List available automation/script execution traces via WebSocket API.

Usage:
    uv run list-traces.py automation.my_automation
    uv run list-traces.py --domain automation
    uv run list-traces.py --domain script
    uv run list-traces.py --json
    uv run list-traces.py --help
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


def format_traces(traces: dict[str, Any], entity_id: str | None, domain: str | None) -> str:
    """Format traces for human-readable output."""
    lines: list[str] = []

    if not traces:
        if entity_id:
            return f"No traces found for {entity_id}.\n\nTip: HA stores only 5 traces per automation by default.\nAdd 'trace: stored_traces: 20' to automation YAML for more history."
        return f"No traces found for domain '{domain}'."

    lines.append("")
    lines.append("=" * 80)
    if entity_id:
        lines.append(f"📋 Traces for: {entity_id}")
    else:
        lines.append(f"📋 Traces for domain: {domain}")
    lines.append("=" * 80)

    # traces is a dict: {domain: {item_id: [trace_list]}}
    for trace_domain, items in traces.items():
        for item_id, trace_list in items.items():
            full_id = f"{trace_domain}.{item_id}"

            if entity_id and full_id != entity_id:
                continue

            lines.append("")
            lines.append(f"🔧 {full_id}")
            lines.append("-" * 40)

            if not trace_list:
                lines.append("   No traces available")
                continue

            for trace in trace_list:
                run_id = trace.get("run_id", "unknown")
                timestamp = trace.get("timestamp", {})
                start = timestamp.get("start", "")
                state = trace.get("state", "unknown")

                # Format timestamp
                try:
                    if start:
                        time_str = datetime.fromisoformat(start.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        time_str = "unknown"
                except (ValueError, AttributeError):
                    time_str = start or "unknown"

                # State emoji
                state_emoji = "✓" if state == "stopped" else "⏳" if state == "running" else "?"

                lines.append(f"   {state_emoji} {time_str} | run_id: {run_id} | state: {state}")

    lines.append("")
    lines.append("-" * 80)

    # Count total traces
    total = sum(len(trace_list) for items in traces.values() for trace_list in items.values())
    lines.append(f"Total: {total} traces")
    lines.append("")
    lines.append("Use 'get-trace.py <entity_id> --run-id <run_id>' to view trace details.")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.argument("entity_id", required=False)
@click.option(
    "--domain",
    "-d",
    type=click.Choice(["automation", "script"], case_sensitive=False),
    help="List traces for all automations or scripts",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(
    entity_id: str | None,
    domain: str | None,
    output_json: bool,
) -> None:
    """
    List available automation/script execution traces.

    Provide an entity_id to list traces for a specific automation/script,
    or use --domain to list traces for all automations or scripts.

    Examples:

        uv run list-traces.py automation.my_automation

        uv run list-traces.py --domain automation

        uv run list-traces.py --domain script

        uv run list-traces.py automation.my_automation --json
    """
    if not entity_id and not domain:
        click.echo("❌ Error: Provide an entity_id or use --domain to specify scope.", err=True)
        click.echo("   Example: list-traces.py automation.my_automation", err=True)
        click.echo("   Example: list-traces.py --domain automation", err=True)
        sys.exit(1)

    _validate_config()

    try:
        # Build request data
        data: dict[str, Any] = {}

        if entity_id:
            # Parse entity_id to get domain and item_id
            parts = entity_id.split(".", 1)
            if len(parts) != 2:
                raise Exception(f"Invalid entity_id format: {entity_id}. Expected: domain.item_id")
            data["domain"] = parts[0]
            data["item_id"] = parts[1]
        elif domain:
            data["domain"] = domain

        result = websocket_command("trace/list", data)

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            formatted = format_traces(result, entity_id, domain)
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
