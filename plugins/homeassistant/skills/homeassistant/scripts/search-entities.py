#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Search Entities Script

Search entities by name pattern, domain, state, or attributes.

Usage:
    uv run search-entities.py "bedroom"
    uv run search-entities.py "temperature" --domain sensor
    uv run search-entities.py --state on --domain light
    uv run search-entities.py --help
"""

import json
import os
import re
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
    """Minimal HTTP client for Home Assistant REST API - search entities"""

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


def matches_pattern(text: str, pattern: str, use_regex: bool) -> bool:
    """Check if text matches pattern"""
    if use_regex:
        try:
            return bool(re.search(pattern, text, re.IGNORECASE))
        except re.error:
            return pattern.lower() in text.lower()
    return pattern.lower() in text.lower()


def format_search_results(entities: list[dict[str, Any]], query: str | None) -> str:
    """Format search results for human-readable output"""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 80)
    if query:
        lines.append(f'🔍 Search Results for: "{query}"')
    else:
        lines.append("🔍 Search Results")
    lines.append("=" * 80)
    lines.append("")

    if not entities:
        lines.append("No entities found matching criteria.")
        lines.append("")
        return "\n".join(lines)

    # Group by domain
    by_domain: dict[str, list[dict[str, Any]]] = {}
    for entity in entities:
        entity_id = entity.get("entity_id", "")
        domain = entity_id.split(".")[0] if "." in entity_id else "unknown"
        if domain not in by_domain:
            by_domain[domain] = []
        by_domain[domain].append(entity)

    for domain in sorted(by_domain.keys()):
        domain_entities = by_domain[domain]
        lines.append(f"📦 {domain.upper()} ({len(domain_entities)})")
        lines.append("-" * 40)

        for entity in sorted(domain_entities, key=lambda x: x.get("entity_id", "")):
            entity_id = entity.get("entity_id", "unknown")
            state = entity.get("state", "unknown")
            friendly_name = entity.get("attributes", {}).get("friendly_name", "")

            state_emoji = "⚪"
            if state == "on":
                state_emoji = "🟢"
            elif state == "off":
                state_emoji = "🔴"
            elif state == "unavailable":
                state_emoji = "⚫"

            name_display = f" ({friendly_name})" if friendly_name else ""
            lines.append(f"  {state_emoji} {entity_id}{name_display}")
            lines.append(f"      State: {state}")

        lines.append("")

    lines.append("-" * 80)
    lines.append(f"Found: {len(entities)} entities")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.argument("pattern", required=False)
@click.option(
    "--domain",
    "-d",
    help="Filter by domain (light, switch, sensor, etc.)",
)
@click.option(
    "--state",
    "-s",
    help="Filter by state (on, off, unavailable, etc.)",
)
@click.option(
    "--attribute",
    "-a",
    multiple=True,
    help="Filter by attribute (format: key=value). Can be used multiple times.",
)
@click.option(
    "--regex",
    "-r",
    is_flag=True,
    help="Use regex pattern matching",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    default=50,
    help="Maximum number of results (default: 50)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(
    pattern: str | None,
    domain: str | None,
    state: str | None,
    attribute: tuple[str, ...],
    regex: bool,
    limit: int,
    output_json: bool,
) -> None:
    """
    Search entities by name pattern, domain, state, or attributes.

    PATTERN is an optional search string to match against entity_id or friendly_name.

    Examples:

        uv run search-entities.py "bedroom"

        uv run search-entities.py "temperature" --domain sensor

        uv run search-entities.py --state on --domain light

        uv run search-entities.py --domain binary_sensor --state off

        uv run search-entities.py "motion" --regex

        uv run search-entities.py --attribute device_class=motion
    """
    _validate_config()
    try:
        with HomeAssistantClient() as client:
            entities = client.get_states()

        # Apply filters
        filtered = entities

        # Domain filter
        if domain:
            filtered = [e for e in filtered if e.get("entity_id", "").startswith(f"{domain}.")]

        # Pattern filter
        if pattern:
            new_filtered = []
            for entity in filtered:
                entity_id = entity.get("entity_id", "")
                friendly_name = entity.get("attributes", {}).get("friendly_name", "")
                if matches_pattern(entity_id, pattern, regex) or matches_pattern(friendly_name, pattern, regex):
                    new_filtered.append(entity)
            filtered = new_filtered

        # State filter
        if state:
            filtered = [e for e in filtered if e.get("state") == state]

        # Attribute filters
        for attr_filter in attribute:
            if "=" not in attr_filter:
                continue
            key, value = attr_filter.split("=", 1)
            filtered = [e for e in filtered if str(e.get("attributes", {}).get(key, "")) == value]

        # Apply limit
        filtered = filtered[:limit]

        if output_json:
            click.echo(json.dumps(filtered, indent=2))
        else:
            formatted = format_search_results(filtered, pattern)
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
