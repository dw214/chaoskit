"""Enumerations for Chaos Mesh SDK."""

from enum import Enum


class ChaosMode(str, Enum):
    """Chaos experiment target selection mode."""
    ONE = "one"
    ALL = "all"
    FIXED = "fixed"
    FIXED_PERCENT = "fixed-percent"
    RANDOM_MAX_PERCENT = "random-max-percent"


class PodChaosAction(str, Enum):
    """Pod-level chaos experiment actions."""
    POD_FAILURE = "pod-failure"
    POD_KILL = "pod-kill"
    CONTAINER_KILL = "container-kill"


class NetworkChaosAction(str, Enum):
    """Network-level chaos experiment actions."""
    DELAY = "delay"
    LOSS = "loss"
    DUPLICATE = "duplicate"
    CORRUPT = "corrupt"
    PARTITION = "partition"
    BANDWIDTH = "bandwidth"
    REORDER = "reorder"


class NetworkDirection(str, Enum):
    """Network traffic direction."""
    TO = "to"
    FROM = "from"
    BOTH = "both"


CHAOS_KINDS = [
    "PodChaos",
    "NetworkChaos",
    "IOChaos",
    "StressChaos",
    "TimeChaos",
    "KernelChaos",
    "DNSChaos",
    "HTTPChaos",
    "JVMChaos",
    "AWSChaos",
    "GCPChaos",
]