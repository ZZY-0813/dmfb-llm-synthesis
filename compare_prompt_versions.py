"""Compare original vs seven-section prompt engineering performance."""

import sys
import time
sys.path.insert(0, 'src')

from agents.prompts import PlacementPrompt
from agents.verifier import PlacementVerifier
from llm.client import LLMClient
import json

# Test problem set
test_problems = [
    {
        "name": "Simple (3 ops)",
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
    },
    {
        "name": "Medium (4 ops)",
        "chip_width": 15,
        "chip_height": 15,
        "operations": [
            {"id": 0, "op_type": "mix", "module_type": "mixer_2x2", "dependencies": []},
            {"id": 1, "op_type": "mix", "module_type": "mixer_2x2", "dependencies": [0]},
            {"id": 2, "op_type": "detect", "module_type": "detector_1x2", "dependencies": [0]},
            {"id": 3, "op_type": "heat", "module_type": "heater_2x2", "dependencies": [1, 2]}
        ],
        "modules": {
            "mixer_2x2": {"width": 2, "height": 2, "exec_time": 3},
            "detector_1x2": {"width": 1, "height": 2, "exec_time": 2},
            "heater_2x2": {"width": 2, "height": 2, "exec_time": 4}
        }
    }
]

class OriginalPlacementPrompt(PlacementPrompt):
    """Original prompt without seven-section optimization."""

    def generate(self, problem, examples=None, chain_of_thought=None):
        """Original simple prompt."""
        if examples is not None:
            self.examples = examples
        if chain_of_thought is not None:
            self.chain_of_thought = chain_of_thought

        problem_desc = self._format_problem(problem)
        task_instructions = self._get_task_instructions()
        output_format = self._get_output_format()

        prompt = f"""## Problem

{problem_desc}

## Task

{task_instructions}

## Output Format

{output_format}

Generate your solution now:"""

        return prompt

def test_prompt_version(prompt_class, problems, version_name):
    """Test a specific prompt version."""
    print(f"\n{'='*70}")
    print(f"Testing: {version_name}")
    print(f"{'='*70}")

    API_KEY = "sk-SEd9538RQoEuFkuvotMWQRd0hHkuGxfnrQfAuwVMMh86pm7y"
    client = LLMClient.from_kimi(API_KEY)
    verifier = PlacementVerifier()

    results = []

    for problem in problems:
        print(f"\nProblem: {problem['name']}")
        print(f"Operations: {len(problem['operations'])}")

        # Generate prompt
        template = prompt_class()
        prompt = template.generate(problem, chain_of_thought=True)

        print(f"Prompt length: {len(prompt)} chars")

        # Call LLM
        start_time = time.time()
        try:
            response = client.chat(
                prompt=prompt,
                system_prompt=template.get_system_prompt(),
                temperature=0.3,
                max_tokens=2000
            )
            duration = time.time() - start_time

            # Parse solution
            content = response.content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content

            solution = json.loads(json_str)

            # Verify
            result = verifier.verify(problem, solution)

            # Metrics
            violations = len(result.violations)
            placements = len(solution.get('placements', []))

            # Calculate wirelength
            wirelength = 0
            op_positions = {p['operation_id']: (p['x'], p['y'])
                          for p in solution.get('placements', [])}
            for op in problem['operations']:
                op_id = op.get('id')
                if op_id not in op_positions:
                    continue
                x1, y1 = op_positions[op_id]
                for dep_id in op.get('dependencies', []):
                    if dep_id in op_positions:
                        x2, y2 = op_positions[dep_id]
                        wirelength += abs(x1 - x2) + abs(y1 - y2)

            success = violations == 0

            print(f"  Result: {'SUCCESS' if success else 'FAIL'}")
            print(f"  Duration: {duration:.2f}s")
            print(f"  Violations: {violations}")
            print(f"  Placements: {placements}")
            print(f"  Wirelength: {wirelength}")

            results.append({
                'problem': problem['name'],
                'success': success,
                'duration': duration,
                'violations': violations,
                'wirelength': wirelength,
                'tokens': len(content)
            })

        except Exception as e:
            print(f"  [ERROR] {e}")
            results.append({
                'problem': problem['name'],
                'success': False,
                'error': str(e)
            })

    return results

def main():
    print("="*70)
    print("Prompt Engineering Comparison: Original vs Seven-Section")
    print("="*70)

    # Test original version
    original_results = test_prompt_version(
        OriginalPlacementPrompt,
        test_problems,
        "Original Prompt"
    )

    # Test seven-section version
    seven_section_results = test_prompt_version(
        PlacementPrompt,
        test_problems,
        "Seven-Section Prompt"
    )

    # Summary
    print(f"\n{'='*70}")
    print("COMPARISON SUMMARY")
    print(f"{'='*70}")

    print("\nOriginal Prompt:")
    orig_success = sum(1 for r in original_results if r.get('success', False))
    orig_violations = sum(r.get('violations', 0) for r in original_results)
    orig_time = sum(r.get('duration', 0) for r in original_results)
    print(f"  Success Rate: {orig_success}/{len(original_results)}")
    print(f"  Total Violations: {orig_violations}")
    print(f"  Avg Time: {orig_time/len(original_results):.2f}s")

    print("\nSeven-Section Prompt:")
    seven_success = sum(1 for r in seven_section_results if r.get('success', False))
    seven_violations = sum(r.get('violations', 0) for r in seven_section_results)
    seven_time = sum(r.get('duration', 0) for r in seven_section_results)
    print(f"  Success Rate: {seven_success}/{len(seven_section_results)}")
    print(f"  Total Violations: {seven_violations}")
    print(f"  Avg Time: {seven_time/len(seven_section_results):.2f}s")

    print("\nImprovement:")
    success_improvement = (seven_success - orig_success) / len(original_results) * 100
    violation_reduction = orig_violations - seven_violations
    print(f"  Success Rate: {success_improvement:+.0f}%")
    print(f"  Violations Reduced: {violation_reduction}")
    print(f"  Time Change: {seven_time - orig_time:+.2f}s")

    print(f"\n{'='*70}")

if __name__ == "__main__":
    main()
