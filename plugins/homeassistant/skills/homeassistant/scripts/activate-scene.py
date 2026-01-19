#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Activate Scene Script

Activate a scene.

Usage:
    uv run activate-scene.py scene.movie_night
    uv run activate-scene.py scene.bedtime
    uv run activate-scene.py --help
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
    """Minimal HTTP client for Home Assistant REST API - activate scene"""

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
        """Get scene state"""
        try:
            response = self.client.get(f"/states/{entity_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                raise Exception(f"Scene not found: {entity_id}") from error
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error

    def activate_scene(self, entity_id: str) -> list[dict[str, Any]]:
        """Activate a scene"""
        try:
            response = self.client.post(
                "/services/scene/turn_on",
                json={"entity_id": entity_id},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def format_result(entity_id: str, friendly_name: str) -> str:
    """Format result for human-readable output"""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 80)
    lines.append(f"🎬 Scene Activated: {friendly_name}")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"📍 Entity: {entity_id}")
    lines.append("")
    lines.append("✅ Scene activated successfully!")
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
    Activate a scene.

    ENTITY_ID is the scene entity ID (e.g., scene.movie_night).

    Examples:

        uv run activate-scene.py scene.movie_night

        uv run activate-scene.py scene.bedtime

        uv run activate-scene.py scene.morning --json
    """
    try:
        # Validate entity_id
        if not entity_id.startswith("scene."):
            entity_id = f"scene.{entity_id}"

        with HomeAssistantClient() as client:
            # Verify scene exists
            state = client.get_state(entity_id)
            friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)

            # Activate scene
            client.activate_scene(entity_id)

        result = {
            "entity_id": entity_id,
            "friendly_name": friendly_name,
            "success": True,
        }

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            formatted = format_result(entity_id, friendly_name)
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
