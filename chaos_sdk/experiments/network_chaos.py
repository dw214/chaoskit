"""NetworkChaos experiment implementation."""

import logging
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator, model_validator

from chaos_sdk.models.base import BaseChaos
from chaos_sdk.models.selector import ChaosSelector
from chaos_sdk.models.enums import NetworkChaosAction, NetworkDirection
from chaos_sdk.utils import validate_network_param_format, validate_percentage

logger = logging.getLogger(__name__)


class NetworkDelayParams(BaseModel):
    """Parameters for network delay chaos."""
    latency: str = Field(...)
    jitter: str = Field(default="0ms")
    correlation: str = Field(default="0")
    reorder: Optional[Dict[str, str]] = Field(default=None)

    @field_validator('latency', 'jitter')
    @classmethod
    def validate_duration_format(cls, value: str) -> str:
        return validate_network_param_format(value, "latency/jitter")

    @field_validator('correlation')
    @classmethod
    def validate_correlation(cls, value: str) -> str:
        return validate_percentage(value, "correlation")


class NetworkLossParams(BaseModel):
    """Parameters for network packet loss chaos."""
    loss: str = Field(...)
    correlation: str = Field(default="0")

    @field_validator('loss', 'correlation')
    @classmethod
    def validate_percentage_field(cls, value: str) -> str:
        return validate_percentage(value, "percentage")


class NetworkDuplicateParams(BaseModel):
    """Parameters for network packet duplication chaos."""
    duplicate: str = Field(...)
    correlation: str = Field(default="0")

    @field_validator('duplicate', 'correlation')
    @classmethod
    def validate_percentage_field(cls, value: str) -> str:
        return validate_percentage(value, "percentage")


class NetworkCorruptParams(BaseModel):
    """Parameters for network packet corruption chaos."""
    corrupt: str = Field(...)
    correlation: str = Field(default="0")

    @field_validator('corrupt', 'correlation')
    @classmethod
    def validate_percentage_field(cls, value: str) -> str:
        return validate_percentage(value, "percentage")


class NetworkPartitionParams(BaseModel):
    """Parameters for network partition chaos."""
    direction: NetworkDirection = Field(...)
    target: ChaosSelector = Field(...)


class NetworkBandwidthParams(BaseModel):
    """Parameters for network bandwidth limitation chaos."""
    rate: str = Field(...)
    limit: str = Field(...)
    buffer: str = Field(...)
    peakrate: Optional[str] = Field(default=None)
    minburst: Optional[str] = Field(default=None)


class NetworkReorderParams(BaseModel):
    """Parameters for network packet reordering chaos."""
    reorder: str = Field(...)
    correlation: str = Field(default="0")
    gap: str = Field(...)

    @field_validator('reorder', 'correlation')
    @classmethod
    def validate_percentage_field(cls, value: str) -> str:
        return validate_percentage(value, "percentage")


