"""
Scheduling Agent using LLM for operation scheduling.

Generates valid schedules respecting dependencies and resource constraints.
"""

import json
import re
from typing import List, Dict, Any, Tuple

import sys
sys.path.insert(0, 'src')

from agents.base_agent import BaseAgent, AgentStage, AgentContext
from agents.verifier import ScheduleVerifier
from baseline.problem import DMFBProblem


class SchedulingAgent(BaseAgent):
    """
    Agent for scheduling operations on placed modules.

    Assigns start/end times to operations respecting:
    - Operation dependencies (DAG constraints)
    - Resource availability (modules can't be double-booked)
    - Timing requirements
    """

    def __init__(self, llm_client, max_iterations: int = 5, verbose: bool = True):
        super().__init__(AgentStage.SCHEDULING, llm_client, max_iterations, verbose)
        self.verifier = ScheduleVerifier()

    def generate_prompt(self, context: AgentContext, errors: List[str] = None) -> str:
        """Generate prompt for scheduling."""
        problem = context.problem
        placement = context.placement

        prompt = f"""# DMFB Scheduling Task

## Problem
- Chip: {problem.chip_width}x{problem.chip_height}
- Operations: {len(problem.operations)}
- Available modules: {list(problem.modules.keys())}

## Placement (Fixed)
"""
        if placement:
            for p in placement[:10]:
                prompt += f"- {p['module_id']} at ({p['x']}, {p['y']}), size {p['width']}x{p['height']}\n"
            if len(placement) > 10:
                prompt += f"- ... and {len(placement) - 10} more\n"

        prompt += f"""
## Operations
"""
        for op in problem.operations[:15]:
            deps = f" (depends on: {op.dependencies})" if op.dependencies else ""
            duration = op.get_duration(problem.modules)
            prompt += f"- Op {op.id}: {op.op_type} on {op.module_type}, duration {duration}{deps}\n"

        if len(problem.operations) > 15:
            prompt += f"- ... and {len(problem.operations) - 15} more operations\n"

        if errors:
            prompt += f"""
## Previous Errors
"""
            for error in errors[:5]:
                prompt += f"- {error}\n"

        prompt += """
## Task
Generate a valid schedule assigning start times to each operation:
1. Respect all dependencies (operation starts after predecessors finish)
2. No resource conflicts (same module can't be used simultaneously)
3. Minimize total completion time (makespan)

## Output Format
```json
[
  {"operation_id": 0, "start_time": 0, "end_time": 3, "module_id": "mixer_0"},
  {"operation_id": 1, "start_time": 3, "end_time": 7, "module_id": "heater_0"},
  ...
]
```

Use the module_id from the provided placement.
"""
        return prompt

    def parse_response(self, response: str, context: AgentContext) -> List[Dict]:
        """Extract JSON schedule from LLM response."""
        patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'(\[\s*{.*?}\s*\])',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                try:
                    schedule = json.loads(match.strip())
                    if isinstance(schedule, list):
                        return schedule
                except json.JSONDecodeError:
                    continue

        raise ValueError("Could not parse schedule JSON from response")

    def verify_solution(self, solution: List[Dict], context: AgentContext) -> Tuple[bool, List[str]]:
        """Verify schedule using ScheduleVerifier."""
        result = self.verifier.verify(context.problem, {"schedule": solution})

        if result.is_valid:
            return True, []

        errors = [f"{v.violation_type.value}: {v.message}" for v in result.violations]
        return False, errors

    def get_system_prompt(self) -> str:
        """System prompt for scheduling agent."""
        return """You are a DMFB scheduling optimization expert.

Your task is to assign execution times to operations on a digital microfluidic biochip.

Key considerations:
1. Dependencies: An operation can only start after all its predecessors complete
2. Resources: Each module can only execute one operation at a time
3. Critical path: Identify the longest path to minimize total time
4. Parallelism: Execute independent operations concurrently when resources allow

Start with operations that have no dependencies, then schedule their successors.
Minimize idle time while respecting all constraints.
"""
