"""
End-to-End Agent Demo with Mock LLM

Demonstrates full synthesis pipeline without requiring API key.
"""

import sys
sys.path.insert(0, 'src')

from baseline.problem import DMFBProblem, Operation, Module, ModuleType
from agents import PlacementAgent, SchedulingAgent, RoutingAgent, MasterAgent, AgentContext
from llm.mock_client import MockLLMClient


def demo_placement_agent():
    """Demo: Placement Agent with Mock LLM."""
    print("\n" + "="*60)
    print("PLACEMENT AGENT DEMO (Mock Mode)")
    print("="*60)

    # Create test problem
    modules = {
        "mixer_2x2": Module("mixer_2x2", ModuleType.MIXER, 2, 2, 3),
        "heater_1x1": Module("heater_1x1", ModuleType.HEATER, 1, 1, 4),
        "detector_1x2": Module("detector_1x2", ModuleType.DETECTOR, 1, 2, 2),
    }

    operations = [
        Operation(id=0, op_type="mix", module_type="mixer_2x2"),
        Operation(id=1, op_type="heat", module_type="heater_1x1", dependencies=[0]),
        Operation(id=2, op_type="detect", module_type="detector_1x2", dependencies=[1]),
    ]

    problem = DMFBProblem(
        name="demo_placement",
        chip_width=10,
        chip_height=10,
        modules=modules,
        operations=operations
    )

    # Test 1: Success mode
    print("\n[Test 1] Success Mode (valid placement):")
    client = MockLLMClient(mode="success")
    agent = PlacementAgent(client, max_iterations=3, verbose=True)

    context = AgentContext(problem=problem)
    result = agent.solve(context)

    print(f"\nResult: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Iterations: {result.iterations}")
    print(f"LLM calls: {result.llm_calls}")
    if result.solution:
        print(f"Solution: {len(result.solution)} modules placed")
        for p in result.solution:
            print(f"  - {p['module_id']} at ({p['x']},{p['y']})")

    # Test 2: Error mode (with repair)
    print("\n" + "-"*40)
    print("\n[Test 2] Error Mode (with iterative repair):")
    client = MockLLMClient(mode="error")  # Returns invalid placement first
    agent = PlacementAgent(client, max_iterations=3, verbose=True)

    context = AgentContext(problem=problem)
    result = agent.solve(context)

    print(f"\nResult: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Iterations: {result.iterations}")
    print(f"Note: Even with error mode, agent may succeed if verifier")
    print(f"      feedback leads to valid solution")


def demo_scheduling_agent():
    """Demo: Scheduling Agent with Mock LLM."""
    print("\n" + "="*60)
    print("SCHEDULING AGENT DEMO (Mock Mode)")
    print("="*60)

    modules = {
        "mixer_2x2": Module("mixer_2x2", ModuleType.MIXER, 2, 2, 3),
        "heater_1x1": Module("heater_1x1", ModuleType.HEATER, 1, 1, 4),
    }

    operations = [
        Operation(id=0, op_type="mix", module_type="mixer_2x2"),
        Operation(id=1, op_type="heat", module_type="heater_1x1", dependencies=[0]),
    ]

    problem = DMFBProblem(
        name="demo_schedule",
        chip_width=10,
        chip_height=10,
        modules=modules,
        operations=operations
    )

    print("\n[Test] Schedule Generation:")
    client = MockLLMClient(mode="success")
    agent = SchedulingAgent(client, max_iterations=3, verbose=True)

    # Mock placement (would come from Placement Agent)
    context = AgentContext(
        problem=problem,
        placement=[
            {"module_id": "mixer_2x2", "x": 2, "y": 2, "width": 2, "height": 2},
            {"module_id": "heater_1x1", "x": 5, "y": 5, "width": 1, "height": 1},
        ]
    )

    result = agent.solve(context)

    print(f"\nResult: {'SUCCESS' if result.success else 'FAILED'}")
    if result.solution:
        print(f"Schedule: {len(result.solution)} operations")
        for s in result.solution:
            op_id = s.get('operation_id', s.get('op_id', '?'))
            print(f"  - Op {op_id}: t={s.get('start_time', '?')}-{s.get('end_time', '?')}")


def demo_full_pipeline():
    """Demo: Full synthesis pipeline."""
    print("\n" + "="*60)
    print("FULL PIPELINE DEMO (Mock Mode)")
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
        name="demo_pipeline",
        chip_width=10,
        chip_height=10,
        modules=modules,
        operations=operations
    )

    print(f"\nProblem: {problem.name}")
    print(f"  Operations: {len(problem.operations)}")
    print(f"  Chip: {problem.chip_width}x{problem.chip_height}")

    # Create Master Agent with Mock LLM
    print("\nInitializing Master Agent with Mock LLM...")
    client = MockLLMClient(mode="success")

    master = MasterAgent(
        placement_agent=PlacementAgent(client, max_iterations=2, verbose=False),
        scheduling_agent=SchedulingAgent(client, max_iterations=2, verbose=False),
        routing_agent=RoutingAgent(client, max_iterations=2, verbose=False),
        verbose=True
    )

    print("\nRunning synthesis pipeline...")
    result = master.synthesize(problem)

    # Show results
    print("\n" + "-"*40)
    print("SYNTHESIS RESULTS")
    print("-"*40)

    summary = result['summary']
    print(f"\nStage Results:")
    print(f"  Placement:   {'PASS' if summary['success_placement'] else 'FAIL'}")
    print(f"  Scheduling:  {'PASS' if summary['success_scheduling'] else 'FAIL'}")
    print(f"  Routing:     {'PASS' if summary['success_routing'] else 'FAIL'}")

    print(f"\nPerformance:")
    print(f"  Total time: {summary['total_time_seconds']:.2f}s")
    print(f"  LLM calls: {summary['total_llm_calls']}")
    print(f"  Iterations: {summary['total_iterations']}")

    # Show solution
    solution = result['solution']
    if solution['placement']:
        print(f"\nPlacement ({len(solution['placement'])} modules):")
        for p in solution['placement']:
            print(f"  - {p['module_id']} at ({p['x']},{p['y']})")

    if solution['schedule']:
        print(f"\nSchedule ({len(solution['schedule'])} operations):")
        for s in solution['schedule']:
            op_id = s.get('operation_id', s.get('op_id', '?'))
            start = s.get('start_time', '?')
            end = s.get('end_time', '?')
            print(f"  - Op {op_id}: t={start}-{end}")


def demo_with_real_api():
    """Show how to switch to real API."""
    print("\n" + "="*60)
    print("SWITCHING TO REAL API")
    print("="*60)

    print("""
To use the real Kimi API instead of Mock:

1. Set your API key:
   export KIMI_API_KEY="your-api-key"

2. Change the client initialization:

   # From:
   from llm.mock_client import MockLLMClient
   client = MockLLMClient(mode="success")

   # To:
   from llm import LLMClient
   client = LLMClient.from_kimi("your-api-key")

3. Everything else stays the same!

   master = MasterAgent(
       placement_agent=PlacementAgent(client),
       scheduling_agent=SchedulingAgent(client),
       routing_agent=RoutingAgent(client)
   )
   result = master.synthesize(problem)
""")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("DMFB AGENT - END TO END DEMO")
    print("="*60)
    print("\nUsing Mock LLM Client (no API key required)")
    print("This demonstrates the full framework functionality")

    demo_placement_agent()
    demo_scheduling_agent()
    demo_full_pipeline()
    demo_with_real_api()

    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("  1. Get a valid API key")
    print("  2. Replace MockLLMClient with LLMClient")
    print("  3. Run real synthesis experiments")
