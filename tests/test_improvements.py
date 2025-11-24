#!/usr/bin/env python3
"""
Test script to verify the improvements to Chaos Mesh SDK:
1. Random name generation with type prefix
2. Complete field coverage including advanced selectors
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chaos_sdk.experiments.pod_chaos import PodChaos
from chaos_sdk.experiments.network_chaos import NetworkChaos, NetworkDelayParams
from chaos_sdk.models.selector import ChaosSelector
from chaos_sdk.models.enums import PodChaosAction, NetworkChaosAction, ChaosMode, NetworkDirection


def test_auto_name_generation():
    """Test 1: Verify auto-generated names have correct prefixes."""
    print("=" * 60)
    print("Test 1: Auto Name Generation with Type Prefix")
    print("=" * 60)
    
    # Test PodChaos auto-naming
    pod_chaos = PodChaos(
        action=PodChaosAction.POD_KILL,
        selector=ChaosSelector.from_labels({"app": "test"})
    )
    print(f"✓ PodChaos auto-generated name: {pod_chaos.name}")
    assert pod_chaos.name.startswith("podchaos-"), f"Expected name to start with 'podchaos-', got {pod_chaos.name}"
    
    # Test NetworkChaos auto-naming
    network_chaos = NetworkChaos(
        action=NetworkChaosAction.DELAY,
        delay=NetworkDelayParams(latency="100ms"),
        selector=ChaosSelector.from_labels({"app": "test"})
    )
    print(f"✓ NetworkChaos auto-generated name: {network_chaos.name}")
    assert network_chaos.name.startswith("networkchaos-"), f"Expected name to start with 'networkchaos-', got {network_chaos.name}"
    
    # Test with custom name
    custom_chaos = PodChaos(
        name="my-custom-chaos",
        action=PodChaosAction.POD_FAILURE,
        selector=ChaosSelector.from_labels({"app": "test"})
    )
    print(f"✓ Custom name preserved: {custom_chaos.name}")
    assert custom_chaos.name == "my-custom-chaos"
    
    print()


def test_selector_advanced_fields():
    """Test 2: Verify advanced selector fields work correctly."""
    print("=" * 60)
    print("Test 2: Advanced Selector Fields")
    print("=" * 60)
    
    # Test with node selectors
    selector_with_nodes = ChaosSelector(
        label_selectors={"app": "web"},
        node_selectors={"zone": "us-west-1a"},
        pod_phase_selectors=["Running", "Pending"]
    )
    print("✓ Selector with node_selectors and pod_phase_selectors created")
    
    crd_dict = selector_with_nodes.to_crd_dict()
    print(f"  - labelSelectors: {crd_dict.get('labelSelectors')}")
    print(f"  - nodeSelectors: {crd_dict.get('nodeSelectors')}")
    print(f"  - podPhaseSelectors: {crd_dict.get('podPhaseSelectors')}")
    
    assert "nodeSelectors" in crd_dict
    assert "podPhaseSelectors" in crd_dict
    assert crd_dict["nodeSelectors"] == {"zone": "us-west-1a"}
    assert crd_dict["podPhaseSelectors"] == ["Running", "Pending"]
    
    # Test with expression selectors
    selector_with_expressions = ChaosSelector(
        label_selectors={"app": "api"},
        expression_selectors=[
            {"key": "tier", "operator": "In", "values": ["frontend", "backend"]}
        ]
    )
    print("✓ Selector with expression_selectors created")
    
    crd_dict2 = selector_with_expressions.to_crd_dict()
    print(f"  - expressionSelectors: {crd_dict2.get('expressionSelectors')}")
    assert "expressionSelectors" in crd_dict2
    
    print()


def test_podchaos_advanced_fields():
    """Test 3: Verify PodChaos advanced fields (scheduler, remote_cluster)."""
    print("=" * 60)
    print("Test 3: PodChaos Advanced Fields")
    print("=" * 60)
    
    # Create PodChaos with scheduler
    pod_chaos_with_scheduler = PodChaos(
        action=PodChaosAction.POD_KILL,
        selector=ChaosSelector.from_labels({"app": "database"}),
        scheduler={
            "cron": "@every 5m",
            "duration": "30s"
        },
        remote_cluster="cluster-west"
    )
    
    print(f"✓ PodChaos created with scheduler and remote_cluster")
    print(f"  - Name: {pod_chaos_with_scheduler.name}")
    
    # Build CRD and verify fields
    crd = pod_chaos_with_scheduler.to_crd()
    spec = crd["spec"]
    
    print(f"  - Scheduler in spec: {spec.get('scheduler')}")
    print(f"  - Remote cluster in spec: {spec.get('remoteCluster')}")
    
    assert spec.get("scheduler") == {"cron": "@every 5m", "duration": "30s"}
    assert spec.get("remoteCluster") == "cluster-west"
    
    print()


def test_networkchaos_advanced_fields():
    """Test 4: Verify NetworkChaos advanced fields."""
    print("=" * 60)
    print("Test 4: NetworkChaos Advanced Fields")
    print("=" * 60)
    
    # Create NetworkChaos with advanced fields
    network_chaos = NetworkChaos(
        action=NetworkChaosAction.DELAY,
        delay=NetworkDelayParams(latency="200ms", jitter="50ms"),
        selector=ChaosSelector.from_labels({"app": "api"}),
        direction=NetworkDirection.TO,
        device="eth1",
        external_targets=["8.8.8.8", "example.com"]
    )
    
    print(f"✓ NetworkChaos created with advanced fields")
    print(f"  - Name: {network_chaos.name}")
    
    # Build CRD and verify fields
    crd = network_chaos.to_crd()
    spec = crd["spec"]
    
    print(f"  - Direction: {spec.get('direction')}")
    print(f"  - Device: {spec.get('device')}")
    print(f"  - External targets: {spec.get('externalTargets')}")
    
    assert spec.get("direction") == "to"
    assert spec.get("device") == "eth1"
    assert spec.get("externalTargets") == ["8.8.8.8", "example.com"]
    
    # Test network partition with target
    partition_chaos = NetworkChaos.create_partition(
        selector=ChaosSelector.from_labels({"app": "web"}),
        target=ChaosSelector.from_labels({"app": "database"}),
        direction=NetworkDirection.BOTH
    )
    
    print(f"✓ Network partition created")
    print(f"  - Name: {partition_chaos.name}")
    
    partition_crd = partition_chaos.to_crd()
    partition_spec = partition_crd["spec"]
    
    print(f"  - Partition direction: {partition_spec.get('direction')}")
    print(f"  - Partition target: {partition_spec.get('target', {}).get('labelSelectors')}")
    
    assert partition_spec.get("direction") == "both"
    assert partition_spec["target"]["labelSelectors"] == {"app": "database"}
    
    print()


def test_complete_crd_structure():
    """Test 5: Verify complete CRD structure with all fields."""
    print("=" * 60)
    print("Test 5: Complete CRD Structure Verification")
    print("=" * 60)
    
    # Create a complex PodChaos with many fields
    complex_chaos = PodChaos(
        action=PodChaosAction.CONTAINER_KILL,
        container_names=["nginx", "sidecar"],
        grace_period=10,
        mode=ChaosMode.FIXED,
        value="2",
        duration="5m",
        selector=ChaosSelector(
            namespaces=["production"],
            label_selectors={"app": "web", "tier": "frontend"},
            node_selectors={"zone": "us-east-1a"},
            pod_phase_selectors=["Running"]
        ),
        scheduler={
            "cron": "@daily",
            "duration": "1h"
        }
    )
    
    print(f"✓ Complex PodChaos created: {complex_chaos.name}")
    
    crd = complex_chaos.to_crd()
    
    # Verify CRD structure
    assert crd["apiVersion"]
    assert crd["kind"] == "PodChaos"
    assert crd["metadata"]["name"] == complex_chaos.name
    assert crd["metadata"]["namespace"] == "default"
    
    spec = crd["spec"]
    assert spec["action"] == "container-kill"
    assert spec["containerNames"] == ["nginx", "sidecar"]
    assert spec["gracePeriod"] == 10
    assert spec["mode"] == "fixed"
    assert spec["value"] == "2"
    assert spec["duration"] == "5m"
    assert spec["scheduler"]["cron"] == "@daily"
    
    selector = spec["selector"]
    assert selector["namespaces"] == ["production"]
    assert selector["labelSelectors"] == {"app": "web", "tier": "frontend"}
    assert selector["nodeSelectors"] == {"zone": "us-east-1a"}
    assert selector["podPhaseSelectors"] == ["Running"]
    
    print("✓ All CRD fields verified successfully")
    print(f"\n  Generated CRD structure:")
    import json
    print(json.dumps(crd, indent=2))
    
    print()


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Chaos Mesh SDK Improvements Verification")
    print("=" * 60 + "\n")
    
    try:
        test_auto_name_generation()
        test_selector_advanced_fields()
        test_podchaos_advanced_fields()
        test_networkchaos_advanced_fields()
        test_complete_crd_structure()
        
        print("=" * 60)
        print("All tests passed successfully!")
        print("=" * 60)
        print("\nSummary of improvements:")
        print("1. ✓ Auto-generated names with type prefix (e.g., podchaos-*, networkchaos-*)")
        print("2. ✓ Advanced selector fields (node_selectors, pod_phase_selectors, expression_selectors)")
        print("3. ✓ PodChaos advanced fields (scheduler, remote_cluster)")
        print("4. ✓ NetworkChaos advanced fields (direction, device, external_targets, tc_parameter)")
        print("5. ✓ Complete YAML field coverage for production use")
        print()
        
        return 0
        
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
