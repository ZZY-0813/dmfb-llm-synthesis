"""Integration test: Dataset → Prompt → LLM → Verifier."""

import sys
import json
sys.path.insert(0, 'src')

from agents.prompts import PlacementPrompt
from agents.verifier import PlacementVerifier
from llm.client import LLMClient

def load_test_problem():
    """Load a test problem from dataset."""
    try:
        with open('data/dataset/problems_small.json', 'r') as f:
            problems = json.load(f)
        return problems[0] if problems else None
    except FileNotFoundError:
        print("Dataset not found, creating minimal test problem...")
        return {
            "chip_width": 20,
            "chip_height": 20,
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

def test_full_pipeline():
    """Test full pipeline: Problem → Prompt → LLM → Parse → Verify."""
    print("=" * 70)
    print("Integration Test: Full Pipeline")
    print("=" * 70)

    # Step 1: Load problem
    print("\n[1/5] Loading problem...")
    problem = load_test_problem()
    if not problem:
        print("[FAIL] No problem loaded")
        return False

    print(f"[OK] Loaded problem with {len(problem.get('operations', []))} operations")
    print(f"      Chip: {problem.get('chip_width')}x{problem.get('chip_height')}")

    # Step 2: Generate prompt
    print("\n[2/5] Generating prompt...")
    prompt_template = PlacementPrompt()
    prompt = prompt_template.generate(problem, chain_of_thought=True)
    system_prompt = prompt_template.get_system_prompt()

    print(f"[OK] Generated prompt ({len(prompt)} chars)")
    print(f"      System prompt: {len(system_prompt)} chars")

    # Step 3: Call LLM
    print("\n[3/5] Calling LLM (Kimi)...")
    API_KEY = "sk-SEd9538RQoEuFkuvotMWQRd0hHkuGxfnrQfAuwVMMh86pm7y"
    client = LLMClient.from_kimi(API_KEY)

    try:
        response = client.chat(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1500
        )
        print(f"[OK] LLM response received ({len(response.content)} chars)")
        print(f"      Tokens: {response.usage}")
    except Exception as e:
        print(f"[FAIL] LLM call failed: {e}")
        return False

    # Step 4: Parse solution
    print("\n[4/5] Parsing solution...")
    content = response.content

    # Extract JSON
    try:
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content

        solution = json.loads(json_str)
        placements = solution.get('placements', [])
        print(f"[OK] Parsed {len(placements)} placements")

        # Show first placement
        if placements:
            p = placements[0]
            print(f"      Example: Op {p.get('operation_id')} at ({p.get('x')},{p.get('y')})")

    except json.JSONDecodeError as e:
        print(f"[FAIL] JSON parse error: {e}")
        print(f"      Content preview: {content[:500]}")
        return False

    # Step 5: Verify
    print("\n[5/5] Verifying solution...")
    verifier = PlacementVerifier()
    result = verifier.verify(problem, solution)

    print(f"[{'OK' if result.is_valid else 'FAIL'}] Verification {'PASSED' if result.is_valid else 'FAILED'}")
    print(f"      Violations: {len(result.violations)}")

    if result.violations:
        print("\n      Violation details:")
        for v in result.violations[:3]:
            print(f"        - {v.violation_type.value}: {v.message}")

    # Summary
    print("\n" + "=" * 70)
    print("Integration Test Summary")
    print("=" * 70)
    print(f"Problem:    {len(problem.get('operations', []))} operations")
    print(f"Prompt:     {len(prompt)} chars")
    print(f"LLM output: {len(response.content)} chars ({response.usage.get('total_tokens', 0)} tokens)")
    print(f"Placements: {len(placements)}")
    print(f"Valid:      {'[OK] YES' if result.is_valid else '[FAIL] NO'}")
    print(f"Violations: {len(result.violations)}")
    print("=" * 70)

    return result.is_valid

if __name__ == "__main__":
    success = test_full_pipeline()
    sys.exit(0 if success else 1)
