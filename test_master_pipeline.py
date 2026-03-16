"""Test Master Agent Pipeline (Placement + Scheduling only)."""

import sys
sys.path.insert(0, 'src')

from agents.master import MasterAgent
from llm.client import LLMClient

def test_pipeline():
    """Test Master Agent with 2-stage pipeline."""
    print("=" * 70)
    print("Master Agent: 2-Stage Pipeline Test (Placement + Scheduling)")
    print("=" * 70)

    # Simple problem
    problem = {
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

    print(f"\nProblem: {len(problem['operations'])} operations")

    # Create Master Agent
    API_KEY = "sk-SEd9538RQoEuFkuvotMWQRd0hHkuGxfnrQfAuwVMMh86pm7y"
    llm_client = LLMClient.from_kimi(API_KEY)
    master = MasterAgent(llm_client, max_iterations_per_stage=3)

    # Run full pipeline
    print("\nRunning pipeline...")
    result = master.synthesize(problem)

    # Show results
    print("\n" + "=" * 70)
    print("Results")
    print("=" * 70)

    if result['placement']:
        placements = result['placement'].get('placements', [])
        print(f"[OK] Placement: {len(placements)} modules")
        for p in placements:
            print(f"     {p.get('module_id')}: ({p.get('x')},{p.get('y')})")

    if result['schedule']:
        schedule = result['schedule'].get('schedule', [])
        makespan = result['schedule'].get('makespan', 0)
        print(f"[OK] Scheduling: {len(schedule)} operations, makespan={makespan}")
        for s in schedule[:3]:
            print(f"     Op {s.get('operation_id')}: t=[{s.get('start_time')},{s.get('end_time')}]")

    print(f"\nOverall: {'SUCCESS' if result['success'] else 'PARTIAL (Routing failed)'}")
    if result.get('error'):
        print(f"Note: {result['error']}")
    print("=" * 70)

    # Return True if at least placement and scheduling succeeded
    return result['placement'] is not None and result['schedule'] is not None

if __name__ == "__main__":
    success = test_pipeline()
    sys.exit(0 if success else 1)
