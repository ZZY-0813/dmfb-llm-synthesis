"""Test Seven-Section Prompt Engineering optimization."""

import sys
sys.path.insert(0, 'src')

from agents.prompts import PlacementPrompt
from llm.client import LLMClient

def test_seven_section_placement():
    """Test placement with optimized seven-section prompt."""
    print("=" * 70)
    print("Seven-Section Prompt Engineering Test")
    print("=" * 70)

    # Simple test problem
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

    print(f"\n[1] Generating seven-section prompt...")
    prompt_template = PlacementPrompt()
    prompt = prompt_template.generate(problem, chain_of_thought=True)

    # Show prompt structure
    print(f"[OK] Prompt generated ({len(prompt)} chars)")
    print(f"\nPrompt Structure:")
    sections = prompt.split("## Section")
    for i, section in enumerate(sections[1:], 1):
        lines = section.strip().split("\n")
        title = lines[0].strip()
        content_preview = " ".join(lines[1:3]).strip()[:80]
        print(f"  Section {i}: {title}")
        print(f"    Preview: {content_preview}...")

    # Test with LLM
    print(f"\n[2] Testing with Kimi API...")
    API_KEY = "sk-SEd9538RQoEuFkuvotMWQRd0hHkuGxfnrQfAuwVMMh86pm7y"
    client = LLMClient.from_kimi(API_KEY)

    try:
        response = client.chat(
            prompt=prompt,
            system_prompt=prompt_template.get_system_prompt(),
            temperature=0.3,
            max_tokens=2000
        )

        print(f"[OK] Response received ({len(response.content)} chars)")

        # Parse and validate
        content = response.content
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content

        import json
        solution = json.loads(json_str)
        placements = solution.get('placements', [])

        print(f"\n[3] Validation Results:")
        print(f"  Placements: {len(placements)}")

        # Show placements
        for p in placements:
            print(f"    Op {p.get('operation_id')}: ({p.get('x')},{p.get('y')}) "
                  f"{p.get('width')}x{p.get('height')}")

        # Verify constraints
        print(f"\n[4] Constraint Verification:")
        violations = []

        # Check boundaries
        for p in placements:
            if p['x'] < 0 or p['y'] < 0:
                violations.append(f"Op {p['operation_id']}: negative coordinates")
            if p['x'] + p.get('width', 0) > problem['chip_width']:
                violations.append(f"Op {p['operation_id']}: exceeds chip width")
            if p['y'] + p.get('height', 0) > problem['chip_height']:
                violations.append(f"Op {p['operation_id']}: exceeds chip height")

        # Check overlaps
        for i, p1 in enumerate(placements):
            for p2 in placements[i+1:]:
                if (p1['x'] < p2['x'] + p2.get('width', 0) and
                    p1['x'] + p1.get('width', 0) > p2['x'] and
                    p1['y'] < p2['y'] + p2.get('height', 0) and
                    p1['y'] + p1.get('height', 0) > p2['y']):
                    violations.append(f"Overlap: Op {p1['operation_id']} and Op {p2['operation_id']}")

        if violations:
            print(f"  [FAIL] Violations found: {len(violations)}")
            for v in violations:
                print(f"    - {v}")
        else:
            print(f"  [OK] All constraints satisfied!")
            print(f"  [OK] 0 violations (boundary + overlap checks passed)")

        # Check if self-verification was performed
        print(f"\n[5] Self-Verification Evidence:")
        if "[ ]" in content or "[x]" in content:
            print(f"  [OK] Checklist format detected (model attempted verification)")
        if "Step 1:" in content or "Step 5:" in content:
            print(f"  [OK] Step-by-step thinking detected")
        if "wirelength" in content.lower():
            print(f"  [OK] Wirelength consideration detected")

        return len(violations) == 0

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_seven_section_placement()
    sys.exit(0 if success else 1)
