"""
Placement Agent using LLM for module positioning.

Generates non-overlapping, valid placements for DMFB modules.
"""

import json
import re
from typing import List, Dict, Any, Tuple

import sys
sys.path.insert(0, 'src')

from agents.base_agent import BaseAgent, AgentStage, AgentContext, AgentResult
from agents.verifier import PlacementVerifier, ViolationType
from baseline.problem import DMFBProblem, Module


class PlacementAgent(BaseAgent):
    """
    Agent for placing modules on the DMFB chip.

    Uses LLM to generate positions for all required modules.
    Validates with PlacementVerifier and repairs if needed.
    """

    def __init__(self, llm_client, max_iterations: int = 5, verbose: bool = True):
        super().__init__(AgentStage.PLACEMENT, llm_client, max_iterations, verbose)
        self.verifier = PlacementVerifier()

    def generate_prompt(self, context: AgentContext, errors: List[str] = None) -> str:
        """Generate prompt for placement."""
        problem = context.problem

        # Count required modules
        module_counts = {}
        for op in problem.operations:
            mt = op.module_type
            module_counts[mt] = module_counts.get(mt, 0) + 1

        # Build prompt
        prompt = f"""# DMFB Placement Task

## Chip Specifications
- Grid size: {problem.chip_width} x {problem.chip_height} electrodes
- Total area: {problem.chip_width * problem.chip_height} cells

## Required Modules
"""
        for module_type, count in module_counts.items():
            module = problem.modules.get(module_type)
            if module:
                prompt += f"- {module_type}: {count} instance(s), size {module.width}x{module.height}\n"

        prompt += f"""
## Operations
Total operations: {len(problem.operations)}
"""

        # Show dependencies
        for op in problem.operations[:10]:  # Limit to first 10 for brevity
            deps = f" (depends on: {op.dependencies})" if op.dependencies else ""
            prompt += f"- Op {op.id}: {op.op_type} using {op.module_type}{deps}\n"

        if len(problem.operations) > 10:
            prompt += f"- ... and {len(problem.operations) - 10} more operations\n"

        if errors:
            prompt += f"""
## Previous Attempt Errors
The previous placement had these errors:
"""
            for error in errors[:5]:  # Show first 5 errors
                prompt += f"- {error}\n"

            prompt += """
Please fix these errors and generate a corrected placement.
"""

        prompt += """
## Task
Generate a valid placement where:
1. No modules overlap
2. All modules fit within the chip boundaries
3. Modules that are used by dependent operations are placed close together

## Output Format
Provide your reasoning first, then output the placement as JSON:

```json
[
  {"module_id": "mixer_0", "x": 0, "y": 0, "width": 2, "height": 2},
  {"module_id": "mixer_1", "x": 3, "y": 0, "width": 2, "height": 2},
  ...
]
```

Use unique module_ids (e.g., mixer_0, mixer_1 for multiple mixers).
Place frequently interacting modules near each other.
"""
        return prompt

    def parse_response(self, response: str, context: AgentContext) -> List[Dict]:
        """Extract JSON placement from LLM response."""
        # Try to find JSON block
        patterns = [
            r'```json\s*(.*?)\s*```',  # Markdown JSON block
            r'```\s*(.*?)\s*```',      # Any markdown block
            r'(\[\s*{.*?}\s*\])',       # Raw JSON array
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                try:
                    placements = json.loads(match.strip())
                    if isinstance(placements, list):
                        return placements
                except json.JSONDecodeError:
                    continue

        # Fallback: try to parse entire response as JSON
        try:
            placements = json.loads(response.strip())
            if isinstance(placements, list):
                return placements
        except:
            pass

        raise ValueError("Could not parse placement JSON from response")

    def verify_solution(self, solution: List[Dict], context: AgentContext) -> Tuple[bool, List[str]]:
        """Verify placement using PlacementVerifier."""
        result = self.verifier.verify(context.problem, {"placements": solution})

        if result.is_valid:
            return True, []

        errors = []
        for v in result.violations:
            errors.append(f"{v.violation_type.value}: {v.message}")
            if v.suggested_fix:
                errors.append(f"  Suggestion: {v.suggested_fix}")

        return False, errors

    def get_system_prompt(self) -> str:
        """System prompt for placement agent."""
        return """You are a DMFB placement optimization expert.

Your task is to position functional modules on a digital microfluidic biochip.

Key considerations:
1. No overlap: Modules cannot share the same space
2. Boundaries: Modules must fit entirely within the chip
3. Proximity: Modules used by dependent operations should be close
4. Path planning: Leave space for droplet routing between modules

Place modules starting from top-left (0,0), expanding right and down.
Group related modules together to minimize routing distances.
"""


if __name__ == "__main__":
    # Test the agent
    from llm import LLMClient
    import os

    print("Testing Placement Agent...")

    # Create a simple test problem
    from baseline.problem import Operation, Module, ModuleType

    modules = {
        "mixer_2x2": Module("mixer_2x2", ModuleType.MIXER, 2, 2, 3),
        "heater_1x1": Module("heater_1x1", ModuleType.HEATER, 1, 1, 4),
    }

    operations = [
        Operation(id=0, op_type="mix", module_type="mixer_2x2"),
        Operation(id=1, op_type="heat", module_type="heater_1x1", dependencies=[0]),
    ]

    problem = DMFBProblem(
        name="test",
        chip_width=10,
        chip_height=10,
        modules=modules,
        operations=operations
    )

    # Create agent (will fail without API key, but shows structure)
    try:
        client = LLMClient.from_kimi(os.getenv("KIMI_API_KEY", "dummy"))
        agent = PlacementAgent(client, verbose=True)

        context = AgentContext(problem=problem)
        prompt = agent.generate_prompt(context)

        print("\nGenerated prompt (first 1000 chars):")
        print(prompt[:1000])
        print("...")

    except Exception as e:
        print(f"Setup error (expected without API key): {e}")
