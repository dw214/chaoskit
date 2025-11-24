"""Chaos Experiment Manager."""

import logging
import time
from typing import Optional, Dict, Any

from chaos_sdk.client import ChaosClient
from chaos_sdk.config import config
from chaos_sdk.models.base import BaseChaos
from chaos_sdk.exceptions import (
    ExperimentTimeoutError,
    ChaosResourceNotFoundError,
)

logger = logging.getLogger(__name__)


class ChaosManager:
    """Manager for Chaos Mesh experiment lifecycle."""

    def __init__(self, client: Optional[ChaosClient] = None):
        self.client = client or ChaosClient()

    def apply(self, experiment: BaseChaos) -> None:
        """Apply a chaos experiment to the cluster."""
        kind = experiment.__class__.__name__
        crd = experiment.to_crd()

        self.client.create_chaos_resource(
            kind=kind,
            namespace=experiment.namespace,
            body=crd
        )

        logger.info("Applied %s/%s targeting %s", kind, experiment.name, experiment.selector)

    def delete(self, experiment: BaseChaos) -> None:
        """Delete a chaos experiment from the cluster."""
        kind = experiment.__class__.__name__

        self.client.delete_chaos_resource(
            kind=kind,
            namespace=experiment.namespace,
            name=experiment.name
        )

        logger.info("Deleted %s/%s", kind, experiment.name)

    def get_status(self, experiment: BaseChaos) -> Dict[str, Any]:
        """Get current status of a chaos experiment."""
        kind = experiment.__class__.__name__

        resource = self.client.get_chaos_resource(
            kind=kind,
            namespace=experiment.namespace,
            name=experiment.name
        )

        return resource.get("status", {})

    def wait_for_injection(
            self,
            experiment: BaseChaos,
            timeout: Optional[int] = None,
            poll_interval: Optional[float] = None
    ) -> bool:
        """Wait for chaos injection to complete."""
        timeout = timeout or config.wait_timeout
        poll_interval = poll_interval or config.poll_interval

        kind = experiment.__class__.__name__
        start_time = time.time()

        logger.info("Waiting for %s/%s injection (timeout: %ds)", kind, experiment.name, timeout)

        while time.time() - start_time < timeout:
            try:
                status = self.get_status(experiment)
                conditions = status.get("conditions", [])
                
                for condition in conditions:
                    cond_type = condition.get("type")
                    cond_status = condition.get("status")
                    
                    if cond_type == "AllInjected" and cond_status == "True":
                        elapsed = time.time() - start_time
                        logger.info("Chaos %s injected successfully after %.1fs", experiment.name, elapsed)
                        return True

                    if cond_status == "True" and cond_type in {"Failed", "Timeout", "Finished"}:
                        message = condition.get("message") or "Experiment reported failure"
                        raise ExperimentTimeoutError(
                            f"Chaos {experiment.name} reported {cond_type}: {message}"
                        )

                logger.debug("Chaos %s not yet injected, waiting...", experiment.name)

            except ChaosResourceNotFoundError:
                logger.warning("Chaos %s not found yet, retrying...", experiment.name)

            time.sleep(poll_interval)

        elapsed = time.time() - start_time
        raise ExperimentTimeoutError(
            "Chaos %s injection timeout after %.1fs" % (experiment.name, elapsed)
        )

    def wait_for_deletion(
            self,
            experiment: BaseChaos,
            timeout: int = 30,
            poll_interval: float = 1.0
    ) -> bool:
        """Wait for chaos experiment to be fully deleted."""
        kind = experiment.__class__.__name__
        start_time = time.time()

        logger.debug("Waiting for %s/%s deletion", kind, experiment.name)

        while time.time() - start_time < timeout:
            try:
                self.get_status(experiment)
                time.sleep(poll_interval)
            except ChaosResourceNotFoundError:
                elapsed = time.time() - start_time
                logger.info("Chaos %s deleted successfully after %.1fs", experiment.name, elapsed)
                return True

        raise ExperimentTimeoutError(
            "Chaos %s deletion timeout after %ds" % (experiment.name, timeout)
        )