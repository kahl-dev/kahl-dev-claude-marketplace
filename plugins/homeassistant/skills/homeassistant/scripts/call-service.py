#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Call Service Script

Call any Home Assistant service. This is the universal script for all HA operations.

Usage:
    uv run call-service.py light turn_on --entity light.living_room
    uv run call-service.py light turn_on --entity light.bedroom --data '{"brightness_pct": 50}'
    uv run call-service.py climate set_temperature --entity climate.thermostat --data '{"temperature": 22}'
    uv run call-service.py --help
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


# Configuration from environment
HA_URL = get_required_env(
    "HOMEASSISTANT_URL",
    "Your HA instance URL, e.g., http://homeassistant.local:8123",
)
HA_TOKEN = get_required_env(
    "HOMEASSISTANT_TOKEN",
    "Get from: HA → Profile → Security → Long-Lived Access Tokens",
)
API_TIMEOUT = 30.0
USER_AGENT = "HomeAssistant-CLI/1.0"


class HomeAssistantClient:
    """Minimal HTTP client for Home Assistant REST API - call service"""

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

    def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Call a Home Assistant service"""
        try:
            payload: dict[str, Any] = data.copy() if data else {}
            if entity_id:
                payload["entity_id"] = entity_id

            response = self.client.post(
                f"/services/{domain}/{service}",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error

    def list_services(self) -> list[dict[str, Any]]:
        """List all available services"""
        try:
            response = self.client.get("/services")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def format_result(
    domain: str,
    service: str,
    entity_id: str | None,
    result: list[dict[str, Any]],
) -> str:
    """Format service call result for human-readable output"""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 80)
    lines.append(f"✅ Service Called: {domain}.{service}")
    lines.append("=" * 80)
    lines.append("")

    if entity_id:
        lines.append(f"📍 Entity: {entity_id}")

    if result:
        lines.append("")
        lines.append("📋 Affected Entities:")
        lines.append("-" * 40)
        for entity in result:
            eid = entity.get("entity_id", "unknown")
            state = entity.get("state", "unknown")
            state_emoji = "🟢" if state == "on" else "🔴" if state == "off" else "⚪"
            lines.append(f"  {state_emoji} {eid}: {state}")
    else:
        lines.append("")
        lines.append("ℹ️  Service called successfully (no state change reported)")

    lines.append("")

    return "\n".join(lines)


def format_services(services: list[dict[str, Any]], domain_filter: str | None) -> str:
    """Format available services for human-readable output"""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 80)
    lines.append("🔧 Available Services")
    lines.append("=" * 80)

    for domain_info in sorted(services, key=lambda x: x.get("domain", "")):
        domain = domain_info.get("domain", "unknown")

        if domain_filter and domain != domain_filter:
            continue

        domain_services = domain_info.get("services", {})
        if not domain_services:
            continue

        lines.append("")
        lines.append(f"📦 {domain.upper()}")
        lines.append("-" * 40)

        for service_name, service_info in sorted(domain_services.items()):
            description = service_info.get("description", "No description")
            lines.append(f"  • {domain}.{service_name}")
            lines.append(f"    {description[:60]}...")

    lines.append("")

    return "\n".join(lines)


@click.command()
@click.argument("domain", required=False)
@click.argument("service", required=False)
@click.option(
    "--entity",
    "-e",
    help="Target entity ID (e.g., light.living_room)",
)
@click.option(
    "--data",
    "-d",
    help="Service data as JSON string (e.g., '{\"brightness_pct\": 50}')",
)
@click.option(
    "--list-services",
    "-l",
    is_flag=True,
    help="List all available services",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(
    domain: str | None,
    service: str | None,
    entity: str | None,
    data: str | None,
    list_services: bool,
    output_json: bool,
) -> None:
    """
    Call any Home Assistant service.

    DOMAIN is the service domain (light, switch, climate, etc.)
    SERVICE is the service name (turn_on, turn_off, toggle, etc.)

    Use --list-services to see all available services.

    Examples:

        uv run call-service.py --list-services

        uv run call-service.py light turn_on --entity light.living_room

        uv run call-service.py light turn_on --entity light.bedroom --data '{"brightness_pct": 50}'

        uv run call-service.py climate set_temperature --entity climate.thermostat --data '{"temperature": 22}'

        uv run call-service.py script turn_on --entity script.morning_routine
    """
    try:
        with HomeAssistantClient() as client:
            if list_services:
                services = client.list_services()
                if output_json:
                    click.echo(json.dumps(services, indent=2))
                else:
                    formatted = format_services(services, domain)
                    click.echo(formatted)
            else:
                if not domain or not service:
                    raise click.UsageError(
                        "DOMAIN and SERVICE are required. Use --list-services to see available services."
                    )

                # Parse data JSON if provided
                service_data: dict[str, Any] | None = None
                if data:
                    try:
                        service_data = json.loads(data)
                    except json.JSONDecodeError as error:
                        raise click.UsageError(f"Invalid JSON in --data: {error}") from error

                result = client.call_service(domain, service, entity, service_data)

                if output_json:
                    click.echo(json.dumps(result, indent=2))
                else:
                    formatted = format_result(domain, service, entity, result)
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