class NetworkChaos(BaseChaos):
    """Network-level chaos experiment."""

    action: NetworkChaosAction = Field(...)

    delay: Optional[NetworkDelayParams] = None
    loss: Optional[NetworkLossParams] = None
    duplicate: Optional[NetworkDuplicateParams] = None
    corrupt: Optional[NetworkCorruptParams] = None
    partition: Optional[NetworkPartitionParams] = None
    bandwidth: Optional[NetworkBandwidthParams] = None
    reorder: Optional[NetworkReorderParams] = None

    direction: Optional[NetworkDirection] = Field(default=None)
    device: Optional[str] = Field(default=None)
    external_targets: Optional[list] = Field(default=None)
    tc_parameter: Optional[Dict[str, Any]] = Field(default=None)

    @model_validator(mode='after')
    def validate_action_params(self) -> "NetworkChaos":
        param_map = {
            NetworkChaosAction.DELAY: self.delay,
            NetworkChaosAction.LOSS: self.loss,
            NetworkChaosAction.DUPLICATE: self.duplicate,
            NetworkChaosAction.CORRUPT: self.corrupt,
            NetworkChaosAction.PARTITION: self.partition,
            NetworkChaosAction.BANDWIDTH: self.bandwidth,
            NetworkChaosAction.REORDER: self.reorder,
        }

        if param_map.get(self.action) is None:
            raise ValueError(
                f"Action '{self.action.value}' requires corresponding parameters. "
                f"For example, for delay action, provide: delay=NetworkDelayParams(latency='100ms')"
            )

        return self

    def _build_action_spec(self) -> Dict[str, Any]:
        spec = {"action": self.action.value}

        if self.action == NetworkChaosAction.DELAY and self.delay:
            spec["delay"] = self.delay.model_dump(exclude_none=True)
        elif self.action == NetworkChaosAction.LOSS and self.loss:
            spec["loss"] = self.loss.model_dump(exclude_none=True)
        elif self.action == NetworkChaosAction.DUPLICATE and self.duplicate:
            spec["duplicate"] = self.duplicate.model_dump(exclude_none=True)
        elif self.action == NetworkChaosAction.CORRUPT and self.corrupt:
            spec["corrupt"] = self.corrupt.model_dump(exclude_none=True)
        elif self.action == NetworkChaosAction.PARTITION and self.partition:
            spec["direction"] = self.partition.direction.value
            spec["target"] = self.partition.target.to_crd_dict()
        elif self.action == NetworkChaosAction.BANDWIDTH and self.bandwidth:
            spec["bandwidth"] = self.bandwidth.model_dump(exclude_none=True)
        elif self.action == NetworkChaosAction.REORDER and self.reorder:
            spec["reorder"] = self.reorder.model_dump(exclude_none=True)

        if self.direction is not None and self.action != NetworkChaosAction.PARTITION:
            spec["direction"] = self.direction.value

        if self.device is not None:
            spec["device"] = self.device

        if self.external_targets is not None:
            spec["externalTargets"] = self.external_targets

        if self.tc_parameter is not None:
            spec["tcParameter"] = self.tc_parameter

        return spec

    @classmethod
    def create_delay(
            cls,
            selector: ChaosSelector,
            latency: str = "100ms",
            jitter: str = "10ms",
            correlation: str = "0",
            **kwargs
    ) -> "NetworkChaos":
        """Create network delay chaos."""
        return cls(
            action=NetworkChaosAction.DELAY,
            selector=selector,
            delay=NetworkDelayParams(latency=latency, jitter=jitter, correlation=correlation),
            **kwargs
        )

    @classmethod
    def create_loss(
            cls,
            selector: ChaosSelector,
            loss: str = "20",
            correlation: str = "0",
            **kwargs
    ) -> "NetworkChaos":
        """Create network packet loss chaos."""
        return cls(
            action=NetworkChaosAction.LOSS,
            selector=selector,
            loss=NetworkLossParams(loss=loss, correlation=correlation),
            **kwargs
        )

    @classmethod
    def create_partition(
            cls,
            selector: ChaosSelector,
            target: ChaosSelector,
            direction: NetworkDirection = NetworkDirection.TO,
            **kwargs
    ) -> "NetworkChaos":
        """Create network partition chaos."""
        return cls(
            action=NetworkChaosAction.PARTITION,
            selector=selector,
            partition=NetworkPartitionParams(direction=direction, target=target),
            **kwargs
        )

    @classmethod
    def create_bandwidth(
            cls,
            selector: ChaosSelector,
            rate: str = "1mbps",
            limit: str = "1000",
            buffer: str = "10000",
            **kwargs
    ) -> "NetworkChaos":
        """Create network bandwidth limitation chaos."""
        return cls(
            action=NetworkChaosAction.BANDWIDTH,
            selector=selector,
            bandwidth=NetworkBandwidthParams(rate=rate, limit=limit, buffer=buffer),
            **kwargs
        )
