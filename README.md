# Chaos Kit Python SDK

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Chaos Mesh](https://img.shields.io/badge/chaos--mesh-2.0+-green.svg)](https://chaos-mesh.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

A Python SDK for [Chaos Mesh](https://chaos-mesh.org/) with type safety, auto-cleanup, and pytest integration.

## Features

- **Type-Safe**: Pydantic models with comprehensive validation
- **Auto-Cleanup**: Context manager ensures no orphaned experiments
- **Synchronous Wait**: Bridge Kubernetes async with test scripts
- **Smart Retry**: Exponential backoff for transient failures

## Requirements

- Python 3.8+
- Kubernetes cluster with [Chaos Mesh](https://chaos-mesh.org/docs/quick-start/) installed
- Valid kubeconfig or in-cluster credentials

## Installation

```bash
pip install chaoskit
```

## Quick Start

```python
from chaos_sdk import ChaosController, PodChaos, ChaosSelector

selector = ChaosSelector.from_labels(
    labels={"app": "web-server"},
    namespaces=["default"]
)

chaos = PodChaos.pod_kill(selector=selector)

with ChaosController() as controller:
    controller.inject(chaos, wait=True)
    # Your test logic here
    # Auto cleanup on exit
```

## Core Concepts

### Selectors

Target pods by labels or specific names:

```python
# Label-based
selector = ChaosSelector.from_labels(
    labels={"app": "web", "tier": "frontend"},
    namespaces=["default"]
)

# Pod-specific
selector = ChaosSelector.from_pods(
    namespace="default",
    pod_names=["nginx-7d8b6", "nginx-9f3a2"]
)
```

### Chaos Modes

```python
from chaos_sdk import ChaosMode

PodChaos(..., mode=ChaosMode.ONE)           # One random target
PodChaos(..., mode=ChaosMode.ALL)           # All targets
PodChaos(..., mode=ChaosMode.FIXED, value="3")         # Exact count
PodChaos(..., mode=ChaosMode.FIXED_PERCENT, value="50") # Percentage
```

## PodChaos

```python
from chaos_sdk import PodChaos, ChaosSelector

selector = ChaosSelector.from_labels({"app": "web"})

# Kill pods
PodChaos.pod_kill(selector=selector, grace_period=10)

# Make pods unavailable
PodChaos.pod_failure(selector=selector, duration="5m")

# Kill specific containers
PodChaos.container_kill(selector=selector, container_names=["sidecar"])
```

## NetworkChaos

```python
from chaos_sdk import NetworkChaos, ChaosSelector, NetworkDirection

selector = ChaosSelector.from_labels({"app": "api"})

# Add latency
NetworkChaos.create_delay(
    selector=selector,
    latency="100ms",
    jitter="10ms",
    duration="30s"
)

# Packet loss
NetworkChaos.create_loss(
    selector=selector,
    loss="20",  # 20%
    correlation="50"
)

# Network partition
NetworkChaos.create_partition(
    selector=ChaosSelector.from_labels({"tier": "frontend"}),
    target=ChaosSelector.from_labels({"tier": "backend"}),
    direction=NetworkDirection.TO
)

# Bandwidth limit
NetworkChaos.create_bandwidth(
    selector=selector,
    rate="1mbps",
    limit="1000",
    buffer="10000"
)
```

## Pytest Integration

```python
import pytest
from chaos_sdk import ChaosController, PodChaos, ChaosSelector

@pytest.fixture
def chaos_controller():
    with ChaosController() as controller:
        yield controller

def test_pod_resilience(chaos_controller):
    chaos = PodChaos.pod_kill(
        selector=ChaosSelector.from_labels({"app": "web"})
    )
    chaos_controller.inject(chaos, wait=True)
    assert check_service_healthy()
```

## Configuration

```python
from chaos_sdk import ChaosConfig

config = ChaosConfig.get_instance()
config.update(
    retry_max_attempts=5,
    poll_interval=3.0,
    wait_timeout=120
)
```

## Error Handling

```python
from chaos_sdk.exceptions import (
    ChaosMeshSDKError,           # Base exception
    ChaosMeshConnectionError,    # K8s API unreachable
    ExperimentAlreadyExistsError,
    ChaosResourceNotFoundError,
    ExperimentTimeoutError,
)

try:
    controller.inject(chaos)
except ExperimentAlreadyExistsError:
    print("Experiment already exists")
except ChaosMeshConnectionError:
    print("Cannot connect to Kubernetes")
```

## Examples

See [`examples/`](examples/) for complete examples:

```bash
python examples/pod_kill_example.py
python examples/network_delay_example.py
pytest examples/pytest_integration.py -v
```

## License

Apache-2.0 - See [LICENSE](LICENSE)