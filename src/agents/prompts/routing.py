"""Routing Agent prompt template.

Plans droplet paths through time and space to avoid collisions
and minimize routing time.
"""

from typing import Dict, Any, List
import json

from .base import BasePromptTemplate, Example


class RoutingPrompt(BasePromptTemplate):
    """Prompt template for Routing Agent.

    Optimizes:
    1. Droplet paths (x, y, t) from source to destination
    2. Avoids droplet collisions (2x2 exclusion rule)
    3. Minimizes routing time
    4. Respects timing constraints from schedule
    """

    TASK_NAME = "routing"
    TASK_DESCRIPTION = "droplet routing on DMFB"

    SYSTEM_PROMPT = """You are an expert DMFB (Digital Microfluidic Biochip) routing optimizer.
Your goal is to plan droplet paths through space and time to avoid collisions while minimizing routing time.

Fluid Constraints:
- Two droplets cannot occupy the same cell at the same time
- Two droplets must maintain 2-cell Manhattan distance (electrode interference)
- Droplets can move to adjacent cells (up, down, left, right) or stay

Path Representation:
- List of (x, y, t) positions from start to destination
- t=0 is droplet creation time
- Path must be continuous (adjacent positions in consecutive timesteps)
"""

    def _format_problem(self, problem: Dict[str, Any]) -> str:
        """Format routing problem."""
        lines = [
            f"Chip Size: {problem.get('chip_width', '?')} x {problem.get('chip_height', '?')}",
            f"Operations: {len(problem.get('operations', []))}",
        ]

        # Add placement if available
        placements = problem.get('placements', [])
        if placements:
            lines.extend(["", "Module Placements (from placement step):"])
            for p in placements:
                op_id = p.get('operation_id', '?')
                x, y = p.get('x', '?'), p.get('y', '?')
                w, h = p.get('width', '?'), p.get('height', '?')
                lines.append(f"  - Operation {op_id}: ({x},{y}) size {w}x{h}")

        # Add schedule if available
        schedule = problem.get('schedule', [])
        if schedule:
            lines.extend(["", "Operation Schedule (from scheduling step):"])
            for s in schedule:
                op_id = s.get('operation_id', '?')
                start = s.get('start_time', '?')
                end = s.get('end_time', '?')
                lines.append(f"  - Operation {op_id}: time [{start}, {end}]")

        # Identify droplets that need routing
        lines.extend(["", "Droplets to Route:"])
        operations = problem.get('operations', [])

        for i, op in enumerate(operations):
            op_id = op.get('id', i)
            op_type = op.get('op_type', op.get('type', 'unknown'))

            # Get source and destination
            deps = op.get('dependencies', [])
            if deps:
                # Route from dependency's module to this operation's module
                for dep_id in deps:
                    lines.append(f"  - Droplet {op_id}: from Operation {dep_id} to Operation {op_id} ({op_type})")
            else:
                # Initial droplet, route from dispensing port
                lines.append(f"  - Droplet {op_id}: from DispensePort to Operation {op_id} ({op_type})")

        return "\n".join(lines)

    def _get_task_instructions(self) -> str:
        """Get routing instructions."""
        return """Plan paths for all droplets from sources to destinations.

Optimization Objectives (in priority order):
1. Valid paths: No collisions, maintain 2-cell separation
2. Minimize routing time: Shortest paths, minimal detours
3. Respect timing: Droplets arrive before operation starts

Routing Rules:
- Droplets move on a grid (x, y coordinates)
- Each move is to adjacent cell (up/down/left/right) or stay
- Paths must be continuous (no teleportation)
- Collision avoidance:
  * No two droplets at same (x, y, t)
  * Manhattan distance between droplets >= 2 at all times
- Droplets wait at source if path is blocked

Path Representation:
- Array of (x, y, t) timestamps
- First position: droplet creation location and time
- Last position: droplet destination and arrival time
"""

    def _get_output_format(self) -> str:
        """Get routing output format."""
        schema = {
            "type": "object",
            "properties": {
                "droplet_paths": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "droplet_id": {
                                "type": "string",
                                "description": "Unique droplet identifier"
                            },
                            "operation_id": {
                                "type": "integer",
                                "description": "Target operation ID"
                            },
                            "path": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "x": {"type": "integer"},
                                        "y": {"type": "integer"},
                                        "t": {"type": "integer"}
                                    },
                                    "required": ["x", "y", "t"]
                                },
                                "description": "List of (x, y, t) positions"
                            },
                            "start_time": {"type": "integer"},
                            "end_time": {"type": "integer"},
                            "length": {"type": "integer", "description": "Number of steps"}
                        },
                        "required": ["droplet_id", "operation_id", "path"]
                    }
                },
                "total_routing_time": {
                    "type": "integer",
                    "description": "Maximum end_time across all droplets"
                },
                "collisions_avoided": {
                    "type": "integer",
                    "description": "Number of potential collisions resolved"
                }
            },
            "required": ["droplet_paths", "total_routing_time"]
        }

        example = {
            "droplet_paths": [
                {
                    "droplet_id": "d_0",
                    "operation_id": 0,
                    "path": [
                        {"x": 0, "y": 0, "t": 0},
                        {"x": 1, "y": 0, "t": 1},
                        {"x": 2, "y": 0, "t": 2},
                        {"x": 2, "y": 1, "t": 3}
                    ],
                    "start_time": 0,
                    "end_time": 3,
                    "length": 4
                },
                {
                    "droplet_id": "d_1",
                    "operation_id": 1,
                    "path": [
                        {"x": 5, "y": 5, "t": 0},
                        {"x": 4, "y": 5, "t": 1},
                        {"x": 3, "y": 5, "t": 2}
                    ],
                    "start_time": 0,
                    "end_time": 2,
                    "length": 3
                }
            ],
            "total_routing_time": 3,
            "collisions_avoided": 2
        }

        return f"""Return a JSON object with this schema:
```json
{json.dumps(schema, indent=2)}
```

Example output:
```json
{json.dumps(example, indent=2)}
```

Note: Paths can overlap in space at different times, but not at the same time."""

    def create_example(self,
                       problem: Dict[str, Any],
                       droplet_paths: List[Dict],
                       explanation: str = None) -> Example:
        """Create a few-shot example for routing."""
        problem_desc = self._format_problem(problem)

        # Calculate metrics
        total_time = max(p.get('end_time', 0) for p in droplet_paths) if droplet_paths else 0

        output = json.dumps({
            "droplet_paths": droplet_paths,
            "total_routing_time": total_time,
            "collisions_avoided": len(droplet_paths)  # Simplified
        }, indent=2)

        return Example(
            input=problem_desc,
            output=output,
            explanation=explanation or f"Routed {len(droplet_paths)} droplets in {total_time} time steps with collision avoidance."
        )
