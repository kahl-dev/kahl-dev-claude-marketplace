#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "pyyaml>=6.0.1",
# ]
# ///

"""
Home Assistant Validate Config Script

Validates HA config by:
1. Parsing all YAML files locally for syntax errors
2. Pushing to staging directory on HA
3. Copying secrets.yaml from production for completeness

Note: Due to HA OS protection mode, full HA validation (check_config) runs
AFTER deployment via `ha core check`. This script catches YAML syntax errors
before deployment.

Usage:
    uv run validate-config.py
    uv run validate-config.py --local-path ~/ha-config
    uv run validate-config.py --json
    uv run validate-config.py --help
"""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

import click
import yaml


# Custom YAML loader that handles Home Assistant's !include and similar tags
class HAYAMLLoader(yaml.SafeLoader):
    """YAML loader with Home Assistant custom tags support"""

    pass


def _include_constructor(loader: yaml.Loader, node: yaml.Node) -> str:
    """Handle !include tag - return placeholder for syntax check"""
    return f"!include:{loader.construct_scalar(node)}"


def _secret_constructor(loader: yaml.Loader, node: yaml.Node) -> str:
    """Handle !secret tag - return placeholder for syntax check"""
    return f"!secret:{loader.construct_scalar(node)}"


def _env_var_constructor(loader: yaml.Loader, node: yaml.Node) -> str:
    """Handle !env_var tag - return placeholder for syntax check"""
    return f"!env_var:{loader.construct_scalar(node)}"


def _include_dir_constructor(loader: yaml.Loader, node: yaml.Node) -> list[str]:
    """Handle !include_dir_* tags - return placeholder for syntax check"""
    return [f"!include_dir:{loader.construct_scalar(node)}"]


# Register HA-specific YAML tags
HAYAMLLoader.add_constructor("!include", _include_constructor)
HAYAMLLoader.add_constructor("!include_dir_list", _include_dir_constructor)
HAYAMLLoader.add_constructor("!include_dir_named", _include_dir_constructor)
HAYAMLLoader.add_constructor("!include_dir_merge_list", _include_dir_constructor)
HAYAMLLoader.add_constructor("!include_dir_merge_named", _include_dir_constructor)
HAYAMLLoader.add_constructor("!secret", _secret_constructor)
HAYAMLLoader.add_constructor("!env_var", _env_var_constructor)


def get_required_env(name: str) -> str:
    """Get required environment variable or fail fast with clear error."""
    value = os.getenv(name)
    if not value:
        click.echo(f"❌ Error: {name} environment variable is required but not set.", err=True)
        click.echo(f'   Set it with: export {name}="<your-value>"', err=True)
        sys.exit(1)
    return value


# Configuration from environment
HA_STAGING_PATH = os.getenv("HA_STAGING_PATH", "/homeassistant/config_staging")
HA_CONFIG_PATH = os.getenv("HA_CONFIG_PATH", "/homeassistant")
DEFAULT_LOCAL_PATH = os.path.expanduser(os.getenv("HA_LOCAL_CONFIG", "~/ha-config"))


def validate_yaml_file(filepath: Path) -> dict[str, Any]:
    """Validate a single YAML file for syntax errors"""
    result: dict[str, Any] = {
        "file": str(filepath.name),
        "path": str(filepath),
        "valid": False,
        "error": None,
    }

    try:
        with open(filepath) as file:
            yaml.load(file, Loader=HAYAMLLoader)
        result["valid"] = True
    except yaml.YAMLError as error:
        result["error"] = str(error)
    except Exception as error:
        result["error"] = f"Read error: {error}"

    return result


def validate_all_yaml_files(local_path: Path) -> list[dict[str, Any]]:
    """Validate all YAML files in the config directory"""
    results: list[dict[str, Any]] = []

    yaml_files = list(local_path.glob("*.yaml")) + list(local_path.glob("*.yml"))

    for filepath in sorted(yaml_files):
        if filepath.name == "secrets.yaml":
            continue
        results.append(validate_yaml_file(filepath))

    return results


