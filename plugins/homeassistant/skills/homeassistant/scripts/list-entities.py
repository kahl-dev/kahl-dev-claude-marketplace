#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant List Entities Script

List all entities with their current states. Filter by domain or search by name.

Usage:
    uv run list-entities.py
    uv run list-entities.py --domain light
    uv run list-entities.py --domain sensor --search temperature
    uv run list-entities.py --json
    uv run list-entities.py --help
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
    """Minimal HTTP client for Home Assistant REST API - list entities"""

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

    def get_states(self) -> list[dict[str, Any]]:
        """Get all entity states"""
        try:
            response = self.client.get("/states")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise Exception(
                f"API error: {error.response.status_code} - {error.response.text}"
            ) from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def format_entities(entities: list[dict[str, Any]], domain: str | None) -> str:
    """Format entities for human-readable output"""
    lines: list[str] = []

    # Group by domain
    by_domain: dict[str, list[dict[str, Any]]] = {}
    for entity in entities:
        entity_id = entity.get("entity_id", "")
        entity_domain = entity_id.split(".")[0] if "." in entity_id else "unknown"

        if domain and entity_domain != domain:
            continue

        if entity_domain not in by_domain:
            by_domain[entity_domain] = []
        by_domain[entity_domain].append(entity)

    if not by_domain:
        return "No entities found."

    lines.append("")
    lines.append("=" * 80)
    lines.append("🏠 Home Assistant Entities")
    lines.append("=" * 80)

    total = 0
    for domain_name in sorted(by_domain.keys()):
        domain_entities = by_domain[domain_name]
        total += len(domain_entities)

        lines.append("")
        lines.append(f"📦 {domain_name.upper()} ({len(domain_entities)} entities)")
        lines.append("-" * 40)

        for entity in sorted(domain_entities, key=lambda x: x.get("entity_id", "")):
            entity_id = entity.get("entity_id", "unknown")
            state = entity.get("state", "unknown")
            friendly_name = entity.get("attributes", {}).get("friendly_name", "")

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

            name_display = f" ({friendly_name})" if friendly_name else ""
            lines.append(f"  {state_emoji} {entity_id}{name_display}: {state}")

    lines.append("")
    lines.append("-" * 80)
    lines.append(f"Total: {total} entities")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--domain",
    "-d",
    help="Filter by domain (light, switch, sensor, binary_sensor, etc.)",
)
@click.option(
    "--search",
    "-s",
    help="Search entities by name pattern (case-insensitive)",
)
@click.option(
    "--state",
    help="Filter by state (on, off, unavailable, etc.)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(
    domain: str | None,
    search: str | None,
    state: str | None,
    output_json: bool,
) -> None:
    """
    List all Home Assistant entities with their current states.

    Filter by domain (--domain light), search by name (--search bedroom),
    or filter by state (--state on).

    Examples:

        uv run list-entities.py

        uv run list-entities.py --domain light

        uv run list-entities.py --domain sensor --search temperature

        uv run list-entities.py --state on --json
    """
    try:
        with HomeAssistantClient() as client:
            entities = client.get_states()

        # Apply filters
        filtered = entities

        if domain:
            filtered = [
                entity
                for entity in filtered
                if entity.get("entity_id", "").startswith(f"{domain}.")
            ]

        if search:
            search_lower = search.lower()
            filtered = [
                entity
                for entity in filtered
                if search_lower in entity.get("entity_id", "").lower()
                or search_lower
                in entity.get("attributes", {}).get("friendly_name", "").lower()
            ]

        if state:
            filtered = [entity for entity in filtered if entity.get("state") == state]

        if output_json:
            click.echo(json.dumps(filtered, indent=2))
        else:
            formatted = format_entities(filtered, domain=None)
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
