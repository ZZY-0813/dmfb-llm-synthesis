"""
Routing Agent using LLM for droplet path planning.

Generates collision-free paths for droplets moving between modules.
"""

import json
import re
from typing import List, Dict, Any, Tuple

import sys
sys.path.insert(0, 'src')

from agents.base_agent import BaseAgent, AgentStage, AgentContext
from agents.verifier import RoutingVerifier
from baseline.problem import DMFBProblem


class RoutingAgent(BaseAgent):
    """
    Agent for routing droplets on the DMFB grid.

    Generates paths for droplets moving between:
    - Dispenser to module
    - Module to module
    - Module to waste

    Ensures no collisions at any time step.
    """

    def __init__(self, llm_client, max_iterations: int = 5, verbose: bool = True):
        super().__init__(AgentStage.ROUTING, llm_client, max_iterations, verbose)
        self.verifier = RoutingVerifier()

    def generate_prompt(self, context: AgentContext, errors: List[str] = None) -> str:
        """Generate prompt for routing."""
        problem = context.problem
        placement = context.placement
        schedule = context.schedule

        prompt = f"""# DMFB Routing Task

## Problem
- Chip: {problem.chip_width}x{problem.chip_height}
- Operations: {len(problem.operations)}

## Module Positions
"""
        if placement:
            for p in placement:
                cx = p['x'] + p['width'] // 2
                cy = p['y'] + p['height'] // 2
                prompt += f"- {p['module_id']}: ({p['x']},{p['y']}) to ({p['x']+p['width']},{p['y']+p['height']}), center ({cx},{cy})\n"

        if schedule:
            prompt += f"""
## Schedule
"""
            for s in schedule[:10]:
                prompt += f"- Op {s['operation_id']}: t={s['start_time']}-{s['end_time']} on {s['module_id']}\n"

        prompt += f"""
## Droplets to Route
Each droplet needs a path from start to destination:
"""
        # Generate droplet requirements based on operations
        droplets = self._extract_droplet_requirements(context)
        for i, d in enumerate(droplets):
            prompt += f"- Droplet {i}: ({d['start']}) -> ({d['end']}), start at t={d['start_time']}\n"

        if errors:
            prompt += f"""
## Previous Errors
"""
            for error in errors[:5]:
                prompt += f"- {error}\n"

        prompt += """
## Task
Generate collision-free paths for all droplets:
1. Each path is a sequence of (time, x, y) positions
2. Droplets cannot occupy the same cell at the same time
3. Droplets can only move to adjacent cells (including diagonals) or stay
4. Paths must reach their destinations

## Output Format
```json
[
  {
    "droplet_id": "d0",
    "path": [[0, 1, 1], [1, 2, 1], [2, 3, 1], [3, 3, 2]]
  },
  ...
]
```

Each path point is [time, x, y]. Time must start at 0 for each droplet and be continuous.
"""
        return prompt

    def _extract_droplet_requirements(self, context: AgentContext) -> List[Dict]:
        """Extract droplet movement requirements from schedule and placement."""
        # Simplified: create droplets based on operations
        droplets = []

        if not context.placement or not context.schedule:
            return droplets

        # Map module_id to position
        module_pos = {}
        for p in context.placement:
            cx = p['x'] + p['width'] // 2
            cy = p['y'] + p['height'] // 2
            module_pos[p['module_id']] = (cx, cy)

        # Create droplets for each operation
        for s in context.schedule[:5]:  # Limit for demo
            module_id = s.get('module_id', 'unknown')
            if module_id in module_pos:
                pos = module_pos[module_id]
                start_time = s['start_time']
                droplets.append({
                    'start': (0, 0),  # Assume dispenser at (0,0)
                    'end': pos,
                    'start_time': max(0, start_time - 5)
                })

        return droplets

    def parse_response(self, response: str, context: AgentContext) -> List[Dict]:
        """Extract JSON routes from LLM response."""
        patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'(\[\s*{.*?}\s*\])',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                try:
                    routes = json.loads(match.strip())
                    if isinstance(routes, list):
                        return routes
                except json.JSONDecodeError:
                    continue

        raise ValueError("Could not parse routes JSON from response")

    def verify_solution(self, solution: List[Dict], context: AgentContext) -> Tuple[bool, List[str]]:
        """Verify routes using RoutingVerifier."""
        result = self.verifier.verify(context.problem, {"routes": solution})

        if result.is_valid:
            return True, []

        errors = [f"{v.violation_type.value}: {v.message}" for v in result.violations]
        return False, errors

    def get_system_prompt(self) -> str:
        """System prompt for routing agent."""
        return """You are a DMFB routing optimization expert.

Your task is to plan collision-free paths for droplets moving on a digital microfluidic biochip.

Key considerations:
1. Collision avoidance: Two droplets cannot be at the same position at the same time
2. Movement: Droplets can move to adjacent cells or stay in place
3. Timing: Paths must align with operation schedule
4. Efficiency: Minimize total routing time and distance

Plan paths sequentially, avoiding conflicts with already-planned droplets.
Use waiting (staying in place) to resolve timing conflicts.
"""
