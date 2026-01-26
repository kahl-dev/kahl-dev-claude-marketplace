#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Get Dashboard Script

Get the configuration of a Lovelace dashboard.

Usage:
    uv run get-dashboard.py
    uv run get-dashboard.py lovelace
    uv run get-dashboard.py custom-dashboard --view 0
    uv run get-dashboard.py --json
    uv run get-dashboard.py --help
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
    """Minimal HTTP client for Home Assistant REST API - get dashboard"""

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

    def get_dashboard(self, url_path: str | None = None) -> dict[str, Any]:
        """Get dashboard configuration"""
        try:
            if url_path and url_path != "lovelace":
                endpoint = f"/lovelace/config/{url_path}"
            else:
                endpoint = "/lovelace/config"

            response = self.client.get(endpoint)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                raise Exception(f"Dashboard not found: {url_path or 'lovelace'}") from error
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def format_dashboard(config: dict[str, Any], url_path: str, view_index: int | None) -> str:
    """Format dashboard config for human-readable output"""
    lines: list[str] = []

    title = config.get("title", url_path)
    views = config.get("views", [])

    lines.append("")
    lines.append("=" * 80)
    lines.append(f"📊 Dashboard: {title}")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"📍 URL Path: /{url_path}")
    lines.append(f"📑 Views: {len(views)}")
    lines.append("")

    if view_index is not None:
        # Show specific view
        if view_index >= len(views):
            lines.append(f"❌ View {view_index} not found. Dashboard has {len(views)} views.")
        else:
            view = views[view_index]
            view_title = view.get("title", f"View {view_index}")
            view_path = view.get("path", "")
            cards = view.get("cards", [])

            lines.append(f"📑 View {view_index}: {view_title}")
            if view_path:
                lines.append(f"   Path: {view_path}")
            lines.append(f"   Cards: {len(cards)}")
            lines.append("")
            lines.append("-" * 40)

            for i, card in enumerate(cards):
                card_type = card.get("type", "unknown")
                card_title = card.get("title", "")
                entities = card.get("entities", card.get("entity", ""))

                lines.append(f"   [{i}] {card_type}")
                if card_title:
                    lines.append(f"       Title: {card_title}")
                if entities:
                    if isinstance(entities, list):
                        lines.append(f"       Entities: {len(entities)}")
                    else:
                        lines.append(f"       Entity: {entities}")
    else:
        # Show overview of all views
        lines.append("📑 Views:")
        lines.append("-" * 40)

        for i, view in enumerate(views):
            view_title = view.get("title", f"View {i}")
            view_path = view.get("path", "")
            cards = view.get("cards", [])
            view_icon = view.get("icon", "")

            icon_display = f" {view_icon}" if view_icon else ""
            path_display = f" (/{view_path})" if view_path else ""

            lines.append(f"   [{i}]{icon_display} {view_title}{path_display}")
            lines.append(f"       Cards: {len(cards)}")

    lines.append("")
    lines.append("💡 Tip: Use --view N to see details of a specific view")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.argument("url_path", required=False, default="lovelace")
@click.option(
    "--view",
    "-v",
    type=int,
    help="Show details of specific view (0-indexed)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(url_path: str, view: int | None, output_json: bool) -> None:
    """
    Get Lovelace dashboard configuration.

    URL_PATH is the dashboard path (default: lovelace for main dashboard).

    Examples:

        uv run get-dashboard.py

        uv run get-dashboard.py lovelace

        uv run get-dashboard.py lovelace --view 0

        uv run get-dashboard.py custom-dashboard --json
    """
    _validate_config()
    try:
        with HomeAssistantClient() as client:
            config = client.get_dashboard(url_path)

        if output_json:
            if view is not None:
                # Output specific view
                views = config.get("views", [])
                if view < len(views):
                    click.echo(json.dumps(views[view], indent=2))
                else:
                    click.echo(json.dumps({"error": f"View {view} not found"}, indent=2))
            else:
                click.echo(json.dumps(config, indent=2))
        else:
            formatted = format_dashboard(config, url_path, view)
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
