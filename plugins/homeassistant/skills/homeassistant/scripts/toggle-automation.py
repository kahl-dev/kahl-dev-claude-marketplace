#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Toggle Automation Script

Enable or disable an automation.

Usage:
    uv run toggle-automation.py automation.morning_routine on
    uv run toggle-automation.py automation.bedtime off
    uv run toggle-automation.py automation.motion_lights toggle
    uv run toggle-automation.py --help
"""

import json
import os
import sys
from typing import Any

import click
import httpx


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
API_TIMEOUT = 30.0
USER_AGENT = "HomeAssistant-CLI/1.0"


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


class HomeAssistantClient:
    """Minimal HTTP client for Home Assistant REST API - toggle automation"""

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

    def get_state(self, entity_id: str) -> dict[str, Any]:
        """Get automation state"""
        try:
            response = self.client.get(f"/states/{entity_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                raise Exception(f"Automation not found: {entity_id}") from error
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error

    def call_service(
        self,
        service: str,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        """Call automation service"""
        try:
            response = self.client.post(
                f"/services/automation/{service}",
                json={"entity_id": entity_id},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def format_result(
    entity_id: str,
    action: str,
    before_state: str,
    after_state: str,
    friendly_name: str,
) -> str:
    """Format result for human-readable output"""
    lines: list[str] = []

    before_emoji = "🟢" if before_state == "on" else "🔴"
    after_emoji = "🟢" if after_state == "on" else "🔴"

    lines.append("")
    lines.append("=" * 80)
    lines.append(f"🤖 Automation: {friendly_name}")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"📍 Entity: {entity_id}")
    lines.append(f"🎯 Action: {action}")
    lines.append(f"{before_emoji} Before: {'Enabled' if before_state == 'on' else 'Disabled'}")
    lines.append(f"{after_emoji} After: {'Enabled' if after_state == 'on' else 'Disabled'}")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.argument("entity_id")
@click.argument("action", type=click.Choice(["on", "off", "toggle"]))
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(entity_id: str, action: str, output_json: bool) -> None:
    """
    Enable or disable an automation.

    ENTITY_ID is the automation entity ID (e.g., automation.morning_routine).
    ACTION is 'on' (enable), 'off' (disable), or 'toggle'.

    Examples:

        uv run toggle-automation.py automation.morning_routine on

        uv run toggle-automation.py automation.bedtime off

        uv run toggle-automation.py automation.motion_lights toggle
    """
    _validate_config()
    try:
        # Validate entity_id
        if not entity_id.startswith("automation."):
            entity_id = f"automation.{entity_id}"

        with HomeAssistantClient() as client:
            # Get current state
            before = client.get_state(entity_id)
            before_state = before.get("state", "unknown")
            friendly_name = before.get("attributes", {}).get("friendly_name", entity_id)

            # Determine service to call
            if action == "toggle":
                service = "toggle"
            elif action == "on":
                service = "turn_on"
            else:
                service = "turn_off"

            # Call service
            client.call_service(service, entity_id)

            # Get new state
            after = client.get_state(entity_id)
            after_state = after.get("state", "unknown")

        result = {
            "entity_id": entity_id,
            "friendly_name": friendly_name,
            "action": action,
            "before": before_state,
            "after": after_state,
            "success": True,
        }

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            formatted = format_result(entity_id, action, before_state, after_state, friendly_name)
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
