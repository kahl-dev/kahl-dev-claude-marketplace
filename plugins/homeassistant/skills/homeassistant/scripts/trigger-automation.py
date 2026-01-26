#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Trigger Automation Script

Manually trigger an automation.

Usage:
    uv run trigger-automation.py automation.morning_routine
    uv run trigger-automation.py automation.bedtime --skip-condition
    uv run trigger-automation.py --help
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
    """Minimal HTTP client for Home Assistant REST API - trigger automation"""

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

    def trigger_automation(
        self,
        entity_id: str,
        skip_condition: bool = False,
    ) -> list[dict[str, Any]]:
        """Trigger an automation"""
        try:
            payload: dict[str, Any] = {"entity_id": entity_id}
            if skip_condition:
                payload["skip_condition"] = True

            response = self.client.post(
                "/services/automation/trigger",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def format_result(
    entity_id: str,
    friendly_name: str,
    skip_condition: bool,
) -> str:
    """Format result for human-readable output"""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 80)
    lines.append(f"⚡ Automation Triggered: {friendly_name}")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"📍 Entity: {entity_id}")
    lines.append(f"🎯 Skip Condition: {'Yes' if skip_condition else 'No'}")
    lines.append("")
    lines.append("✅ Automation triggered successfully!")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.argument("entity_id")
@click.option(
    "--skip-condition",
    is_flag=True,
    help="Skip the automation's condition check",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(entity_id: str, skip_condition: bool, output_json: bool) -> None:
    """
    Manually trigger an automation.

    ENTITY_ID is the automation entity ID (e.g., automation.morning_routine).

    Use --skip-condition to run the automation actions even if conditions aren't met.

    Examples:

        uv run trigger-automation.py automation.morning_routine

        uv run trigger-automation.py automation.bedtime --skip-condition

        uv run trigger-automation.py automation.test --json
    """
    _validate_config()
    try:
        # Validate entity_id
        if not entity_id.startswith("automation."):
            entity_id = f"automation.{entity_id}"

        with HomeAssistantClient() as client:
            # Verify automation exists
            state = client.get_state(entity_id)
            friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)

            # Trigger automation
            client.trigger_automation(entity_id, skip_condition)

        result = {
            "entity_id": entity_id,
            "friendly_name": friendly_name,
            "skip_condition": skip_condition,
            "success": True,
        }

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            formatted = format_result(entity_id, friendly_name, skip_condition)
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
