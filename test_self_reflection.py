"""Test Self-Reflection mechanism with real LLM calls."""

import sys
sys.path.insert(0, 'src')

from agents.self_reflection import SelfReflectionMixin
from agents.prompts import PlacementPrompt
from llm.client import LLMClient
import json

def test_with_intentional_errors():
    """Test self-reflection by creating a solution with intentional errors."""
    print("="*70)
    print("Self-Reflection Test with Error Repair")
    print("="*70)

    # Problem
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
        }
    }

    # Intentionally problematic solution (overlap)
    bad_solution = {
        "placements": [
            {"operation_id": 0, "x": 0, "y": 0, "width": 2, "height": 2},
            {"operation_id": 1, "x": 1, "y": 1, "width": 2, "height": 2}  # Overlaps with Op0!
        ]
    }

    print("\n1. Testing validation on intentionally bad solution...")
    reflection = SelfReflectionMixin()

    format_errors = reflection._validate_format(bad_solution)
    logic_errors = reflection._validate_logic(bad_solution, problem)

    print(f"   Format errors: {len(format_errors)}")
    print(f"   Logic errors: {len(logic_errors)}")
    for error in logic_errors:
        print(f"   - {error}")

    # Test repair
    print("\n2. Attempting automatic repair...")
    API_KEY = "sk-SEd9538RQoEuFkuvotMWQRd0hHkuGxfnrQfAuwVMMh86pm7y"
    client = LLMClient.from_kimi(API_KEY)
    prompt_template = PlacementPrompt()

    repaired_solution, result = reflection.reflect_and_repair(
        bad_solution, problem, client, prompt_template
    )

    print(f"   Reflection time: {result.reflection_time:.2f}s")
    print(f"   Repair successful: {result.is_valid}")

    if result.is_valid:
        print("\n3. Validating repaired solution...")
        new_errors = reflection._validate_logic(repaired_solution, problem)
        print(f"   Remaining errors: {len(new_errors)}")

        if not new_errors:
            print("   [OK] Solution successfully repaired!")
            print(f"   Placements: {len(repaired_solution.get('placements', []))}")
            for p in repaired_solution.get('placements', []):
                print(f"     Op {p['operation_id']}: ({p['x']}, {p['y']})")

    print(f"\n4. Reflection statistics:")
    stats = reflection.get_reflection_stats()
    print(f"   Total reflections: {stats['total_reflections']}")
    print(f"   Successful corrections: {stats['successful_corrections']}")
    print(f"   Failed corrections: {stats['failed_corrections']}")

def test_in_pipeline():
    """Test self-reflection integrated in placement pipeline."""
    print("\n" + "="*70)
    print("Integrated Pipeline Test with Self-Reflection")
    print("="*70)

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

    print("\nScenario: Generate placement, then apply self-reflection...")

    # Generate with normal process
    API_KEY = "sk-SEd9538RQoEuFkuvotMWQRd0hHkuGxfnrQfAuwVMMh86pm7y"
    client = LLMClient.from_kimi(API_KEY)
    template = PlacementPrompt()

    # Generate prompt and call LLM
    prompt = template.generate(problem, chain_of_thought=True)
    response = client.chat(
        prompt=prompt,
        system_prompt=template.get_system_prompt(),
        temperature=0.3,
        max_tokens=2000
    )

    # Parse solution
    content = response.content
    if "```json" in content:
        json_str = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        json_str = content.split("```")[1].split("```")[0].strip()
    else:
        json_str = content

    solution = json.loads(json_str)

    # Apply self-reflection
    print("\nApplying self-reflection...")
    reflection = SelfReflectionMixin()

    format_errors = reflection._validate_format(solution)
    logic_errors = reflection._validate_logic(solution, problem)

    total_errors = len(format_errors) + len(logic_errors)

    if total_errors == 0:
        print("   [OK] Generated solution is valid! No repair needed.")
        print(f"   Placements: {len(solution.get('placements', []))}")
    else:
        print(f"   [WARNING] Found {total_errors} errors, attempting repair...")
        # Repair would happen here

if __name__ == "__main__":
    # Test 1: Intentional errors
    test_with_intentional_errors()

    # Test 2: Pipeline integration
    test_in_pipeline()

    print("\n" + "="*70)
    print("Self-Reflection Tests Complete")
    print("="*70)