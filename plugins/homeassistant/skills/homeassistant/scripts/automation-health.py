#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Automation Health Script

Analyze automations for potential issues: disabled, stale, unknown entity references.

Usage:
    uv run automation-health.py
    uv run automation-health.py --check-entities
    uv run automation-health.py --stale-days 30
    uv run automation-health.py --json
    uv run automation-health.py --help
"""

import json
import os
import re
import sys
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse, urlunparse

import click
import httpx
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
API_TIMEOUT = 30.0
WS_TIMEOUT = 30
USER_AGENT = "HomeAssistant-CLI/1.0"


class HomeAssistantClient:
    """Minimal HTTP client for Home Assistant REST API"""

    def __init__(self) -> None:
        self.client = httpx.Client(
            base_url=f"{HA_URL}/api",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            timeout=API_TIMEOUT,
        )

    def __enter__(self) -> "HomeAssistantClient":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.client.close()

    def get_states(self) -> list[dict[str, Any]]:
        """Get all entity states"""
        try:
            response = self.client.get("/states")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def get_websocket_url(base_url: str) -> str:
    """Convert HTTP(S) URL to WebSocket URL using proper parsing."""
    parsed = urlparse(base_url)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse(parsed._replace(scheme=ws_scheme, path="/api/websocket"))


def get_automation_config(automation_id: str) -> dict[str, Any] | None:
    """Get automation config via WebSocket API."""
    ws_url = get_websocket_url(HA_URL)

    ws = create_connection(ws_url, timeout=WS_TIMEOUT)
    try:
        # Auth phase
        ws.recv()  # auth_required
        ws.send(json.dumps({"type": "auth", "access_token": HA_TOKEN}))
        auth_result = json.loads(ws.recv())

        if auth_result.get("type") != "auth_ok":
            return None

        # Get automation config
        ws.send(json.dumps({"id": 1, "type": "automation/config", "entity_id": automation_id}))
        result = json.loads(ws.recv())

        if not result.get("success"):
            return None

        return result.get("result", {})
    except (WebSocketTimeoutException, Exception):
        return None
    finally:
        ws.close()


def extract_entity_references(config: dict[str, Any]) -> set[str]:
    """Extract all entity_id references from automation config."""
    references: set[str] = set()

    # Known service names to exclude (not entities)
    service_names = {
        "turn_on",
        "turn_off",
        "toggle",
        "set",
        "volume_set",
        "volume_up",
        "volume_down",
        "play_media",
        "media_play",
        "media_pause",
        "media_stop",
        "set_temperature",
        "set_hvac_mode",
        "open_cover",
        "close_cover",
        "set_cover_position",
    }

    def is_valid_entity_id(value: str) -> bool:
        """Check if value looks like a valid entity_id."""
        if "." not in value:
            return False
        parts = value.split(".")
        if len(parts) != 2:
            return False
        domain, name = parts
        # Exclude service-like names
        if name in service_names:
            return False
        # Exclude hex device IDs
        if re.match(r"^[a-f0-9]{32}$", name):
            return False
        return True

    def search_dict(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "entity_id":
                    if isinstance(value, str) and is_valid_entity_id(value):
                        references.add(value)
                    elif isinstance(value, list):
                        references.update(v for v in value if isinstance(v, str) and is_valid_entity_id(v))
                else:
                    search_dict(value)
        elif isinstance(obj, list):
            for item in obj:
                search_dict(item)

    search_dict(config)
    return references


def analyze_automations(
    automations: list[dict[str, Any]],
    all_entity_ids: set[str],
    check_entities: bool,
    stale_days: int,
) -> dict[str, Any]:
    """Analyze automations for health issues."""
    issues: list[dict[str, Any]] = []
    now = datetime.now(UTC)

    disabled_count = 0
    stale_count = 0
    unknown_refs_count = 0

    for automation in automations:
        entity_id = automation.get("entity_id", "")
        state = automation.get("state", "")
        attributes = automation.get("attributes", {})
        friendly_name = attributes.get("friendly_name", entity_id)
        last_triggered = attributes.get("last_triggered")

        automation_issues: list[str] = []

        # Check: Disabled
        if state != "on":
            automation_issues.append("disabled")
            disabled_count += 1

        # Check: Stale (not triggered recently)
        if last_triggered:
            try:
                triggered_dt = datetime.fromisoformat(last_triggered.replace("Z", "+00:00"))
                days_since = (now - triggered_dt).days
                if days_since > stale_days:
                    automation_issues.append(f"stale ({days_since} days)")
                    stale_count += 1
            except (ValueError, TypeError):
                pass
        elif state == "on":
            # Enabled but never triggered
            automation_issues.append("never triggered")
            stale_count += 1

        # Check: Unknown entity references
        unknown_entities: list[str] = []
        if check_entities:
            config = get_automation_config(entity_id)
            if config:
                references = extract_entity_references(config)
                for ref in references:
                    if ref not in all_entity_ids and ref != entity_id:
                        unknown_entities.append(ref)
                if unknown_entities:
                    automation_issues.append(f"unknown entities: {', '.join(unknown_entities[:3])}")
                    if len(unknown_entities) > 3:
                        automation_issues[-1] += f" (+{len(unknown_entities) - 3} more)"
                    unknown_refs_count += 1

        if automation_issues:
            issues.append(
                {
                    "entity_id": entity_id,
                    "friendly_name": friendly_name,
                    "state": state,
                    "last_triggered": last_triggered,
                    "issues": automation_issues,
                    "unknown_entities": unknown_entities if unknown_entities else None,
                }
            )

    return {
        "total_automations": len(automations),
        "issues_found": len(issues),
        "summary": {
            "disabled": disabled_count,
            "stale": stale_count,
            "unknown_references": unknown_refs_count,
        },
        "automations_with_issues": issues,
    }


def format_health_report(report: dict[str, Any], check_entities: bool) -> str:
    """Format health report for human-readable output."""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 80)
    lines.append("🩺 Home Assistant Automation Health Report")
    lines.append("=" * 80)
    lines.append("")

    total = report["total_automations"]
    issues_count = report["issues_found"]
    summary = report["summary"]

    if issues_count == 0:
        lines.append(f"✅ All {total} automations are healthy!")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"📊 Summary: {total} automations, {issues_count} with issues")
    lines.append("")
    lines.append(f"   🔴 Disabled: {summary['disabled']}")
    lines.append(f"   ⏰ Stale/Never triggered: {summary['stale']}")
    if check_entities:
        lines.append(f"   ❓ Unknown entity references: {summary['unknown_references']}")
    lines.append("")
    lines.append("-" * 80)
    lines.append("")

    for item in report["automations_with_issues"]:
        entity_id = item["entity_id"]
        friendly_name = item["friendly_name"]
        issues = item["issues"]

        # Severity emoji
        if "disabled" in issues:
            emoji = "🔴"
        elif any("unknown" in i for i in issues):
            emoji = "❓"
        else:
            emoji = "⚠️"

        lines.append(f"{emoji} {friendly_name}")
        lines.append(f"   ID: {entity_id}")
        lines.append(f"   Issues: {', '.join(issues)}")

        if item.get("unknown_entities"):
            lines.append(f"   Missing: {', '.join(item['unknown_entities'][:5])}")

        lines.append("")

    lines.append("-" * 80)
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--check-entities",
    is_flag=True,
    help="Check for references to unknown/missing entities (slower, uses WebSocket)",
)
@click.option(
    "--stale-days",
    default=30,
    type=int,
    help="Days without trigger to consider automation stale (default: 30)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(
    check_entities: bool,
    stale_days: int,
    output_json: bool,
) -> None:
    """
    Analyze Home Assistant automations for potential issues.

    Checks for:
    - Disabled automations
    - Stale automations (not triggered in X days)
    - References to unknown/missing entities (with --check-entities)

    Examples:

        uv run automation-health.py

        uv run automation-health.py --check-entities

        uv run automation-health.py --stale-days 7

        uv run automation-health.py --json
    """
    try:
        with HomeAssistantClient() as client:
            all_states = client.get_states()

        # Extract automations and all entity IDs
        automations = [s for s in all_states if s.get("entity_id", "").startswith("automation.")]
        all_entity_ids = {s.get("entity_id", "") for s in all_states}

        # Analyze
        report = analyze_automations(automations, all_entity_ids, check_entities, stale_days)

        if output_json:
            click.echo(json.dumps(report, indent=2, default=str))
        else:
            formatted = format_health_report(report, check_entities)
            click.echo(formatted)

        # Exit with error code if issues found
        if report["issues_found"] > 0:
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
