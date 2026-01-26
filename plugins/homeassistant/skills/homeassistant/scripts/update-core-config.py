#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Core Configuration Update Script

Update core configuration settings via WebSocket API.

Usage:
    uv run update-core-config.py --location-name "Home"
    uv run update-core-config.py --latitude 52.52 --longitude 13.405
    uv run update-core-config.py --elevation 34 --unit-system metric
    uv run update-core-config.py --help
"""

import json
import os
import sys
from typing import Any
from urllib.parse import urlparse, urlunparse

import click
from websocket import WebSocketTimeoutException, create_connection


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
WS_TIMEOUT = 30


def get_websocket_url(base_url: str) -> str:
    """Convert HTTP(S) URL to WebSocket URL using proper parsing."""
    parsed = urlparse(base_url)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    base_path = parsed.path.rstrip("/")
    ws_path = f"{base_path}/api/websocket"
    return urlunparse(parsed._replace(scheme=ws_scheme, path=ws_path))


def websocket_command(command_type: str, params: dict[str, Any] | None = None) -> Any:
    """Execute WebSocket command and return result."""
    ws_url = get_websocket_url(HA_URL)
    ws = None
    try:
        ws = create_connection(ws_url, timeout=WS_TIMEOUT)
        # Auth phase
        ws.recv()  # auth_required
        ws.send(json.dumps({"type": "auth", "access_token": HA_TOKEN}))
        auth_result = json.loads(ws.recv())

        if auth_result.get("type") != "auth_ok":
            raise Exception(f"Authentication failed: {auth_result}")

        # Command phase
        message: dict[str, Any] = {"id": 1, "type": command_type}
        if params:
            message.update(params)
        ws.send(json.dumps(message))
        result = json.loads(ws.recv())

        if not result.get("success"):
            error = result.get("error", {})
            error_code = error.get("code", "unknown")
            if error_code == "unknown_command":
                raise Exception(f"Command '{command_type}' not supported (HA version may be incompatible)")
            raise Exception(f"Command failed: {error.get('message', 'Unknown error')}")

        return result.get("result", {})
    except WebSocketTimeoutException as error:
        raise Exception(f"WebSocket timeout after {WS_TIMEOUT}s") from error
    finally:
        if ws:
            ws.close()


@click.command()
@click.option("--location-name", type=str, help="Name of the location (e.g., 'Home')")
@click.option("--latitude", type=float, help="Latitude of home location")
@click.option("--longitude", type=float, help="Longitude of home location")
@click.option("--elevation", type=int, help="Elevation in meters")
@click.option("--unit-system", type=click.Choice(["metric", "us_customary"]), help="Unit system")
@click.option("--currency", type=str, help="Currency code (e.g., EUR, USD)")
@click.option("--time-zone", type=str, help="Time zone (e.g., Europe/Berlin)")
@click.option("--external-url", type=str, help="External URL for HA")
@click.option("--internal-url", type=str, help="Internal URL for HA")
@click.option("--country", type=str, help="Country code (e.g., DE, US)")
@click.option("--language", type=str, help="Language code (e.g., en, de)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def main(
    location_name: str | None,
    latitude: float | None,
    longitude: float | None,
    elevation: int | None,
    unit_system: str | None,
    currency: str | None,
    time_zone: str | None,
    external_url: str | None,
    internal_url: str | None,
    country: str | None,
    language: str | None,
    output_json: bool,
) -> None:
    """
    Update Home Assistant core configuration.

    At least one option must be provided.

    Examples:

        uv run update-core-config.py --location-name "My Home"

        uv run update-core-config.py --latitude 52.52 --longitude 13.405

        uv run update-core-config.py --unit-system metric --currency EUR

        uv run update-core-config.py --time-zone "Europe/Berlin" --language de
    """
    try:
        # Build update params
        updates: dict[str, Any] = {}

        if location_name is not None:
            updates["location_name"] = location_name
        if latitude is not None:
            updates["latitude"] = latitude
        if longitude is not None:
            updates["longitude"] = longitude
        if elevation is not None:
            updates["elevation"] = elevation
        if unit_system is not None:
            updates["unit_system"] = unit_system
        if currency is not None:
            updates["currency"] = currency
        if time_zone is not None:
            updates["time_zone"] = time_zone
        if external_url is not None:
            updates["external_url"] = external_url
        if internal_url is not None:
            updates["internal_url"] = internal_url
        if country is not None:
            updates["country"] = country
        if language is not None:
            updates["language"] = language

        if not updates:
            click.echo("❌ Error: At least one config option must be provided.", err=True)
            click.echo("   Run with --help to see available options.", err=True)
            sys.exit(1)

        result = websocket_command("config/core/update", updates)

        if output_json:
            click.echo(json.dumps({"updated": updates, "result": result}, indent=2))
        else:
            click.echo("✅ Core configuration updated:")
            for key, value in updates.items():
                click.echo(f"   {key}: {value}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
