#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Integrations List Script

List config entries (integrations) via WebSocket API.

Usage:
    uv run list-integrations.py
    uv run list-integrations.py --domain zha
    uv run list-integrations.py --state loaded
    uv run list-integrations.py --help
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


def format_integrations(entries: list[dict[str, Any]]) -> str:
    """Format integrations for human-readable output."""
    lines: list[str] = []

    if not entries:
        return "No integrations found."

    lines.append("")
    lines.append("=" * 70)
    lines.append("🔌 Home Assistant Integrations (Config Entries)")
    lines.append("=" * 70)

    # Group by domain
    by_domain: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        domain = entry.get("domain", "unknown")
        if domain not in by_domain:
            by_domain[domain] = []
        by_domain[domain].append(entry)

    for domain in sorted(by_domain.keys()):
        domain_entries = by_domain[domain]
        lines.append("")
        lines.append(f"📦 {domain} ({len(domain_entries)} entries)")

        for entry in domain_entries:
            entry_id = entry.get("entry_id", "")
            title = entry.get("title", "(no title)")
            state = entry.get("state", "unknown")
            disabled_by = entry.get("disabled_by")

            # State indicator
            if disabled_by:
                state_icon = "⏸️"
                state_text = f"disabled ({disabled_by})"
            elif state == "loaded":
                state_icon = "✅"
                state_text = "loaded"
            elif state == "setup_error":
                state_icon = "❌"
                state_text = "setup error"
            elif state == "setup_retry":
                state_icon = "🔄"
                state_text = "retrying"
            else:
                state_icon = "❓"
                state_text = state

            lines.append(f"   {state_icon} {title}")
            lines.append(f"      ID: {entry_id}")
            lines.append(f"      State: {state_text}")

    lines.append("")
    lines.append("-" * 70)
    lines.append(f"Total: {len(entries)} integrations across {len(by_domain)} domains")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option("--domain", type=str, help="Filter by integration domain (e.g., zha, hue)")
@click.option(
    "--state", type=click.Choice(["loaded", "setup_error", "setup_retry", "not_loaded"]), help="Filter by state"
)
@click.option("--disabled", is_flag=True, help="Show only disabled integrations")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def main(
    domain: str | None,
    state: str | None,
    disabled: bool,
    output_json: bool,
) -> None:
    """
    List all Home Assistant integrations (config entries).

    Examples:

        uv run list-integrations.py

        uv run list-integrations.py --domain zha

        uv run list-integrations.py --state setup_error

        uv run list-integrations.py --disabled

        uv run list-integrations.py --json
    """
    try:
        result = websocket_command("config_entries/get")
        entries = result if isinstance(result, list) else []

        # Apply filters
        if domain:
            entries = [e for e in entries if e.get("domain") == domain]
        if state:
            entries = [e for e in entries if e.get("state") == state]
        if disabled:
            entries = [e for e in entries if e.get("disabled_by") is not None]

        if output_json:
            click.echo(json.dumps(entries, indent=2))
        else:
            formatted = format_integrations(entries)
            click.echo(formatted)

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
