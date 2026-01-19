#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Get History Script

Get state history for an entity over a time range.

Usage:
    uv run get-history.py sensor.temperature
    uv run get-history.py sensor.temperature --hours 24
    uv run get-history.py light.living_room --start "2024-01-01T00:00:00"
    uv run get-history.py --help
"""

import json
import os
import sys
from datetime import UTC, datetime, timedelta
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
API_TIMEOUT = 60.0  # History can be slow
USER_AGENT = "HomeAssistant-CLI/1.0"


class HomeAssistantClient:
    """Minimal HTTP client for Home Assistant REST API - history"""

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

    def get_history(
        self,
        entity_id: str,
        start_time: datetime,
        end_time: datetime | None = None,
    ) -> list[list[dict[str, Any]]]:
        """Get entity state history"""
        try:
            # Format timestamps for API
            timestamp = start_time.isoformat()
            params: dict[str, str] = {
                "filter_entity_id": entity_id,
                "minimal_response": "false",
                "significant_changes_only": "false",
            }

            if end_time:
                params["end_time"] = end_time.isoformat()

            response = self.client.get(
                f"/history/period/{timestamp}",
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def format_history(
    entity_id: str,
    history: list[dict[str, Any]],
    start_time: datetime,
) -> str:
    """Format history for human-readable output"""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 80)
    lines.append(f"📊 History: {entity_id}")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"📅 From: {start_time.isoformat()}")
    lines.append(f"📈 Data Points: {len(history)}")
    lines.append("")

    if not history:
        lines.append("No history data found for this time range.")
        lines.append("")
        return "\n".join(lines)

    lines.append("📋 State Changes:")
    lines.append("-" * 60)

    # Show state changes (limit to last 50 for readability)
    display_history = history[-50:] if len(history) > 50 else history

    if len(history) > 50:
        lines.append(f"  (Showing last 50 of {len(history)} entries)")
        lines.append("")

    for entry in display_history:
        state = entry.get("state", "unknown")
        last_changed = entry.get("last_changed", "")

        # Parse and format timestamp
        if last_changed:
            try:
                timestamp = datetime.fromisoformat(last_changed.replace("Z", "+00:00"))
                time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                time_str = last_changed
        else:
            time_str = "unknown"

        state_emoji = "⚪"
        if state == "on":
            state_emoji = "🟢"
        elif state == "off":
            state_emoji = "🔴"
        elif state == "unavailable":
            state_emoji = "⚫"

        lines.append(f"  {time_str}  {state_emoji} {state}")

    lines.append("")

    # Statistics for numeric sensors
    numeric_states = []
    for entry in history:
        try:
            value = float(entry.get("state", ""))
            numeric_states.append(value)
        except (ValueError, TypeError):
            pass

    if numeric_states:
        lines.append("📉 Statistics:")
        lines.append("-" * 40)
        lines.append(f"  Min: {min(numeric_states):.2f}")
        lines.append(f"  Max: {max(numeric_states):.2f}")
        lines.append(f"  Avg: {sum(numeric_states) / len(numeric_states):.2f}")
        lines.append(f"  Latest: {numeric_states[-1]:.2f}")
        lines.append("")

    return "\n".join(lines)


@click.command()
@click.argument("entity_id")
@click.option(
    "--hours",
    "-h",
    type=int,
    default=1,
    help="Hours of history to fetch (default: 1)",
)
@click.option(
    "--start",
    "-s",
    help="Start time (ISO format: 2024-01-01T00:00:00). Overrides --hours.",
)
@click.option(
    "--end",
    "-e",
    help="End time (ISO format). Defaults to now.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(
    entity_id: str,
    hours: int,
    start: str | None,
    end: str | None,
    output_json: bool,
) -> None:
    """
    Get state history for an entity.

    ENTITY_ID is the full entity ID (e.g., sensor.temperature).

    Examples:

        uv run get-history.py sensor.temperature

        uv run get-history.py sensor.temperature --hours 24

        uv run get-history.py light.living_room --hours 12

        uv run get-history.py sensor.power --start "2024-01-01T00:00:00"

        uv run get-history.py sensor.humidity --hours 48 --json
    """
    try:
        # Determine time range
        if start:
            try:
                start_time = datetime.fromisoformat(start)
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=UTC)
            except ValueError as error:
                raise click.UsageError(f"Invalid start time format: {start}. Use ISO format.") from error
        else:
            start_time = datetime.now(UTC) - timedelta(hours=hours)

        end_time: datetime | None = None
        if end:
            try:
                end_time = datetime.fromisoformat(end)
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=UTC)
            except ValueError as error:
                raise click.UsageError(f"Invalid end time format: {end}. Use ISO format.") from error

        with HomeAssistantClient() as client:
            result = client.get_history(entity_id, start_time, end_time)

        # Result is a list of lists (one per entity)
        history = result[0] if result else []

        if output_json:
            click.echo(json.dumps(history, indent=2))
        else:
            formatted = format_history(entity_id, history, start_time)
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
