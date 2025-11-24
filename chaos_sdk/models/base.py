"""Abstract base class for all Chaos Mesh experiments."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from pydantic import BaseModel, model_validator, field_validator

from chaos_sdk.models.selector import ChaosSelector
from chaos_sdk.models.enums import ChaosMode
from chaos_sdk.config import config
from chaos_sdk.utils import generate_unique_name

logger = logging.getLogger(__name__)


class BaseChaos(BaseModel, ABC):
    """
    Abstract base class for all chaos experiments.
    
    Implements Template Method pattern for CRD generation.
    """

    name: Optional[str] = None
    namespace: str = "default"
    selector: ChaosSelector
    mode: ChaosMode = ChaosMode.ONE
    value: Optional[str] = None
    duration: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
        use_enum_values = False

    @field_validator('duration')
    @classmethod
    def validate_duration_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v

        import re
        if not re.match(r'^\d+[smh]$', v):
            raise ValueError(f"Invalid duration: '{v}'. Use format like '30s', '5m', '2h'")
        return v

    @model_validator(mode='after')
    def validate_mode_value(self) -> "BaseChaos":
        modes_requiring_value = {
            ChaosMode.FIXED,
            ChaosMode.FIXED_PERCENT,
            ChaosMode.RANDOM_MAX_PERCENT,
        }

        if self.mode in modes_requiring_value and not self.value:
            raise ValueError(
                f"Mode '{self.mode.value}' requires 'value' parameter. "
                f"For example: value='2' for fixed count or value='50' for percentage."
            )

        percentage_modes = {ChaosMode.FIXED_PERCENT, ChaosMode.RANDOM_MAX_PERCENT}

        if self.mode in percentage_modes and self.value:
            try:
                percentage = float(self.value)
                if not 0 <= percentage <= 100:
                    raise ValueError(
                        f"Invalid value '{self.value}' for mode '{self.mode.value}'. "
                        f"Percentage must be between 0 and 100."
                    )
            except (ValueError, TypeError) as e:
                if "could not convert" in str(e) or "invalid literal" in str(e):
                    raise ValueError(
                        f"Invalid value '{self.value}' for mode '{self.mode.value}'. "
                        f"Expected a numeric percentage (0-100), e.g., '50' or '25.5'"
                    )
                raise

        if self.mode == ChaosMode.FIXED and self.value:
            try:
                count = int(self.value)
                if count <= 0:
                    raise ValueError(
                        f"Invalid value '{self.value}' for mode 'fixed'. "
                        f"Count must be a positive integer, e.g., '1', '2', '5'"
                    )
            except (ValueError, TypeError) as e:
                if "invalid literal" in str(e):
                    raise ValueError(
                        f"Invalid value '{self.value}' for mode 'fixed'. "
                        f"Expected a positive integer, e.g., '1', '2', '5'"
                    )
                raise

        return self

    @model_validator(mode='after')
    def generate_name_if_missing(self) -> "BaseChaos":
        if self.name is None:
            kind = self.__class__.__name__
            kind_lower = kind.lower()
            self.name = generate_unique_name(kind_lower)
            logger.debug(f"Auto-generated experiment name: {self.name}")

        return self

    @abstractmethod
    def _build_action_spec(self) -> Dict[str, Any]:
        """Build action-specific spec fields (subclasses must implement)."""
        pass

    def to_crd(self) -> Dict[str, Any]:
        """Build complete Chaos Mesh CRD definition."""
        kind = self.__class__.__name__

        spec = {
            "selector": self.selector.to_crd_dict(),
            "mode": self.mode.value,
        }

        if self.value is not None:
            spec["value"] = self.value

        if self.duration is not None:
            spec["duration"] = self.duration

        spec.update(self._build_action_spec())

        crd = {
            "apiVersion": f"{config.api_group}/{config.api_version}",
            "kind": kind,
            "metadata": {
                "name": self.name,
                "namespace": self.namespace,
            },
            "spec": spec,
        }

        logger.debug(f"Built CRD for {kind}/{self.name}")
        return crd

    def __str__(self) -> str:
        kind = self.__class__.__name__
        return f"{kind}(name={self.name}, selector={self.selector}, mode={self.mode.value})"
