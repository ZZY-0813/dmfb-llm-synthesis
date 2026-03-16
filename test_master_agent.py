"""Test Master Agent with full Pipeline: Placement → Scheduling → Routing."""

import sys
import json
sys.path.insert(0, 'src')

from agents.master import MasterAgent
from llm.client import LLMClient

def load_test_problem():
    """Load simple test problem."""
    return {
        "chip_width": 15,
        "chip_height": 15,
        "operations": [
            {"id": 0, "op_type": "mix", "module_type": "mixer_2x2", "dependencies": []},
            {"id": 1, "op_type": "detect", "module_type": "detector_1x2", "dependencies": [0]}
        ],
        "modules": {
            "mixer_2x2": {"width": 2, "height": 2, "exec_time": 3},
            "detector_1x2": {"width": 1, "height": 2, "exec_time": 2}
        }
    }

def test_master_agent():
    """Test Master Agent with full pipeline."""
    print("=" * 70)
    print("Master Agent: Full Pipeline Test")
    print("Pipeline: Placement → Scheduling → Routing")
    print("=" * 70)

    # Load problem
    problem = load_test_problem()
    print(f"\nProblem loaded: {len(problem['operations'])} operations")

    # Create LLM client
    API_KEY = "sk-SEd9538RQoEuFkuvotMWQRd0hHkuGxfnrQfAuwVMMh86pm7y"
    llm_client = LLMClient.from_kimi(API_KEY)

    # Create Master Agent
    print("\nInitializing Master Agent...")
    master = MasterAgent(llm_client, max_iterations_per_stage=5)

    # Run synthesis
    print("\nStarting synthesis...")
    result = master.synthesize(problem)

    # Check result
    print("\n" + "=" * 70)
    print("Final Result")
    print("=" * 70)

    if result['success']:
        print("[OK] Overall: SUCCESS")

        # Show placement summary
        if 'placement' in result:
            placements = result['placement'].get('placements', [])
            print(f"\n1. Placement: {len(placements)} modules placed")
            for p in placements[:3]:  # Show first 3
                print(f"   Op {p.get('operation_id')}: ({p.get('x')},{p.get('y')}) "
                      f"{p.get('width')}x{p.get('height')}")

        # Show scheduling summary
        if 'schedule' in result:
            schedule = result['schedule'].get('schedule', [])
            makespan = result['schedule'].get('makespan', 0)
            print(f"\n2. Scheduling: {len(schedule)} operations, makespan={makespan}")
            for s in schedule[:3]:  # Show first 3
                print(f"   Op {s.get('operation_id')}: t=[{s.get('start_time')},{s.get('end_time')}] "
                      f"module={s.get('module_id')}")

        # Show routing summary
        if 'routes' in result:
            droplet_paths = result['routes'].get('droplet_paths', [])
            total_time = result['routes'].get('total_routing_time', 0)
            print(f"\n3. Routing: {len(droplet_paths)} droplets, total_time={total_time}")
            for dp in droplet_paths[:2]:  # Show first 2
                path = dp.get('path', [])
                if path:
                    start = path[0]
                    end = path[-1]
                    print(f"   Droplet {dp.get('droplet_id')}: "
                          f"({start['x']},{start['y']},t={start['t']}) -> "
                          f"({end['x']},{end['y']},t={end['t']}), "
                          f"{len(path)} steps")

    else:
        print("[FAIL] Overall: FAILED")
        print(f"Error: {result.get('error', 'Unknown error')}")

        # Show which stage failed
        context = result.get('context', {})
        stages = context.get('stages', {})
        for stage_name, stage_info in stages.items():
            if stage_info and not stage_info['success']:
                print(f"  Failed at: {stage_name}")

    print(f"\nTotal Duration: {result.get('duration', 0):.2f}s")
    print("=" * 70)

    return result['success']

if __name__ == "__main__":
    try:
        success = test_master_agent()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