def rsync_to_staging(local_path: Path, ssh_host: str) -> dict[str, Any]:
    """Rsync local config to staging directory on HA"""
    result: dict[str, Any] = {
        "success": False,
        "files_transferred": 0,
        "error": None,
    }

    rsync_command = [
        "rsync",
        "-av",
        "--delete",
        "--exclude=.git/",
        "--exclude=.gitignore",
        "--exclude=secrets.yaml",
        "--exclude=.storage/",
        "--exclude=backups/",
        "--exclude=*.db",
        "--exclude=*.log",
        "--exclude=*.log.*",
        "--exclude=home-assistant.log*",
        "--exclude=tts/",
        "--exclude=deps/",
        "--exclude=__pycache__/",
        f"{local_path}/",
        f"{ssh_host}:{HA_STAGING_PATH}/",
    ]

    try:
        process = subprocess.run(
            rsync_command,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if process.returncode == 0:
            result["success"] = True
            lines = process.stdout.strip().split("\n")
            file_lines = [
                line
                for line in lines
                if not line.startswith("sending") and not line.startswith("sent") and not line.startswith("total")
            ]
            result["files_transferred"] = len([line for line in file_lines if line.strip() and not line.endswith("/")])
            result["output"] = process.stdout
        else:
            result["error"] = process.stderr or f"rsync failed with exit code {process.returncode}"

    except subprocess.TimeoutExpired:
        result["error"] = "rsync timed out after 120 seconds"
    except Exception as error:
        result["error"] = str(error)

    return result


def copy_secrets_to_staging(ssh_host: str) -> dict[str, Any]:
    """Copy secrets.yaml from production to staging for validation completeness"""
    result: dict[str, Any] = {
        "success": False,
        "error": None,
    }

    src = shlex.quote(f"{HA_CONFIG_PATH}/secrets.yaml")
    dst = shlex.quote(f"{HA_STAGING_PATH}/secrets.yaml")

    ssh_command = [
        "ssh",
        ssh_host,
        f"cp {src} {dst} 2>/dev/null || echo 'No secrets.yaml found (OK if not using secrets)'",
    ]

    try:
        process = subprocess.run(
            ssh_command,
            capture_output=True,
            text=True,
            timeout=30,
        )

        result["success"] = process.returncode == 0
        if not result["success"]:
            result["error"] = process.stderr or "Failed to copy secrets.yaml"
        elif "No secrets.yaml found" in process.stdout:
            result["note"] = "secrets.yaml not found in production (OK if not using secrets)"

    except subprocess.TimeoutExpired:
        result["error"] = "SSH command timed out"
    except Exception as error:
        result["error"] = str(error)

    return result


def format_validation_result(
    yaml_results: list[dict[str, Any]],
    rsync_result: dict[str, Any],
    secrets_result: dict[str, Any],
    ssh_host: str,
) -> str:
    """Format validation results for human-readable output"""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 80)
    lines.append("🔍 Home Assistant Config Validation")
    lines.append("=" * 80)
    lines.append("")

    # YAML validation results
    lines.append("📄 YAML Syntax Check")
    lines.append("-" * 40)

    errors_found = False
    for result in yaml_results:
        emoji = "✅" if result["valid"] else "❌"
        lines.append(f"  {emoji} {result['file']}")
        if not result["valid"]:
            errors_found = True
            lines.append(f"      Error: {result['error']}")

    lines.append("")

    # Rsync result
    lines.append("📤 Push to Staging")
    lines.append("-" * 40)
    if rsync_result.get("skipped"):
        lines.append("  ⏭️  Skipped (--skip-push)")
    elif rsync_result.get("success"):
        lines.append(f"  ✅ Synced to {ssh_host}:{HA_STAGING_PATH}")
        if "files_transferred" in rsync_result:
            lines.append(f"     Files transferred: {rsync_result['files_transferred']}")
    else:
        lines.append(f"  ❌ Sync failed: {rsync_result.get('error', 'Unknown error')}")
        errors_found = True

    lines.append("")

    # Secrets copy result
    lines.append("🔐 Secrets Copy")
    lines.append("-" * 40)
    if secrets_result.get("skipped"):
        lines.append("  ⏭️  Skipped (--skip-push)")
    elif secrets_result.get("success"):
        if secrets_result.get("note"):
            lines.append(f"  ℹ️  {secrets_result['note']}")
        else:
            lines.append("  ✅ secrets.yaml copied to staging")
    else:
        lines.append(f"  ⚠️  {secrets_result.get('error', 'Unknown error')}")

    lines.append("")
    lines.append("-" * 80)

    # Overall result
    if errors_found:
        lines.append("❌ VALIDATION FAILED - Fix errors before deploying")
    else:
        lines.append("✅ VALIDATION PASSED - Config ready for deployment")
        lines.append("")
        lines.append("ℹ️  Note: Full HA validation (ha core check) runs after deployment")

    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--local-path",
    "-p",
    default=DEFAULT_LOCAL_PATH,
    help=f"Path to local HA config directory (default: {DEFAULT_LOCAL_PATH})",
)
@click.option(
    "--skip-push",
    is_flag=True,
    help="Only validate YAML syntax, don't push to staging",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(
    local_path: str,
    skip_push: bool,
    output_json: bool,
) -> None:
    """
    Validate Home Assistant configuration.

    Checks YAML syntax and pushes to staging directory on HA.
    Due to HA OS protection mode, full check_config runs after deployment.

    Examples:

        uv run validate-config.py

        uv run validate-config.py --local-path ~/my-ha-config

        uv run validate-config.py --skip-push

        uv run validate-config.py --json
    """
    # Fail fast if HA_SSH_HOST not set (unless skipping push)
    ssh_host = ""
    if not skip_push:
        ssh_host = get_required_env("HA_SSH_HOST")

    try:
        config_path = Path(local_path).expanduser()

        if not config_path.exists():
            raise click.UsageError(f"Config path does not exist: {config_path}")

        # Step 1: Validate YAML syntax locally
        yaml_results = validate_all_yaml_files(config_path)

        # Check for YAML errors
        yaml_errors = [r for r in yaml_results if not r["valid"]]

        rsync_result: dict[str, Any] = {"success": True, "skipped": True}
        secrets_result: dict[str, Any] = {"success": True, "skipped": True}

        # Step 2: Push to staging (if no YAML errors and not skipped)
        if not yaml_errors and not skip_push:
            rsync_result = rsync_to_staging(config_path, ssh_host)

            # Step 3: Copy secrets to staging
            if rsync_result["success"]:
                secrets_result = copy_secrets_to_staging(ssh_host)

        # Determine overall success
        overall_valid = len(yaml_errors) == 0 and (skip_push or rsync_result["success"])

        if output_json:
            result = {
                "valid": overall_valid,
                "yaml_validation": yaml_results,
                "rsync": rsync_result if not skip_push else {"skipped": True},
                "secrets": secrets_result if not skip_push else {"skipped": True},
                "errors": [r["error"] for r in yaml_results if not r["valid"]],
                "warnings": [],
            }
            click.echo(json.dumps(result, indent=2))
        else:
            formatted = format_validation_result(
                yaml_results,
                rsync_result,
                secrets_result,
                ssh_host,
            )
            click.echo(formatted)

        sys.exit(0 if overall_valid else 1)

    except click.UsageError:
        raise
    except Exception as error:
        error_data = {"valid": False, "error": str(error)}
        if output_json:
            click.echo(json.dumps(error_data, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
