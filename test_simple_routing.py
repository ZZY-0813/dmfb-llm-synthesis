"""Simple test for Routing Agent end-to-end."""

import sys
import json
sys.path.insert(0, 'src')

from agents.prompts import RoutingPrompt
from agents.verifier import RoutingVerifier
from llm.client import LLMClient

def test_simple_routing():
    """Test with very simple routing problem."""
    print("=" * 70)
    print("Simple Routing Test")
    print("=" * 70)

    # Problem with placement and schedule already done
    problem = {
        "chip_width": 10,
        "chip_height": 10,
        "operations": [
            {"id": 0, "op_type": "mix", "module_type": "mixer_2x2", "dependencies": []},
            {"id": 1, "op_type": "detect", "module_type": "detector_1x2", "dependencies": [0]}
        ],
        "modules": {
            "mixer_2x2": {"width": 2, "height": 2, "exec_time": 3},
            "detector_1x2": {"width": 1, "height": 2, "exec_time": 2}
        },
        # Placement info: modules placed on chip
        "placements": [
            {"operation_id": 0, "x": 0, "y": 0, "width": 2, "height": 2},
            {"operation_id": 1, "x": 4, "y": 0, "width": 1, "height": 2}
        ],
        # Schedule info: when operations run
        "schedule": [
            {"operation_id": 0, "start_time": 0, "end_time": 3, "module_id": "mixer_0"},
            {"operation_id": 1, "start_time": 3, "end_time": 5, "module_id": "detector_0"}
        ]
    }

    print(f"\n[1] Problem: {len(problem['operations'])} operations")
    print(f"    Droplet route: Op0 (0,0) -> Op1 (4,0)")

    # Generate prompt
    prompt_template = RoutingPrompt()
    prompt = prompt_template.generate(problem, chain_of_thought=False)  # Routing simpler without CoT
    print(f"[2] Prompt generated ({len(prompt)} chars)")

    # Call LLM
    API_KEY = "sk-SEd9538RQoEuFkuvotMWQRd0hHkuGxfnrQfAuwVMMh86pm7y"
    client = LLMClient.from_kimi(API_KEY)

    print("[3] Calling LLM...")
    response = client.chat(
        prompt=prompt,
        system_prompt=prompt_template.get_system_prompt(),
        temperature=0.3,
        max_tokens=1500
    )
    print(f"[4] Response received ({len(response.content)} chars)")

    # Parse JSON
    content = response.content
    try:
        # Find JSON block
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            # Try to find JSON object
            start = content.find('{')
            end = content.rfind('}')
            if start >= 0 and end > start:
                json_str = content[start:end+1]
            else:
                raise ValueError("No JSON found in response")

        solution = json.loads(json_str)
        droplet_paths = solution.get('droplet_paths', [])
        total_time = solution.get('total_routing_time', 0)
        print(f"[5] Parsed {len(droplet_paths)} droplet paths, total_time={total_time}")

        # Show paths
        for dp in droplet_paths:
            path = dp.get('path', [])
            print(f"    Droplet {dp.get('droplet_id')}: {len(path)} steps")
            if path:
                print(f"      Start: ({path[0]['x']},{path[0]['y']},t={path[0]['t']})")
                print(f"      End:   ({path[-1]['x']},{path[-1]['y']},t={path[-1]['t']})")

    except json.JSONDecodeError as e:
        print(f"[5] JSON parse error: {e}")
        print(f"    Content preview:\n{content[:1000]}")
        return False

    # Verify
    print("[6] Verifying...")
    verifier = RoutingVerifier()
    result = verifier.verify(problem, solution)

    print(f"[7] Verification: {'PASS' if result.is_valid else 'FAIL'}")
    print(f"    Violations: {len(result.violations)}")

    if result.violations:
        for v in result.violations[:3]:
            print(f"    - {v.violation_type.value}: {v.message[:60]}")

    return result.is_valid

if __name__ == "__main__":
    success = test_simple_routing()
    sys.exit(0 if success else 1)
