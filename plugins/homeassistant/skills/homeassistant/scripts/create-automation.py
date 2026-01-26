#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Create Automation Script

Create a new automation via the REST API using a JSON configuration.

Usage:
    uv run create-automation.py '{"id": "test", "alias": "Test", "trigger": [], "action": []}'
    uv run create-automation.py --json '{"id": "test", "alias": "Test"}'
    uv run create-automation.py --help
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
    """Minimal HTTP client for Home Assistant REST API - create automation"""

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

    def create_automation(self, config: dict[str, Any]) -> dict[str, Any]:
        """Create automation via config endpoint"""
        automation_id = config.get("id", "new")
        try:
            response = self.client.post(
                f"/config/automation/config/{automation_id}",
                json=config,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def format_create_result(config: dict[str, Any], response: dict[str, Any]) -> str:
    """Format creation result for human-readable output"""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 80)
    lines.append("✅ Automation Created")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"🆔 ID: {config.get('id', 'new')}")
    lines.append(f"📝 Alias: {config.get('alias', 'Unknown')}")
    lines.append(f"📍 Endpoint: /api/config/automation/config/{config.get('id', 'new')}")
    lines.append("")
    lines.append("Response:")
    lines.append(json.dumps(response, indent=2))
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.argument("automation_config", type=str)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(automation_config: str, output_json: bool) -> None:
    """
    Create a Home Assistant automation via REST API.

    AUTOMATION_CONFIG is a JSON string containing the automation configuration.
    Must include at minimum: id, alias, trigger, action.

    Examples:

        uv run create-automation.py '{"id": "test_auto", "alias": "Test", "trigger": [], "action": []}'

        uv run create-automation.py --json '{"id": "morning", "alias": "Morning Routine"}'
    """
    _validate_config()
    try:
        # Parse automation config
        try:
            config = json.loads(automation_config)
        except json.JSONDecodeError as error:
            raise click.UsageError(f"Invalid JSON configuration: {error}") from error

        if not isinstance(config, dict):
            raise click.UsageError("Configuration must be a JSON object")

        with HomeAssistantClient() as client:
            response = client.create_automation(config)

        result = {
            "success": True,
            "automation_id": config.get("id", "new"),
            "alias": config.get("alias"),
            "response": response,
        }

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            formatted = format_create_result(config, response)
            click.echo(formatted)

        sys.exit(0)

    except click.UsageError:
        raise
    except Exception as error:
        error_data = {"error": str(error), "success": False}
        if output_json:
            click.echo(json.dumps(error_data, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
