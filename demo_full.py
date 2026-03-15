"""
Full System Demo - Week 1-4 Progress

Demonstrates:
1. Dataset generation
2. Verifier system
3. LLM Client
4. Agent framework (structure)
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, 'src')

from baseline.problem import DMFBProblem, Operation, Module, ModuleType
from agents.verifier import (
    PlacementVerifier, ScheduleVerifier, RoutingVerifier,
    UnifiedVerifier, ViolationType
)


def demo_dataset():
    """Demo: Show generated dataset."""
    print("\n" + "="*60)
    print("1. DATASET GENERATION")
    print("="*60)

    dataset_dir = Path("data/dataset")
    if not dataset_dir.exists():
        print("Dataset not generated yet. Run: python src/data/dataset_generator.py")
        return

    # Load metadata
    with open(dataset_dir / "metadata.json") as f:
        metadata = json.load(f)

    print(f"\nDataset Statistics:")
    print(f"  Total problems: {metadata['statistics']['total_problems']}")
    print(f"  Small (20 ops): {metadata['statistics']['by_size']['small']}")
    print(f"  Large (50 ops): {metadata['statistics']['by_size']['large']}")

    # Load a sample problem
    with open(dataset_dir / "problems_small.json") as f:
        problems = json.load(f)

    sample = DMFBProblem.from_dict(problems[0])
    print(f"\nSample Problem: {sample.name}")
    print(f"  Operations: {len(sample.operations)}")
    print(f"  Chip: {sample.chip_width}x{sample.chip_height}")
    print(f"  Critical path length: {sample.get_critical_path_length()}")

    # Show operations
    print(f"\n  First 5 operations:")
    for op in sample.operations[:5]:
        deps = f" (deps: {op.dependencies})" if op.dependencies else ""
        print(f"    Op {op.id}: {op.op_type} on {op.module_type}{deps}")


def demo_verifiers():
    """Demo: All three verifiers."""
    print("\n" + "="*60)
    print("2. VERIFIER SYSTEM")
    print("="*60)

    # Create test problem
    modules = {
        "mixer_2x2": Module("mixer_2x2", ModuleType.MIXER, 2, 2, 3),
        "heater_1x1": Module("heater_1x1", ModuleType.HEATER, 1, 1, 4),
    }

    operations = [
        Operation(id=0, op_type="mix", module_type="mixer_2x2"),
        Operation(id=1, op_type="heat", module_type="heater_1x1", dependencies=[0]),
    ]

    problem = DMFBProblem(
        name="demo",
        chip_width=10,
        chip_height=10,
        modules=modules,
        operations=operations
    )

    # Test Placement Verifier
    print("\n[Placement Verifier]")
    placement_v = PlacementVerifier()

    # Valid placement
    placements = [
        {"module_id": "mixer_2x2", "x": 2, "y": 2, "width": 2, "height": 2},
        {"module_id": "heater_1x1", "x": 5, "y": 5, "width": 1, "height": 1}
    ]
    result = placement_v.verify(problem, {"placements": placements})
    print(f"  Valid placement: {'PASS' if result.is_valid else 'FAIL'}")

    # Invalid placement (overlap)
    bad_placements = [
        {"module_id": "m1", "x": 2, "y": 2, "width": 3, "height": 3},
        {"module_id": "m2", "x": 3, "y": 3, "width": 3, "height": 3}
    ]
    result = placement_v.verify(problem, {"placements": bad_placements})
    print(f"  Overlap detection: {'PASS' if not result.is_valid else 'FAIL'}")
    print(f"    Error: {result.violations[0].violation_type.value}")

    # Test Schedule Verifier
    print("\n[Schedule Verifier]")
    schedule_v = ScheduleVerifier()

    # Valid schedule
    schedule = [
        {"operation_id": 0, "start_time": 0, "end_time": 3, "module_id": "mixer_2x2"},
        {"operation_id": 1, "start_time": 3, "end_time": 7, "module_id": "heater_1x1"}
    ]
    result = schedule_v.verify(problem, {"schedule": schedule})
    print(f"  Valid schedule: {'PASS' if result.is_valid else 'FAIL'}")

    # Invalid schedule (dependency violation)
    bad_schedule = [
        {"operation_id": 0, "start_time": 0, "end_time": 3, "module_id": "mixer_2x2"},
        {"operation_id": 1, "start_time": 1, "end_time": 5, "module_id": "heater_1x1"}
    ]
    result = schedule_v.verify(problem, {"schedule": bad_schedule})
    print(f"  Dependency violation: {'PASS' if not result.is_valid else 'FAIL'}")
    print(f"    Error: {result.violations[0].violation_type.value}")

    # Test Routing Verifier
    print("\n[Routing Verifier]")
    routing_v = RoutingVerifier()

    # Valid routes
    routes = [
        {"droplet_id": "d1", "path": [[0, 1, 1], [1, 2, 1], [2, 3, 1]]},
        {"droplet_id": "d2", "path": [[0, 5, 5], [1, 5, 6], [2, 5, 7]]}
    ]
    result = routing_v.verify(problem, {"routes": routes})
    print(f"  Valid routes: {'PASS' if result.is_valid else 'FAIL'}")

    # Invalid routes (collision)
    bad_routes = [
        {"droplet_id": "d1", "path": [[0, 1, 1], [1, 2, 1], [2, 3, 1]]},
        {"droplet_id": "d2", "path": [[0, 3, 3], [1, 2, 1], [2, 1, 1]]}  # Collision at t=1, (2,1)
    ]
    result = routing_v.verify(problem, {"routes": bad_routes})
    print(f"  Collision detection: {'PASS' if not result.is_valid else 'FAIL'}")
    print(f"    Error: {result.violations[0].violation_type.value}")

    # Unified verification
    print("\n[Unified Verifier]")
    unified = UnifiedVerifier()
    solution = {
        "placements": placements,
        "schedule": schedule,
        "routes": routes
    }
    results = unified.verify_full(problem, solution)
    print(f"  Full solution verification:")
    for stage, result in results.items():
        status = "PASS" if result.is_valid else "FAIL"
        print(f"    {stage}: {status}")


def demo_llm_client():
    """Demo: LLM Client structure."""
    print("\n" + "="*60)
    print("3. LLM CLIENT")
    print("="*60)

    from llm import LLMClient, LLMProvider

    print("\nSupported Providers:")
    for provider in LLMProvider:
        print(f"  - {provider.value}")

    print("\nCreating clients:")

    # Kimi client
    try:
        client = LLMClient.from_kimi("dummy-key-for-demo")
        print(f"  Kimi client: model={client.config.model}")
    except Exception as e:
        print(f"  Kimi client: configured (API key needed for actual calls)")

    print("\nUsage example:")
    print("  from llm import LLMClient")
    print("  client = LLMClient.from_kimi('your-api-key')")
    print("  response = client.chat('Generate a placement for...')")
    print("  print(response.content)")


def demo_agents():
    """Demo: Agent framework structure."""
    print("\n" + "="*60)
    print("4. AGENT FRAMEWORK")
    print("="*60)

    from agents import (
        BaseAgent, MasterAgent,
        PlacementAgent, SchedulingAgent, RoutingAgent,
        AgentStage, AgentContext
    )

    print("\nAgent Hierarchy:")
    print("  BaseAgent (abstract)")
    print("    +-- PlacementAgent")
    print("    +-- SchedulingAgent")
    print("    +-- RoutingAgent")
    print("\n  MasterAgent (coordinates all three)")

    print("\nSynthesis Pipeline:")
    print("  Input Problem")
    print("      |")
    print("  [PlacementAgent] -> placement.json")
    print("      |")
    print("  [SchedulingAgent] -> schedule.json")
    print("      |")
    print("  [RoutingAgent] -> routes.json")
    print("      |")
    print("  Validated Solution")

    print("\nKey Features:")
    print("  - Iterative repair (max 5 iterations by default)")
    print("  - LLM-generated solutions with verification feedback")
    print("  - Natural language reasoning extraction")
    print("  - Error-to-prompt feedback loop")

    # Show agent creation
    print("\nExample Usage:")
    print("""
    from llm import LLMClient
    from agents import PlacementAgent, MasterAgent

    # Create LLM client
    client = LLMClient.from_kimi('your-api-key')

    # Create individual agent
    placement_agent = PlacementAgent(client)

    # Or create full pipeline
    master = MasterAgent(
        placement_agent=PlacementAgent(client),
        scheduling_agent=SchedulingAgent(client),
        routing_agent=RoutingAgent(client)
    )

    # Run synthesis
    result = master.synthesize(problem)
    """)


def demo_summary():
    """Show overall progress."""
    print("\n" + "="*60)
    print("5. PROJECT STATUS")
    print("="*60)

    status = {
        "Week 1: Verifiers": {
            "Placement Verifier": "[OK] Complete",
            "Schedule Verifier": "[OK] Complete",
            "Routing Verifier": "[OK] Complete",
            "Unified Verifier": "[OK] Complete",
            "Tests": "[OK] All passing"
        },
        "Week 2: Dataset": {
            "Problem Generator": "[OK] Complete",
            "Small problems (20 ops)": "[OK] 50 generated",
            "Large problems (50 ops)": "[OK] 50 generated",
            "Baseline solutions": "[OK] Generated (dummy)"
        },
        "Week 3: Visualization": {
            "3D Visualization": "[NEXT] Optional (can skip)"
        },
        "Week 4: LLM Integration": {
            "LLM Client (multi-provider)": "[OK] Complete",
            "Base Agent class": "[OK] Complete",
            "Placement Agent": "[OK] Complete",
            "Scheduling Agent": "[OK] Complete",
            "Routing Agent": "[OK] Complete",
            "Master Agent": "[OK] Complete"
        }
    }

    for week, items in status.items():
        print(f"\n{week}")
        for item, item_status in items.items():
            print(f"  {item_status} {item}")

    print("\n" + "="*60)
    print("Next Steps:")
    print("="*60)
    print("""
1. Verify API Key works (current key returned 401)
2. Test end-to-end synthesis with actual LLM calls
3. Implement RAG retrieval from dataset
4. Add prompt templates with few-shot examples
5. Collect real baseline solutions (run actual GA/SA)
    """)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("DMFB LLM SYNTHESIS - FULL SYSTEM DEMO")
    print("="*60)
    print("\nCurrent progress: Week 1-4 Complete")

    demo_dataset()
    demo_verifiers()
    demo_llm_client()
    demo_agents()
    demo_summary()

    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60)
