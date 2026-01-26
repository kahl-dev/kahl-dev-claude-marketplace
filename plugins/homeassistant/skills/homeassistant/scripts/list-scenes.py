#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant List Scenes Script

List all scenes available in Home Assistant.

Usage:
    uv run list-scenes.py
    uv run list-scenes.py --search "movie"
    uv run list-scenes.py --json
    uv run list-scenes.py --help
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
    """Minimal HTTP client for Home Assistant REST API - scenes"""

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

    def get_scenes(self) -> list[dict[str, Any]]:
        """Get all scene entities"""
        try:
            response = self.client.get("/states")
            response.raise_for_status()
            all_states = response.json()
            return [s for s in all_states if s.get("entity_id", "").startswith("scene.")]
        except httpx.HTTPStatusError as error:
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def format_scenes(scenes: list[dict[str, Any]]) -> str:
    """Format scenes for human-readable output"""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 80)
    lines.append("🎬 Home Assistant Scenes")
    lines.append("=" * 80)
    lines.append("")

    if not scenes:
        lines.append("No scenes found.")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"Total: {len(scenes)} scenes")
    lines.append("")
    lines.append("-" * 80)

    for scene in sorted(scenes, key=lambda x: x.get("entity_id", "")):
        entity_id = scene.get("entity_id", "unknown")
        attributes = scene.get("attributes", {})
        friendly_name = attributes.get("friendly_name", entity_id)
        entity_ids = attributes.get("entity_id", [])

        lines.append(f"🎬 {friendly_name}")
        lines.append(f"   ID: {entity_id}")
        if entity_ids:
            lines.append(f"   Controls: {len(entity_ids)} entities")
        lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--search",
    "-s",
    help="Search scenes by name (case-insensitive)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(search: str | None, output_json: bool) -> None:
    """
    List all Home Assistant scenes.

    Examples:

        uv run list-scenes.py

        uv run list-scenes.py --search "movie"

        uv run list-scenes.py --json
    """
    _validate_config()
    try:
        with HomeAssistantClient() as client:
            scenes = client.get_scenes()

        # Apply search filter
        if search:
            search_lower = search.lower()
            scenes = [
                s
                for s in scenes
                if search_lower in s.get("entity_id", "").lower()
                or search_lower in s.get("attributes", {}).get("friendly_name", "").lower()
            ]

        if output_json:
            click.echo(json.dumps(scenes, indent=2))
        else:
            formatted = format_scenes(scenes)
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
