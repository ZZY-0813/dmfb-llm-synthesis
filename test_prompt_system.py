"""Test Prompt Template System."""

import sys
import json
sys.path.insert(0, 'src')

from agents.prompts import PlacementPrompt, SchedulingPrompt, RoutingPrompt

def test_placement_prompt():
    """Test placement prompt generation."""
    print("=" * 60)
    print("Test 1: Placement Prompt")
    print("=" * 60)

    # Sample problem
    problem = {
        "chip_width": 20,
        "chip_height": 20,
        "modules": {
            "mixer_2x2": {"width": 2, "height": 2, "exec_time": 3},
            "detector_1x2": {"width": 1, "height": 2, "exec_time": 2}
        },
        "operations": [
            {"id": 0, "op_type": "mix", "module_type": "mixer_2x2", "dependencies": []},
            {"id": 1, "op_type": "detect", "module_type": "detector_1x2", "dependencies": [0]}
        ]
    }

    # Generate prompt
    template = PlacementPrompt()
    prompt = template.generate(problem, chain_of_thought=True)

    print(f"\nSystem Prompt (first 200 chars):\n{template.get_system_prompt()[:200]}...")
    print(f"\nUser Prompt (first 800 chars):\n{prompt[:800]}...")
    print(f"\nPrompt length: {len(prompt)} chars")

    return True

def test_scheduling_prompt():
    """Test scheduling prompt generation."""
    print("\n" + "=" * 60)
    print("Test 2: Scheduling Prompt")
    print("=" * 60)

    problem = {
        "chip_width": 20,
        "chip_height": 20,
        "modules": {
            "mixer_2x2": {"width": 2, "height": 2, "exec_time": 3},
            "detector_1x2": {"width": 1, "height": 2, "exec_time": 2}
        },
        "operations": [
            {"id": 0, "op_type": "mix", "module_type": "mixer_2x2", "dependencies": []},
            {"id": 1, "op_type": "detect", "module_type": "detector_1x2", "dependencies": [0]},
            {"id": 2, "op_type": "mix", "module_type": "mixer_2x2", "dependencies": []}
        ]
    }

    template = SchedulingPrompt()
    prompt = template.generate(problem, chain_of_thought=True)

    print(f"\nSystem Prompt (first 200 chars):\n{template.get_system_prompt()[:200]}...")
    print(f"\nUser Prompt sections:\n")

    # Show sections
    sections = prompt.split("##")
    for section in sections[:4]:  # First 4 sections
        lines = section.strip().split("\n")
        if lines:
            print(f"  - {lines[0][:60]}...")

    print(f"\nPrompt length: {len(prompt)} chars")

    return True

def test_routing_prompt():
    """Test routing prompt generation."""
    print("\n" + "=" * 60)
    print("Test 3: Routing Prompt")
    print("=" * 60)

    problem = {
        "chip_width": 20,
        "chip_height": 20,
        "modules": {
            "mixer_2x2": {"width": 2, "height": 2, "exec_time": 3}
        },
        "operations": [
            {"id": 0, "op_type": "mix", "module_type": "mixer_2x2", "dependencies": []},
            {"id": 1, "op_type": "mix", "module_type": "mixer_2x2", "dependencies": [0]}
        ],
        "placements": [
            {"operation_id": 0, "x": 0, "y": 0, "width": 2, "height": 2},
            {"operation_id": 1, "x": 10, "y": 10, "width": 2, "height": 2}
        ],
        "schedule": [
            {"operation_id": 0, "start_time": 0, "end_time": 3, "module_id": "mixer_2x2"},
            {"operation_id": 1, "start_time": 3, "end_time": 6, "module_id": "mixer_2x2"}
        ]
    }

    template = RoutingPrompt()
    prompt = template.generate(problem, chain_of_thought=False)

    print(f"\nSystem Prompt (first 200 chars):\n{template.get_system_prompt()[:200]}...")
    print(f"\nPrompt length: {len(prompt)} chars")

    return True

def test_with_llm():
    """Test actual LLM call with placement prompt."""
    print("\n" + "=" * 60)
    print("Test 4: Full Integration (Prompt + LLM)")
    print("=" * 60)

    from llm.client import LLMClient

    API_KEY = "sk-SEd9538RQoEuFkuvotMWQRd0hHkuGxfnrQfAuwVMMh86pm7y"

    # Create client
    client = LLMClient.from_kimi(API_KEY)

    # Small test problem
    problem = {
        "chip_width": 10,
        "chip_height": 10,
        "modules": {
            "mixer_2x2": {"width": 2, "height": 2, "exec_time": 3}
        },
        "operations": [
            {"id": 0, "op_type": "mix", "module_type": "mixer_2x2", "dependencies": []}
        ]
    }

    # Generate prompt
    template = PlacementPrompt()
    prompt = template.generate(problem, chain_of_thought=True)

    print(f"\nSending prompt to Kimi API...")
    print(f"Prompt length: {len(prompt)} chars")

    try:
        response = client.chat(
            prompt=prompt,
            system_prompt=template.get_system_prompt(),
            temperature=0.3,
            max_tokens=800
        )

        print(f"\n[OK] Success!")
        print(f"\nResponse (first 600 chars):\n{response.content[:600]}...")
        print(f"\nToken usage: {response.usage}")

        # Try to parse as JSON
        try:
            content = response.content
            # Extract JSON from markdown if present
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content

            result = json.loads(json_str)
            print(f"\n[OK] Valid JSON response!")
            print(f"Placements: {len(result.get('placements', []))}")
        except json.JSONDecodeError as e:
            print(f"\n[WARNING] Response is not valid JSON: {e}")

        return True

    except Exception as e:
        print(f"\n[FAIL] {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    print("\nPrompt Template System Tests\n")

    results = []

    # Run tests
    results.append(("Placement Prompt", test_placement_prompt()))
    results.append(("Scheduling Prompt", test_scheduling_prompt()))
    results.append(("Routing Prompt", test_routing_prompt()))
    results.append(("LLM Integration", test_with_llm()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, passed in results:
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {name}")

    print("\n" + "=" * 60)
