"""Simple test with minimal problem."""

import sys
import json
sys.path.insert(0, 'src')

from agents.prompts import PlacementPrompt
from agents.verifier import PlacementVerifier
from llm.client import LLMClient

def test_simple_placement():
    """Test with very simple problem."""
    print("=" * 70)
    print("Simple Placement Test")
    print("=" * 70)

    # Simple problem with 3 operations
    problem = {
        "chip_width": 10,
        "chip_height": 10,
        "operations": [
            {"id": 0, "op_type": "mix", "module_type": "mixer_2x2", "dependencies": []},
            {"id": 1, "op_type": "detect", "module_type": "detector_1x2", "dependencies": [0]},
            {"id": 2, "op_type": "mix", "module_type": "mixer_2x2", "dependencies": [0]}
        ],
        "modules": {
            "mixer_2x2": {"width": 2, "height": 2, "exec_time": 3},
            "detector_1x2": {"width": 1, "height": 2, "exec_time": 2}
        }
    }

    print(f"\n[1] Problem: {len(problem['operations'])} operations on {problem['chip_width']}x{problem['chip_height']} chip")

    # Generate prompt
    prompt_template = PlacementPrompt()
    prompt = prompt_template.generate(problem, chain_of_thought=True)
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
        placements = solution.get('placements', [])
        print(f"[5] Parsed {len(placements)} placements")

        # Show placements
        for p in placements:
            print(f"    Op {p.get('operation_id')}: ({p.get('x')},{p.get('y')}) "
                  f"{p.get('width')}x{p.get('height')}")

    except json.JSONDecodeError as e:
        print(f"[5] JSON parse error: {e}")
        print(f"    Content preview:\n{content[:1000]}")
        return False

    # Verify
    print("[6] Verifying...")
    verifier = PlacementVerifier()
    result = verifier.verify(problem, solution)

    print(f"[7] Verification: {'PASS' if result.is_valid else 'FAIL'}")
    print(f"    Violations: {len(result.violations)}")

    if result.violations:
        for v in result.violations[:3]:
            print(f"    - {v.violation_type.value}: {v.message[:60]}")

    return result.is_valid

if __name__ == "__main__":
    success = test_simple_placement()
    sys.exit(0 if success else 1)
