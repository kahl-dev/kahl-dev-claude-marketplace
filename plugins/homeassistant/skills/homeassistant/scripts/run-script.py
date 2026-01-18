#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Run Script Script

Execute a Home Assistant script entity.

Usage:
    uv run run-script.py script.morning_routine
    uv run run-script.py script.notify_phone --data '{"message": "Hello"}'
    uv run run-script.py --help
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
    """Minimal HTTP client for Home Assistant REST API - run script"""

    def __init__(self) -> None:
        if not all([HA_URL, HA_TOKEN]):
            raise ValueError(
                "Missing environment variables: HOMEASSISTANT_URL, HOMEASSISTANT_TOKEN"
            )

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
        """Get script state"""
        try:
            response = self.client.get(f"/states/{entity_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                raise Exception(f"Script not found: {entity_id}") from error
            raise Exception(
                f"API error: {error.response.status_code} - {error.response.text}"
            ) from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error

    def run_script(
        self,
        entity_id: str,
        variables: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Run a script with optional variables"""
        try:
            payload: dict[str, Any] = {"entity_id": entity_id}
            if variables:
                payload["variables"] = variables

            response = self.client.post(
                "/services/script/turn_on",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise Exception(
                f"API error: {error.response.status_code} - {error.response.text}"
            ) from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def format_result(
    entity_id: str,
    friendly_name: str,
    variables: dict[str, Any] | None,
) -> str:
    """Format result for human-readable output"""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 80)
    lines.append(f"📜 Script Started: {friendly_name}")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"📍 Entity: {entity_id}")

    if variables:
        lines.append("")
        lines.append("📋 Variables:")
        for key, value in variables.items():
            lines.append(f"   • {key}: {value}")

    lines.append("")
    lines.append("✅ Script started successfully!")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.argument("entity_id")
@click.option(
    "--data",
    "-d",
    help='Variables to pass as JSON string (e.g., \'{"message": "Hello"}\')',
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(entity_id: str, data: str | None, output_json: bool) -> None:
    """
    Execute a Home Assistant script.

    ENTITY_ID is the script entity ID (e.g., script.morning_routine).

    Pass variables with --data as JSON.

    Examples:

        uv run run-script.py script.morning_routine

        uv run run-script.py script.notify_phone --data '{"message": "Hello"}'

        uv run run-script.py script.set_lights --data '{"brightness": 75}'
    """
    try:
        # Validate entity_id
        if not entity_id.startswith("script."):
            entity_id = f"script.{entity_id}"

        # Parse variables JSON if provided
        variables: dict[str, Any] | None = None
        if data:
            try:
                variables = json.loads(data)
            except json.JSONDecodeError as error:
                raise click.UsageError(f"Invalid JSON in --data: {error}") from error

        with HomeAssistantClient() as client:
            # Verify script exists
            state = client.get_state(entity_id)
            friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)

            # Run script
            client.run_script(entity_id, variables)

        result = {
            "entity_id": entity_id,
            "friendly_name": friendly_name,
            "variables": variables,
            "success": True,
        }

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            formatted = format_result(entity_id, friendly_name, variables)
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
