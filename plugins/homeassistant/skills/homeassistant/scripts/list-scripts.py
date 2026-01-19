#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant List Scripts Script

List all HA scripts (not Python scripts, but Home Assistant script entities).

Usage:
    uv run list-scripts.py
    uv run list-scripts.py --running
    uv run list-scripts.py --json
    uv run list-scripts.py --help
"""

import json
import os
import sys
from typing import Any

import click
import httpx

# Configuration from environment
HA_URL = os.getenv("HOMEASSISTANT_URL")
HA_TOKEN = os.getenv("HOMEASSISTANT_TOKEN")
API_TIMEOUT = 30.0
USER_AGENT = "HomeAssistant-CLI/1.0"


class HomeAssistantClient:
    """Minimal HTTP client for Home Assistant REST API - scripts"""

    def __init__(self) -> None:
        if not all([HA_URL, HA_TOKEN]):
            raise ValueError("Missing environment variables: HOMEASSISTANT_URL, HOMEASSISTANT_TOKEN")

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

    def get_scripts(self) -> list[dict[str, Any]]:
        """Get all script entities"""
        try:
            response = self.client.get("/states")
            response.raise_for_status()
            all_states = response.json()
            return [s for s in all_states if s.get("entity_id", "").startswith("script.")]
        except httpx.HTTPStatusError as error:
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def format_scripts(scripts: list[dict[str, Any]]) -> str:
    """Format scripts for human-readable output"""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 80)
    lines.append("📜 Home Assistant Scripts")
    lines.append("=" * 80)
    lines.append("")

    if not scripts:
        lines.append("No scripts found.")
        lines.append("")
        return "\n".join(lines)

    running_count = sum(1 for s in scripts if s.get("state") == "on")

    lines.append(f"Total: {len(scripts)} scripts ({running_count} running)")
    lines.append("")
    lines.append("-" * 80)

    for script in sorted(scripts, key=lambda x: x.get("entity_id", "")):
        entity_id = script.get("entity_id", "unknown")
        state = script.get("state", "unknown")
        attributes = script.get("attributes", {})
        friendly_name = attributes.get("friendly_name", entity_id)
        last_triggered = attributes.get("last_triggered", "Never")

        status_emoji = "🏃" if state == "on" else "⏸️"

        lines.append(f"{status_emoji} {friendly_name}")
        lines.append(f"   ID: {entity_id}")
        lines.append(f"   Status: {'Running' if state == 'on' else 'Idle'}")
        lines.append(f"   Last Triggered: {last_triggered or 'Never'}")
        lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--running",
    is_flag=True,
    help="Show only currently running scripts",
)
@click.option(
    "--search",
    "-s",
    help="Search scripts by name (case-insensitive)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(running: bool, search: str | None, output_json: bool) -> None:
    """
    List all Home Assistant scripts.

    These are HA script entities, not Python scripts.

    Examples:

        uv run list-scripts.py

        uv run list-scripts.py --running

        uv run list-scripts.py --search "notify"

        uv run list-scripts.py --json
    """
    try:
        with HomeAssistantClient() as client:
            scripts = client.get_scripts()

        # Apply filters
        if running:
            scripts = [s for s in scripts if s.get("state") == "on"]

        if search:
            search_lower = search.lower()
            scripts = [
                s
                for s in scripts
                if search_lower in s.get("entity_id", "").lower()
                or search_lower in s.get("attributes", {}).get("friendly_name", "").lower()
            ]

        if output_json:
            click.echo(json.dumps(scripts, indent=2))
        else:
            formatted = format_scripts(scripts)
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
