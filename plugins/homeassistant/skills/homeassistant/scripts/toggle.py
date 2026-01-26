#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Toggle Script

Quick toggle for on/off entities (lights, switches, etc.)

Usage:
    uv run toggle.py light.living_room
    uv run toggle.py light.bedroom on
    uv run toggle.py switch.fan off
    uv run toggle.py --help
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
    """Minimal HTTP client for Home Assistant REST API - toggle"""

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
        """Get current entity state"""
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

    def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        """Call a service on an entity"""
        try:
            response = self.client.post(
                f"/services/{domain}/{service}",
                json={"entity_id": entity_id},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def format_toggle_result(
    entity_id: str,
    action: str,
    before_state: str,
    after_state: str,
) -> str:
    """Format toggle result for human-readable output"""
    lines: list[str] = []

    before_emoji = "🟢" if before_state == "on" else "🔴" if before_state == "off" else "⚪"
    after_emoji = "🟢" if after_state == "on" else "🔴" if after_state == "off" else "⚪"

    lines.append("")
    lines.append("=" * 80)
    lines.append(f"✅ Toggle: {entity_id}")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"🎯 Action: {action}")
    lines.append(f"{before_emoji} Before: {before_state}")
    lines.append(f"{after_emoji} After: {after_state}")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.argument("entity_id")
@click.argument("action", required=False, type=click.Choice(["on", "off", "toggle"]))
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(entity_id: str, action: str | None, output_json: bool) -> None:
    """
    Toggle an entity on/off or to a specific state.

    ENTITY_ID is the full entity ID (e.g., light.living_room).
    ACTION is optional: 'on', 'off', or 'toggle' (default: toggle).

    Examples:

        uv run toggle.py light.living_room

        uv run toggle.py light.bedroom on

        uv run toggle.py switch.fan off

        uv run toggle.py light.kitchen toggle --json
    """
    _validate_config()
    try:
        # Determine domain from entity_id
        if "." not in entity_id:
            raise click.UsageError(f"Invalid entity_id format: {entity_id}. Expected format: domain.name")

        domain = entity_id.split(".")[0]

        # Validate domain supports toggle operations
        toggle_domains = [
            "light",
            "switch",
            "fan",
            "input_boolean",
            "automation",
            "script",
            "cover",
            "lock",
            "media_player",
            "vacuum",
            "humidifier",
            "water_heater",
        ]

        if domain not in toggle_domains:
            raise click.UsageError(f"Domain '{domain}' may not support toggle. Supported: {', '.join(toggle_domains)}")

        with HomeAssistantClient() as client:
            # Get current state
            before = client.get_state(entity_id)
            before_state = before.get("state", "unknown")

            # Determine service to call
            if action is None:
                action = "toggle"

            if action == "toggle":
                service = "toggle"
            elif action == "on":
                service = "turn_on"
            elif action == "off":
                service = "turn_off"
            else:
                service = "toggle"

            # Call service
            client.call_service(domain, service, entity_id)

            # Get new state
            after = client.get_state(entity_id)
            after_state = after.get("state", "unknown")

        result = {
            "entity_id": entity_id,
            "action": action,
            "before": before_state,
            "after": after_state,
            "success": True,
        }

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            formatted = format_toggle_result(entity_id, action, before_state, after_state)
            click.echo(formatted)

        sys.exit(0)

    except click.UsageError:
        raise
    except Exception as error:
        error_data = {"error": str(error)}
        if output_json:
            click.echo(json.dumps(error_data, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
