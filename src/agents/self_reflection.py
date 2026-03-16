"""Self-Reflection mechanism for DMFB Agents.

Based on Atelier paper's self-reflection mechanism:
1. Output format validation (JSON schema check)
2. Logic consistency validation (constraint checking)
3. Re-execution strategy (auto-repair on failure)
"""

from typing import Dict, Any, List, Tuple, Optional
import json
import time
from dataclasses import dataclass


@dataclass
class ReflectionResult:
    """Result of self-reflection."""
    is_valid: bool
    errors: List[str]
    suggested_fixes: List[str]
    reflection_time: float


class SelfReflectionMixin:
    """Mixin class adding self-reflection capability to agents."""

    def __init__(self, max_reflection_iterations: int = 3):
        self.max_reflection_iterations = max_reflection_iterations
        self.reflection_stats = {
            'total_reflections': 0,
            'successful_corrections': 0,
            'failed_corrections': 0
        }

    def reflect_and_repair(self,
                          solution: Dict[str, Any],
                          problem: Dict[str, Any],
                          llm_client,
                          prompt_template) -> Tuple[Dict[str, Any], ReflectionResult]:
        """Perform self-reflection and auto-repair if needed.

        Args:
            solution: Generated solution
            problem: Original problem
            llm_client: LLM client for repair
            prompt_template: Prompt template for generating repair prompts

        Returns:
            (repaired_solution, reflection_result)
        """
        start_time = time.time()

        # Step 1: Format validation
        format_errors = self._validate_format(solution)
        if format_errors:
            self.reflection_stats['total_reflections'] += 1
            repair_result = self._attempt_repair(
                solution, problem, format_errors,
                llm_client, prompt_template, error_type="format"
            )
            if repair_result:
                self.reflection_stats['successful_corrections'] += 1
                return repair_result, ReflectionResult(
                    is_valid=True,
                    errors=format_errors,
                    suggested_fixes=["Auto-repaired format errors"],
                    reflection_time=time.time() - start_time
                )
            else:
                self.reflection_stats['failed_corrections'] += 1

        # Step 2: Logic/constraint validation
        logic_errors = self._validate_logic(solution, problem)
        if logic_errors:
            self.reflection_stats['total_reflections'] += 1
            repair_result = self._attempt_repair(
                solution, problem, logic_errors,
                llm_client, prompt_template, error_type="logic"
            )
            if repair_result:
                self.reflection_stats['successful_corrections'] += 1
                return repair_result, ReflectionResult(
                    is_valid=True,
                    errors=logic_errors,
                    suggested_fixes=["Auto-repaired logic errors"],
                    reflection_time=time.time() - start_time
                )
            else:
                self.reflection_stats['failed_corrections'] += 1

        # No errors or repair failed
        reflection_time = time.time() - start_time
        return solution, ReflectionResult(
            is_valid=len(format_errors) == 0 and len(logic_errors) == 0,
            errors=format_errors + logic_errors,
            suggested_fixes=[],
            reflection_time=reflection_time
        )

    def _validate_format(self, solution: Dict[str, Any]) -> List[str]:
        """Validate output format (JSON schema check)."""
        errors = []

        # Check required fields
        if 'placements' not in solution:
            errors.append("Missing required field: 'placements'")
            return errors

        placements = solution.get('placements', [])
        if not isinstance(placements, list):
            errors.append("'placements' must be an array")
            return errors

        # Check each placement
        for i, p in enumerate(placements):
            required_fields = ['operation_id', 'x', 'y']
            for field in required_fields:
                if field not in p:
                    errors.append(f"Placement {i}: missing required field '{field}'")

            # Check coordinate types
            if 'x' in p and not isinstance(p['x'], (int, float)):
                errors.append(f"Placement {i}: 'x' must be a number")
            if 'y' in p and not isinstance(p['y'], (int, float)):
                errors.append(f"Placement {i}: 'y' must be a number")

        return errors

    def _validate_logic(self, solution: Dict[str, Any], problem: Dict[str, Any]) -> List[str]:
        """Validate logic consistency (constraint checking)."""
        errors = []
        placements = solution.get('placements', [])

        chip_width = problem.get('chip_width', 10)
        chip_height = problem.get('chip_height', 10)

        # Check boundary violations
        for p in placements:
            op_id = p.get('operation_id', '?')
            x, y = p.get('x', 0), p.get('y', 0)
            w = p.get('width', 2)
            h = p.get('height', 2)

            if x < 0 or y < 0:
                errors.append(f"Op {op_id}: negative coordinates ({x}, {y})")
            if x + w > chip_width:
                errors.append(f"Op {op_id}: exceeds chip width (x={x}, w={w}, chip={chip_width})")
            if y + h > chip_height:
                errors.append(f"Op {op_id}: exceeds chip height (y={y}, h={h}, chip={chip_height})")

        # Check overlaps
        for i, p1 in enumerate(placements):
            for p2 in placements[i+1:]:
                id1, id2 = p1.get('operation_id'), p2.get('operation_id')
                x1, y1 = p1.get('x', 0), p1.get('y', 0)
                w1, h1 = p1.get('width', 2), p1.get('height', 2)
                x2, y2 = p2.get('x', 0), p2.get('y', 0)
                w2, h2 = p2.get('width', 2), p2.get('height', 2)

                # Check overlap
                if (x1 < x2 + w2 and x1 + w1 > x2 and
                    y1 < y2 + h2 and y1 + h1 > y2):
                    errors.append(f"Overlap detected: Op {id1} and Op {id2}")

        # Check for duplicate operation_ids
        op_ids = [p.get('operation_id') for p in placements]
        if len(op_ids) != len(set(op_ids)):
            errors.append("Duplicate operation_id found in placements")

        return errors

    def _attempt_repair(self,
                       original_solution: Dict[str, Any],
                       problem: Dict[str, Any],
                       errors: List[str],
                       llm_client,
                       prompt_template,
                       error_type: str = "unknown") -> Optional[Dict[str, Any]]:
        """Attempt to repair solution using LLM.

        Args:
            original_solution: The problematic solution
            problem: Original problem specification
            errors: List of identified errors
            llm_client: LLM client
            prompt_template: Prompt template
            error_type: Type of errors (format/logic)

        Returns:
            Repaired solution or None if repair failed
        """
        if not errors:
            return original_solution

        # Build repair prompt
        repair_prompt = self._build_repair_prompt(
            original_solution, problem, errors, error_type
        )

        # Try repair iterations
        for iteration in range(self.max_reflection_iterations):
            try:
                response = llm_client.chat(
                    prompt=repair_prompt,
                    system_prompt=prompt_template.get_system_prompt(),
                    temperature=0.3,
                    max_tokens=2000
                )

                # Parse repaired solution
                content = response.content
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                else:
                    json_str = content

                repaired_solution = json.loads(json_str)

                # Validate repaired solution
                new_format_errors = self._validate_format(repaired_solution)
                new_logic_errors = self._validate_logic(repaired_solution, problem)

                if not new_format_errors and not new_logic_errors:
                    return repaired_solution

                # If still has errors, use as feedback for next iteration
                errors = new_format_errors + new_logic_errors
                repair_prompt = self._build_repair_prompt(
                    repaired_solution, problem, errors, error_type
                )

            except Exception as e:
                print(f"Repair iteration {iteration+1} failed: {e}")
                continue

        # All repair attempts failed
        return None

    def _build_repair_prompt(self,
                            solution: Dict[str, Any],
                            problem: Dict[str, Any],
                            errors: List[str],
                            error_type: str) -> str:
        """Build prompt for repair."""
        prompt = f"""## Self-Reflection: Solution Repair Required

### Original Problem
Chip Size: {problem.get('chip_width')} x {problem.get('chip_height')}
Operations: {len(problem.get('operations', []))}

### Current Solution (HAS ERRORS)
```json
{json.dumps(solution, indent=2)}
```

### Detected Errors ({error_type})
"""
        for i, error in enumerate(errors, 1):
            prompt += f"{i}. {error}\n"

        prompt += """
### Repair Instructions
Please fix ALL the errors above and provide a corrected solution.

Requirements:
1. Address each specific error listed
2. Maintain the same overall approach if valid
3. Verify all constraints (boundaries, no overlaps)
4. Return complete valid JSON

### Output Format
Return corrected JSON solution only, with no additional explanation.
"""

        return prompt

    def get_reflection_stats(self) -> Dict[str, Any]:
        """Get reflection statistics."""
        return self.reflection_stats.copy()


