"""PodChaos experiment implementation."""

import logging
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from pydantic import Field, model_validator

from chaos_sdk.models.base import BaseChaos
from chaos_sdk.models.enums import PodChaosAction

if TYPE_CHECKING:
    from chaos_sdk.models.selector import ChaosSelector

logger = logging.getLogger(__name__)


class PodChaos(BaseChaos):
    """Pod-level chaos experiment (pod-failure, pod-kill, container-kill)."""

    action: PodChaosAction = Field(...)
    container_names: Optional[List[str]] = Field(default=None)
    grace_period: Optional[int] = Field(default=None, ge=0)
    scheduler: Optional[Dict[str, Any]] = Field(default=None)
    remote_cluster: Optional[str] = Field(default=None)

    @model_validator(mode='after')
    def validate_container_kill(self) -> "PodChaos":
        if self.action == PodChaosAction.CONTAINER_KILL and not self.container_names:
            raise ValueError(
                "container-kill requires container_names, e.g.: "
                "container_names=['nginx', 'sidecar']"
            )
        return self

    def _build_action_spec(self) -> Dict[str, Any]:
        spec = {"action": self.action.value}

        if self.container_names:
            spec["containerNames"] = self.container_names

        if self.grace_period is not None:
            spec["gracePeriod"] = self.grace_period

        if self.scheduler is not None:
            spec["scheduler"] = self.scheduler

        if self.remote_cluster is not None:
            spec["remoteCluster"] = self.remote_cluster

        return spec

    @classmethod
    def pod_failure(
            cls,
            selector: "ChaosSelector",
            duration: str = "30s",
            **kwargs
    ) -> "PodChaos":
        """Create pod-failure chaos."""
        return cls(
            action=PodChaosAction.POD_FAILURE,
            selector=selector,
            duration=duration,
            **kwargs
        )

    @classmethod
    def pod_kill(
            cls,
            selector: "ChaosSelector",
            grace_period: Optional[int] = None,
            **kwargs
    ) -> "PodChaos":
        """Create pod-kill chaos."""
        return cls(
            action=PodChaosAction.POD_KILL,
            selector=selector,
            grace_period=grace_period,
            **kwargs
        )

    @classmethod
    def container_kill(
            cls,
            selector: "ChaosSelector",
            container_names: List[str],
            grace_period: Optional[int] = None,
            **kwargs
    ) -> "PodChaos":
        """Create container-kill chaos."""
        return cls(
            action=PodChaosAction.CONTAINER_KILL,
            selector=selector,
            container_names=container_names,
            grace_period=grace_period,
            **kwargs
        )