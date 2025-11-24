"""Chaos experiment selector model."""

import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, model_validator

from chaos_sdk.exceptions import AmbiguousSelectorError

logger = logging.getLogger(__name__)


class ChaosSelector(BaseModel):
    """
    Unified selector for chaos experiment targets.
    
    Supports label-based OR pod-specific selection (mutually exclusive).
    """

    namespaces: List[str] = Field(default_factory=list)
    label_selectors: Dict[str, str] = Field(default_factory=dict)
    pods: Dict[str, List[str]] = Field(default_factory=dict)
    field_selectors: Dict[str, str] = Field(default_factory=dict)
    annotation_selectors: Dict[str, str] = Field(default_factory=dict)
    node_selectors: Dict[str, str] = Field(default_factory=dict)
    pod_phase_selectors: List[str] = Field(default_factory=list)
    expression_selectors: List[Dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_mutual_exclusivity(self) -> "ChaosSelector":
        if self.label_selectors and self.pods:
            raise AmbiguousSelectorError(
                "Cannot use both 'label_selectors' and 'pods' simultaneously. "
                "Use either label_selectors OR pods for selection."
            )

        if not (
            self.label_selectors
            or self.pods
            or self.field_selectors
            or self.annotation_selectors
            or self.node_selectors
            or self.pod_phase_selectors
            or self.expression_selectors
        ):
            raise AmbiguousSelectorError(
                "At least one selection method must be specified: "
                "label_selectors, pods, field_selectors, annotation_selectors, "
                "node_selectors, pod_phase_selectors, or expression_selectors"
            )

        return self

    @classmethod
    def from_labels(
            cls,
            labels: Dict[str, str],
            namespaces: Optional[List[str]] = None
    ) -> "ChaosSelector":
        """Create selector from labels."""
        return cls(namespaces=namespaces or [], label_selectors=labels)

    @classmethod
    def from_pods(
            cls,
            namespace: str,
            pod_names: List[str]
    ) -> "ChaosSelector":
        """Create selector from specific pod names."""
        return cls(namespaces=[namespace], pods={namespace: pod_names})

    def to_crd_dict(self) -> Dict:
        """Convert selector to Chaos Mesh CRD format."""
        selector_dict = {}

        if self.namespaces:
            selector_dict["namespaces"] = self.namespaces

        if self.label_selectors:
            selector_dict["labelSelectors"] = self.label_selectors

        if self.pods:
            selector_dict["pods"] = self.pods

        if self.field_selectors:
            selector_dict["fieldSelectors"] = self.field_selectors

        if self.annotation_selectors:
            selector_dict["annotationSelectors"] = self.annotation_selectors

        if self.node_selectors:
            selector_dict["nodeSelectors"] = self.node_selectors

        if self.pod_phase_selectors:
            selector_dict["podPhaseSelectors"] = self.pod_phase_selectors

        if self.expression_selectors:
            selector_dict["expressionSelectors"] = self.expression_selectors

        return selector_dict

    def __str__(self) -> str:
        if self.pods:
            pods_str = ", ".join(
                f"{ns}/{','.join(names)}" for ns, names in self.pods.items()
            )
            return f"Pods: {pods_str}"
        elif self.label_selectors:
            labels_str = ", ".join(
                f"{k}={v}" for k, v in self.label_selectors.items()
            )
            ns_str = f" in {', '.join(self.namespaces)}" if self.namespaces else ""
            return f"Labels: {labels_str}{ns_str}"
        else:
            return "Custom selector"