#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant List Repairs Script

Query Home Assistant repair issues via WebSocket API.

Usage:
    uv run list-repairs.py
    uv run list-repairs.py --severity error
    uv run list-repairs.py --domain group
    uv run list-repairs.py --json
    uv run list-repairs.py --help
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
    # Preserve existing path and append /api/websocket
    base_path = parsed.path.rstrip("/")
    ws_path = f"{base_path}/api/websocket"
    return urlunparse(parsed._replace(scheme=ws_scheme, path=ws_path))


def websocket_command(command_type: str) -> dict[str, Any]:
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
        if ws:
            ws.close()


def format_repair_issues(issues: list[dict[str, Any]]) -> str:
    """Format repair issues for human-readable output."""
    lines: list[str] = []

    if not issues:
        return "✅ No repair issues found. Your Home Assistant is healthy!"

    lines.append("")
    lines.append("=" * 80)
    lines.append("🔧 Home Assistant Repair Issues")
    lines.append("=" * 80)

    # Group by domain
    by_domain: dict[str, list[dict[str, Any]]] = {}
    for issue in issues:
        issue_domain = issue.get("domain", "unknown")
        if issue_domain not in by_domain:
            by_domain[issue_domain] = []
        by_domain[issue_domain].append(issue)

    for domain_name in sorted(by_domain.keys()):
        domain_issues = by_domain[domain_name]
        lines.append("")
        lines.append(f"📦 {domain_name.upper()} ({len(domain_issues)} issues)")
        lines.append("-" * 40)

        for issue in domain_issues:
            severity_str = issue.get("severity", "unknown")
            issue_id = issue.get("issue_id", "unknown")
            placeholders = issue.get("translation_placeholders", {})

            # Severity emoji
            severity_emoji = "ℹ️"
            if severity_str == "error":
                severity_emoji = "❌"
            elif severity_str == "warning":
                severity_emoji = "⚠️"
            elif severity_str == "critical":
                severity_emoji = "🚨"

            lines.append("")
            lines.append(f"  {severity_emoji} [{severity_str.upper()}] {issue_id}")

            # Show relevant placeholders
            if placeholders:
                for key, value in placeholders.items():
                    if key in ["entity_id", "entities", "members", "name"]:
                        lines.append(f"     {key}: {value}")

            # Show if issue is ignorable or has fix
            if issue.get("is_fixable"):
                lines.append("     🔧 Has automatic fix available")
            if issue.get("dismissed_version"):
                lines.append(f"     🔕 Dismissed in version: {issue.get('dismissed_version')}")

    lines.append("")
    lines.append("-" * 80)
    lines.append(f"Total: {len(issues)} repair issues")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--severity",
    "-s",
    type=click.Choice(["warning", "error", "critical"], case_sensitive=False),
    help="Filter by severity level",
)
@click.option(
    "--domain",
    "-d",
    help="Filter by domain (group, automation, sensor, etc.)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(
    severity: str | None,
    domain: str | None,
    output_json: bool,
) -> None:
    """
    Query Home Assistant repair issues via WebSocket API.

    Shows configuration issues, broken integrations, and other problems
    detected by Home Assistant and Spook integration.

    Examples:

        uv run list-repairs.py

        uv run list-repairs.py --severity error

        uv run list-repairs.py --domain group

        uv run list-repairs.py --json
    """
    _validate_config()
    try:
        result = websocket_command("repairs/list_issues")

        # Result has 'issues' key
        issues = result.get("issues", []) if isinstance(result, dict) else []

        # Filter by severity if specified
        filtered = issues
        if severity:
            filtered = [i for i in filtered if i.get("severity", "").lower() == severity.lower()]

        # Filter by domain if specified
        if domain:
            filtered = [i for i in filtered if i.get("domain", "").lower() == domain.lower()]

        if output_json:
            click.echo(json.dumps(filtered, indent=2))
        else:
            formatted = format_repair_issues(filtered)
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
