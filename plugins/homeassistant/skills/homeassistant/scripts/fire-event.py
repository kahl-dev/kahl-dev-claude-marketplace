#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Event Firing Script

Fire custom events via WebSocket API.

Usage:
    uv run fire-event.py my_custom_event
    uv run fire-event.py my_custom_event --data '{"key": "value"}'
    uv run fire-event.py --help
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


# Configuration from environment (validated at runtime for --help support)
HA_URL: str = ""
HA_TOKEN: str = ""
WS_TIMEOUT = 30


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
@click.argument("event_type")
@click.option("--data", "-d", type=str, help="Event data as JSON string")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def main(
    event_type: str,
    data: str | None,
    output_json: bool,
) -> None:
    """
    Fire a custom event in Home Assistant.

    EVENT_TYPE is the event name (e.g., my_custom_event).

    Examples:

        uv run fire-event.py my_custom_event

        uv run fire-event.py button_pressed --data '{"button_id": "front_door"}'

        uv run fire-event.py automation_trigger --data '{"source": "cli"}' --json
    """
    _validate_config()
    try:
        # Parse event data
        event_data: dict[str, Any] = {}
        if data:
            try:
                event_data = json.loads(data)
            except json.JSONDecodeError as e:
                raise Exception(f"Invalid JSON in --data: {e}") from e

        # Build params
        params: dict[str, Any] = {"event_type": event_type}
        if event_data:
            params["event_data"] = event_data

        websocket_command("fire_event", params)

        if output_json:
            click.echo(
                json.dumps(
                    {
                        "fired": True,
                        "event_type": event_type,
                        "event_data": event_data,
                    },
                    indent=2,
                )
            )
        else:
            if event_data:
                click.echo(f"✅ Fired event: {event_type} with data: {json.dumps(event_data)}")
            else:
                click.echo(f"✅ Fired event: {event_type}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
