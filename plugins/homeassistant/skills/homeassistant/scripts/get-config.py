#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Get Config Script

Get Home Assistant configuration information.

Usage:
    uv run get-config.py
    uv run get-config.py --json
    uv run get-config.py --help
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
    """Minimal HTTP client for Home Assistant REST API - config"""

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

    def get_config(self) -> dict[str, Any]:
        """Get HA configuration"""
        try:
            response = self.client.get("/config")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error

    def check_api(self) -> dict[str, Any]:
        """Check API status"""
        try:
            response = self.client.get("/")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def format_config(config: dict[str, Any], api_status: dict[str, Any]) -> str:
    """Format config for human-readable output"""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 80)
    lines.append("🏠 Home Assistant Configuration")
    lines.append("=" * 80)
    lines.append("")

    # API Status
    api_message = api_status.get("message", "Unknown")
    lines.append(f"✅ API Status: {api_message}")
    lines.append("")

    # Basic Info
    lines.append("📋 Basic Information")
    lines.append("-" * 40)
    lines.append(f"   Version: {config.get('version', 'Unknown')}")
    lines.append(f"   Location: {config.get('location_name', 'Unknown')}")
    lines.append(f"   Timezone: {config.get('time_zone', 'Unknown')}")
    lines.append(f"   Elevation: {config.get('elevation', 'Unknown')}m")
    lines.append("")

    # Location
    latitude = config.get("latitude", "Unknown")
    longitude = config.get("longitude", "Unknown")
    lines.append("📍 Location")
    lines.append("-" * 40)
    lines.append(f"   Latitude: {latitude}")
    lines.append(f"   Longitude: {longitude}")
    lines.append("")

    # Units
    lines.append("📏 Units")
    lines.append("-" * 40)
    unit_system = config.get("unit_system", {})
    lines.append(f"   Temperature: {unit_system.get('temperature', 'Unknown')}")
    lines.append(f"   Length: {unit_system.get('length', 'Unknown')}")
    lines.append(f"   Mass: {unit_system.get('mass', 'Unknown')}")
    lines.append(f"   Volume: {unit_system.get('volume', 'Unknown')}")
    lines.append("")

    # Components
    components = config.get("components", [])
    lines.append(f"🧩 Components: {len(components)} loaded")
    lines.append("")

    # State
    state = config.get("state", "unknown")
    safe_mode = config.get("safe_mode", False)
    lines.append("⚙️ State")
    lines.append("-" * 40)
    lines.append(f"   State: {state}")
    lines.append(f"   Safe Mode: {'Yes' if safe_mode else 'No'}")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(output_json: bool) -> None:
    """
    Get Home Assistant configuration information.

    Shows version, location, units, and system state.

    Examples:

        uv run get-config.py

        uv run get-config.py --json
    """
    _validate_config()
    try:
        with HomeAssistantClient() as client:
            config = client.get_config()
            api_status = client.check_api()

        if output_json:
            result = {
                "config": config,
                "api_status": api_status,
            }
            click.echo(json.dumps(result, indent=2))
        else:
            formatted = format_config(config, api_status)
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