def demonstrate_self_reflection():
    """Demonstrate self-reflection mechanism."""
    print("="*70)
    print("Self-Reflection Mechanism Demonstration")
    print("="*70)

    # Example problematic solution
    problem = {
        "chip_width": 10,
        "chip_height": 10,
        "operations": [
            {"id": 0, "op_type": "mix", "module_type": "mixer_2x2", "dependencies": []},
            {"id": 1, "op_type": "detect", "module_type": "detector_1x2", "dependencies": [0]}
        ]
    }

    # Valid solution
    valid_solution = {
        "placements": [
            {"operation_id": 0, "x": 0, "y": 0, "width": 2, "height": 2},
            {"operation_id": 1, "x": 4, "y": 0, "width": 1, "height": 2}
        ]
    }

    # Invalid solution (overlap)
    invalid_solution = {
        "placements": [
            {"operation_id": 0, "x": 0, "y": 0, "width": 2, "height": 2},
            {"operation_id": 1, "x": 1, "y": 1, "width": 2, "height": 2}  # Overlap!
        ]
    }

    reflection = SelfReflectionMixin()

    # Test valid solution
    print("\n1. Testing valid solution...")
    errors = reflection._validate_logic(valid_solution, problem)
    print(f"   Errors found: {len(errors)}")
    if errors:
        for e in errors:
            print(f"   - {e}")

    # Test invalid solution
    print("\n2. Testing invalid solution (with overlap)...")
    errors = reflection._validate_logic(invalid_solution, problem)
    print(f"   Errors found: {len(errors)}")
    for e in errors:
        print(f"   - {e}")

    print("\n3. Reflection stats:", reflection.get_reflection_stats())


if __name__ == "__main__":
    demonstrate_self_reflection()
