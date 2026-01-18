#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant List Dashboards Script

List all Lovelace dashboards.

Usage:
    uv run list-dashboards.py
    uv run list-dashboards.py --json
    uv run list-dashboards.py --help
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
    """Minimal HTTP client for Home Assistant REST API - dashboards"""

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

    def list_dashboards(self) -> list[dict[str, Any]]:
        """List all Lovelace dashboards"""
        try:
            response = self.client.get("/lovelace/dashboards")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                # No custom dashboards, return empty with note about default
                return []
            raise Exception(
                f"API error: {error.response.status_code} - {error.response.text}"
            ) from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def format_dashboards(dashboards: list[dict[str, Any]]) -> str:
    """Format dashboards for human-readable output"""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 80)
    lines.append("📊 Home Assistant Dashboards")
    lines.append("=" * 80)
    lines.append("")

    # Always mention default dashboard
    lines.append("📌 Default Dashboard")
    lines.append("   URL: /lovelace")
    lines.append("   Path: lovelace (use with get-dashboard.py)")
    lines.append("")

    if not dashboards:
        lines.append("No additional custom dashboards found.")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"Custom Dashboards: {len(dashboards)}")
    lines.append("-" * 80)

    for dashboard in sorted(dashboards, key=lambda x: x.get("url_path", "")):
        url_path = dashboard.get("url_path", "unknown")
        title = dashboard.get("title", url_path)
        mode = dashboard.get("mode", "storage")
        show_in_sidebar = dashboard.get("show_in_sidebar", True)
        icon = dashboard.get("icon", "mdi:view-dashboard")

        sidebar_emoji = "👁️" if show_in_sidebar else "🚫"

        lines.append(f"📊 {title}")
        lines.append(f"   URL: /{url_path}")
        lines.append(f"   Mode: {mode}")
        lines.append(f"   Icon: {icon}")
        lines.append(
            f"   {sidebar_emoji} In Sidebar: {'Yes' if show_in_sidebar else 'No'}"
        )
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
    List all Lovelace dashboards.

    Shows both the default dashboard and any custom dashboards.

    Examples:

        uv run list-dashboards.py

        uv run list-dashboards.py --json
    """
    try:
        with HomeAssistantClient() as client:
            dashboards = client.list_dashboards()

        # Add default dashboard to list for JSON output
        result = [
            {
                "url_path": "lovelace",
                "title": "Default Dashboard",
                "mode": "storage",
                "show_in_sidebar": True,
                "is_default": True,
            }
        ] + dashboards

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            formatted = format_dashboards(dashboards)
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
