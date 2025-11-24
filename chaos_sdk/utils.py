"""Utility functions for Chaos Mesh SDK."""

import logging
import time
import re
import secrets
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from chaos_sdk.client import ChaosClient

from chaos_sdk.models.enums import CHAOS_KINDS

logger = logging.getLogger(__name__)


def generate_unique_name(prefix: str = "chaos") -> str:
    """Generate a unique experiment name: {prefix}-{timestamp}-{suffix}."""
    timestamp = int(time.time())
    suffix = secrets.token_hex(2)
    return f"{prefix}-{timestamp}-{suffix}"


def parse_duration(duration: str) -> int:
    """Parse duration string (30s, 5m, 2h) to seconds."""
    pattern = r'^(\d+)(s|m|h)$'
    match = re.match(pattern, duration)

    if not match:
        raise ValueError(
            f"Invalid duration format: {duration}. "
            "Expected format: <number><unit> where unit is s/m/h"
        )

    value, unit = match.groups()
    value = int(value)

    multipliers = {'s': 1, 'm': 60, 'h': 3600}
    return value * multipliers[unit]


def validate_network_param_format(param: str, param_name: str = "parameter") -> str:
    """Validate network parameter format (e.g., 100ms, 1s, 5m)."""
    pattern = r'^\d+(?:ns|us|ms|s|m)$'

    if not re.match(pattern, param):
        raise ValueError(
            f"Invalid {param_name} format: {param}. "
            "Expected format: <number><unit> where unit is ns/us/ms/s/m. "
            "Examples: '100us', '5ms', '1s', '5m'"
        )

    return param


def validate_percentage(value: str, param_name: str = "parameter") -> str:
    """Validate percentage parameter (0-100)."""
    try:
        percentage = float(value)
        if not 0 <= percentage <= 100:
            raise ValueError(
                f"Invalid {param_name}: {value}. Must be between 0 and 100."
            )
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid {param_name}: {value}. Must be a number between 0 and 100."
        )

    return value


def cleanup_orphaned_experiments(
        client: "ChaosClient",
        namespace: str = "default",
        label_selector: Optional[str] = None,
        dry_run: bool = False
) -> int:
    """Find and delete orphaned chaos experiments."""
    cleaned_count = 0

    for kind in CHAOS_KINDS:
        try:
            experiments = client.list_chaos_resources(
                kind=kind,
                namespace=namespace,
                label_selector=label_selector or ""
            )

            for exp in experiments:
                name = exp.get("metadata", {}).get("name")
                if not name:
                    continue

                if dry_run:
                    logger.info("[DRY-RUN] Would delete %s/%s", kind, name)
                else:
                    logger.info("Deleting orphaned experiment: %s/%s", kind, name)
                    client.delete_chaos_resource(kind, namespace, name)

                cleaned_count += 1

        except Exception as e:
            logger.warning("Error cleaning %s experiments: %s", kind, e)

    return cleaned_count