#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Check Config Script

Validate Home Assistant configuration via REST API.

Usage:
    uv run check-config.py
    uv run check-config.py --json
    uv run check-config.py --help
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
API_TIMEOUT = 60.0  # Config check can take time
USER_AGENT = "HomeAssistant-CLI/1.0"


class HomeAssistantClient:
    """Minimal HTTP client for Home Assistant REST API - config check"""

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

    def check_config(self) -> dict[str, Any]:
        """Validate Home Assistant configuration"""
        try:
            response = self.client.post("/config/core/check_config")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def format_config_result(result: dict[str, Any]) -> str:
    """Format config check result for human-readable output."""
    lines: list[str] = []

    status = result.get("result", "unknown")
    errors = result.get("errors", None)
    warnings = result.get("warnings", None)

    lines.append("")
    lines.append("=" * 80)
    lines.append("🔍 Home Assistant Configuration Check")
    lines.append("=" * 80)
    lines.append("")

    if status == "valid":
        lines.append("✅ Configuration is VALID")
    else:
        lines.append("❌ Configuration is INVALID")

    # Show errors
    if errors:
        lines.append("")
        lines.append("❌ ERRORS:")
        lines.append("-" * 40)
        if isinstance(errors, str):
            lines.append(f"  {errors}")
        elif isinstance(errors, list):
            for error in errors:
                lines.append(f"  • {error}")

    # Show warnings
    if warnings:
        lines.append("")
        lines.append("⚠️ WARNINGS:")
        lines.append("-" * 40)
        if isinstance(warnings, str):
            lines.append(f"  {warnings}")
        elif isinstance(warnings, list):
            for warning in warnings:
                lines.append(f"  • {warning}")

    if not errors and not warnings and status == "valid":
        lines.append("")
        lines.append("  No errors or warnings detected.")

    lines.append("")
    lines.append("-" * 80)
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
    Validate Home Assistant configuration via REST API.

    Checks configuration files for errors and warnings before applying changes.
    This is the same check that runs when you click "Check Configuration" in the UI.

    Examples:

        uv run check-config.py

        uv run check-config.py --json
    """
    try:
        with HomeAssistantClient() as client:
            result = client.check_config()

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            formatted = format_config_result(result)
            click.echo(formatted)

        # Exit with error code if config is invalid
        if result.get("result") != "valid":
            sys.exit(1)
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
