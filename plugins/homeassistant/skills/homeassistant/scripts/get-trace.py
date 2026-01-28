#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Get Trace Script

Fetch automation/script execution trace details via WebSocket API.
Shows smart formatted output by default (executed path only).

Usage:
    uv run get-trace.py automation.my_automation
    uv run get-trace.py automation.my_automation --run-id abc123
    uv run get-trace.py automation.my_automation --verbose
    uv run get-trace.py automation.my_automation --json
    uv run get-trace.py --help
"""

import json
import os
import sys
from datetime import datetime
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


def websocket_command(command_type: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
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
        message = {"id": 1, "type": command_type}
        if data:
            message.update(data)
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


def get_latest_run_id(domain: str, item_id: str) -> str | None:
    """Get the most recent run_id for an automation/script."""
    data = {"domain": domain, "item_id": item_id}
    result = websocket_command("trace/list", data)

    # Result structure: {domain: {item_id: [traces]}}
    traces = result.get(domain, {}).get(item_id, [])
    if traces:
        return traces[0].get("run_id")
    return None


def format_trace_node(node: dict[str, Any], indent: int = 0) -> list[str]:
    """Format a single trace node."""
    lines: list[str] = []
    prefix = "  " * indent

    path = node.get("path", "unknown")
    result = node.get("result", {})
    error = node.get("error")

    # Determine status
    if error:
        status_icon = "✗"
    elif result:
        status_icon = "✓"
    else:
        status_icon = "→"

    # Build description based on path type
    description = path

    # Check for specific node types and extract useful info
    if "trigger" in path:
        trigger_output = result.get("trigger", {}) if result else {}
        if trigger_output:
            platform = trigger_output.get("platform", "")
            entity_id = trigger_output.get("entity_id", "")
            to_state = trigger_output.get("to_state", {}).get("state", "") if trigger_output.get("to_state") else ""
            if entity_id:
                description = f"Trigger: {platform} - {entity_id}"
                if to_state:
                    description += f' → "{to_state}"'
            else:
                description = f"Trigger: {platform}"

    elif "condition" in path:
        condition_result = result.get("result", None) if result else None
        if condition_result is not None:
            description = f"Condition: {'PASS' if condition_result else 'FAIL'}"
        else:
            description = "Condition"

    elif "action" in path:
        # Try to get action details
        if result:
            # Check for service calls
            if "params" in result:
                params = result.get("params", {})
                domain_action = params.get("domain", "") + "." + params.get("service", "")
                if domain_action != ".":
                    description = f"Action: {domain_action}"
            # Check for repeat actions
            elif "item" in result:
                description = "Action: repeat iteration"
            else:
                description = "Action"
        else:
            description = "Action"

    lines.append(f"{prefix}{status_icon} {description}")

    if error:
        lines.append(f"{prefix}  Error: {error}")

    return lines


def format_trace_smart(trace: dict[str, Any], entity_id: str, verbose: bool = False) -> str:
    """Format trace with smart output - show executed path only."""
    lines: list[str] = []

    run_id = trace.get("run_id", "unknown")
    timestamp = trace.get("timestamp", {})
    start = timestamp.get("start", "")
    finish = timestamp.get("finish", "")
    state = trace.get("state", "unknown")
    script_execution = trace.get("script_execution", "unknown")

    # Format timestamps
    try:
        start_str = (
            datetime.fromisoformat(start.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S") if start else "unknown"
        )
    except (ValueError, AttributeError):
        start_str = start or "unknown"

    try:
        if finish:
            finish_dt = datetime.fromisoformat(finish.replace("Z", "+00:00"))
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00")) if start else None
            if start_dt:
                duration = (finish_dt - start_dt).total_seconds()
                duration_str = f"{duration:.2f}s"
            else:
                duration_str = "unknown"
        else:
            duration_str = "running..."
    except (ValueError, AttributeError):
        duration_str = "unknown"

    # Header
    lines.append("")
    lines.append("=" * 70)
    lines.append(f"Trace: {entity_id} (run: {run_id})")
    lines.append(f"Time: {start_str} | Duration: {duration_str}")
    lines.append("=" * 70)

    # Get trace data
    trace_data = trace.get("trace", {})

    if not trace_data:
        lines.append("")
        lines.append("No trace data available.")
        lines.append("")
        return "\n".join(lines)

    lines.append("")

    # Process trace nodes in order
    # Trace structure: {"path/to/node": [step_data, ...], ...}
    # Sort by path to maintain execution order
    sorted_paths = sorted(trace_data.keys())

    for path in sorted_paths:
        steps = trace_data[path]
        for step in steps:
            node_lines = format_trace_node(step)
            lines.extend(node_lines)

    # Result summary
    lines.append("")
    lines.append("-" * 70)

    if state == "stopped":
        if script_execution == "finished":
            lines.append("✓ Result: SUCCESS")
        elif script_execution == "aborted":
            lines.append("✗ Result: ABORTED")
        elif script_execution == "error":
            lines.append("✗ Result: ERROR")
        else:
            lines.append(f"→ Result: {script_execution}")
    else:
        lines.append(f"⏳ State: {state}")

    # Variables section (verbose only)
    if verbose:
        context = trace.get("context", {})

        if context:
            lines.append("")
            lines.append("📊 Context:")
            lines.append(f"   ID: {context.get('id', 'unknown')}")
            if context.get("parent_id"):
                lines.append(f"   Parent: {context.get('parent_id')}")
            if context.get("user_id"):
                lines.append(f"   User: {context.get('user_id')}")

        # Show changed variables from trace nodes
        all_variables: dict[str, Any] = {}
        for _path, steps in trace_data.items():
            for step in steps:
                changed = step.get("changed_variables", {})
                if changed:
                    all_variables.update(changed)

        if all_variables:
            lines.append("")
            lines.append("📋 Variables Changed:")
            for var_name, var_value in all_variables.items():
                value_str = json.dumps(var_value) if isinstance(var_value, (dict, list)) else str(var_value)
                if len(value_str) > 60:
                    value_str = value_str[:57] + "..."
                lines.append(f"   {var_name}: {value_str}")
    else:
        lines.append("")
        lines.append("Variables: Use --verbose to see all values")

    lines.append("")

    return "\n".join(lines)


@click.command()
@click.argument("entity_id")
@click.option(
    "--run-id",
    "-r",
    help="Specific run_id to fetch (default: latest trace)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show all variable values at each step",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output raw JSON instead of formatted output",
)
def main(
    entity_id: str,
    run_id: str | None,
    verbose: bool,
    output_json: bool,
) -> None:
    """
    Fetch automation/script execution trace details.

    Shows smart formatted output by default (executed path only).
    Use --verbose for full variable values, --json for raw output.

    Examples:

        uv run get-trace.py automation.my_automation

        uv run get-trace.py automation.my_automation --run-id abc123

        uv run get-trace.py automation.my_automation --verbose

        uv run get-trace.py automation.my_automation --json
    """
    _validate_config()

    try:
        # Parse entity_id
        parts = entity_id.split(".", 1)
        if len(parts) != 2:
            raise Exception(f"Invalid entity_id format: {entity_id}. Expected: domain.item_id")

        domain = parts[0]
        item_id = parts[1]

        # Get run_id if not provided
        if not run_id:
            run_id = get_latest_run_id(domain, item_id)
            if not run_id:
                msg = f"No traces found for {entity_id}.\n\n"
                msg += "Tip: HA stores only 5 traces per automation by default.\n"
                msg += "Add 'trace: stored_traces: 20' to automation YAML for more history."
                raise Exception(msg)

        # Fetch trace
        data = {
            "domain": domain,
            "item_id": item_id,
            "run_id": run_id,
        }
        result = websocket_command("trace/get", data)

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            formatted = format_trace_smart(result, entity_id, verbose)
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
