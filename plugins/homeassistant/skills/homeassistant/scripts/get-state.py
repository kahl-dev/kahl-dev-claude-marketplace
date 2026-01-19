#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Get State Script

Get the current state and attributes of a single entity.

Usage:
    uv run get-state.py light.living_room
    uv run get-state.py sensor.temperature --json
    uv run get-state.py --help
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
    """Minimal HTTP client for Home Assistant REST API - get state"""

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

    def get_state(self, entity_id: str) -> dict[str, Any]:
        """Get single entity state"""
        try:
            response = self.client.get(f"/states/{entity_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                raise Exception(f"Entity not found: {entity_id}") from error
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def format_state(entity: dict[str, Any]) -> str:
    """Format entity state for human-readable output"""
    lines: list[str] = []

    entity_id = entity.get("entity_id", "unknown")
    state = entity.get("state", "unknown")
    attributes = entity.get("attributes", {})
    last_changed = entity.get("last_changed", "unknown")
    last_updated = entity.get("last_updated", "unknown")

    # State emoji
    state_emoji = "⚪"
    if state == "on":
        state_emoji = "🟢"
    elif state == "off":
        state_emoji = "🔴"
    elif state == "unavailable":
        state_emoji = "⚫"
    elif state == "unknown":
        state_emoji = "❓"

    friendly_name = attributes.get("friendly_name", entity_id)

    lines.append("")
    lines.append("=" * 80)
    lines.append(f"🏠 {friendly_name}")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"📍 Entity ID: {entity_id}")
    lines.append(f"{state_emoji} State: {state}")
    lines.append("")
    lines.append(f"🕐 Last Changed: {last_changed}")
    lines.append(f"🔄 Last Updated: {last_updated}")

    # Attributes
    if attributes:
        lines.append("")
        lines.append("📋 Attributes:")
        lines.append("-" * 40)
        for key, value in sorted(attributes.items()):
            if key == "friendly_name":
                continue
            # Format value nicely
            if isinstance(value, list):
                value_str = ", ".join(str(v) for v in value)
            elif isinstance(value, dict):
                value_str = json.dumps(value)
            else:
                value_str = str(value)
            lines.append(f"  • {key}: {value_str}")

    lines.append("")

    return "\n".join(lines)


@click.command()
@click.argument("entity_id")
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(entity_id: str, output_json: bool) -> None:
    """
    Get the current state and attributes of an entity.

    ENTITY_ID is the full entity ID (e.g., light.living_room, sensor.temperature).

    Examples:

        uv run get-state.py light.living_room

        uv run get-state.py sensor.temperature --json

        uv run get-state.py binary_sensor.motion
    """
    try:
        with HomeAssistantClient() as client:
            entity = client.get_state(entity_id)

        if output_json:
            click.echo(json.dumps(entity, indent=2))
        else:
            formatted = format_state(entity)
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
