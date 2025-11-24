"""Global configuration management for Chaos Mesh SDK."""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class ChaosConfig:
    """Global configuration for Chaos Mesh SDK (thread-safe singleton)."""

    _instance: Optional["ChaosConfig"] = None
    _initialized: bool = False
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        api_group: str = "chaos-mesh.org",
        api_version: str = "v1alpha1",
        retry_max_attempts: int = 3,
        retry_backoff_multiplier: float = 1.0,
        retry_min_wait: float = 1.0,
        retry_max_wait: float = 10.0,
        poll_interval: float = 2.0,
        wait_timeout: int = 60,
        kubeconfig_path: Optional[str] = None,
    ):
        if ChaosConfig._initialized:
            return

        self.api_group = api_group
        self.api_version = api_version
        self.retry_max_attempts = retry_max_attempts
        self.retry_backoff_multiplier = retry_backoff_multiplier
        self.retry_min_wait = retry_min_wait
        self.retry_max_wait = retry_max_wait
        self.poll_interval = poll_interval
        self.wait_timeout = wait_timeout
        self.kubeconfig_path = kubeconfig_path

        ChaosConfig._initialized = True

    @classmethod
    def get_instance(cls) -> "ChaosConfig":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None
        cls._initialized = False

    def update(self, **kwargs) -> None:
        """Update configuration values."""
        for key, value in kwargs.items():
            if hasattr(self, key) and not key.startswith('_'):
                setattr(self, key, value)
                logger.info("Updated config: %s=%s", key, value)
            else:
                logger.warning("Unknown config key: %s", key)

    def __repr__(self) -> str:
        return (
            f"ChaosConfig("
            f"api_group={self.api_group!r}, "
            f"api_version={self.api_version!r}, "
            f"retry_max_attempts={self.retry_max_attempts}, "
            f"poll_interval={self.poll_interval}, "
            f"wait_timeout={self.wait_timeout})"
        )


config = ChaosConfig.get_instance()