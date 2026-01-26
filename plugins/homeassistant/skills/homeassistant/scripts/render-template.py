#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Template Rendering Script

Render Jinja2 templates via WebSocket API.

Usage:
    uv run render-template.py "{{ states('sensor.temperature') }}"
    uv run render-template.py "{{ state_attr('light.bedroom', 'brightness') }}"
    uv run render-template.py --file template.j2
    uv run render-template.py --help
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


def render_template_ws(template: str, timeout: int | None = None) -> str:
    """
    Render template via WebSocket subscription.

    render_template is a subscription command that returns:
    1. Initial success response with result: null
    2. Event message with rendered result
    """
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

        # Subscribe to render_template
        message: dict[str, Any] = {"id": 1, "type": "render_template", "template": template}
        if timeout is not None:
            message["timeout"] = timeout
        ws.send(json.dumps(message))

        # First response: subscription confirmation
        result = json.loads(ws.recv())
        if not result.get("success"):
            error = result.get("error", {})
            error_code = error.get("code", "unknown")
            if error_code == "unknown_command":
                raise Exception("render_template not supported (HA version may be incompatible)")
            raise Exception(f"Command failed: {error.get('message', 'Unknown error')}")

        # Second response: event with rendered result
        event = json.loads(ws.recv())
        if event.get("type") == "event":
            return event.get("event", {}).get("result", "")
        else:
            raise Exception(f"Unexpected response type: {event.get('type')}")

    except WebSocketTimeoutException as error:
        raise Exception(f"WebSocket timeout after {WS_TIMEOUT}s") from error
    finally:
        if ws:
            ws.close()


@click.command()
@click.argument("template", required=False)
@click.option("--file", "-f", "template_file", type=click.Path(exists=True), help="Read template from file")
@click.option("--timeout", type=int, help="Render timeout in seconds (default: no timeout)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def main(
    template: str | None,
    template_file: str | None,
    timeout: int | None,
    output_json: bool,
) -> None:
    """
    Render a Jinja2 template using Home Assistant's template engine.

    Provide template as argument or use --file to read from file.

    Examples:

        uv run render-template.py "{{ states('sensor.temperature') }}"

        uv run render-template.py "{{ state_attr('light.bedroom', 'brightness') }}"

        uv run render-template.py "{{ now().strftime('%H:%M') }}"

        uv run render-template.py --file my-template.j2

        uv run render-template.py "{{ states.light | list | count }}" --json
    """
    _validate_config()
    try:
        # Get template content
        if template_file:
            with open(template_file) as f:
                template_content = f.read()
        elif template:
            template_content = template
        else:
            click.echo("❌ Error: Provide template as argument or use --file", err=True)
            sys.exit(1)

        result = render_template_ws(template_content, timeout)

        if output_json:
            click.echo(json.dumps({"template": template_content, "result": result}, indent=2))
        else:
            click.echo(result)

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
