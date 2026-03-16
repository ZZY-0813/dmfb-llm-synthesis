"""Placement Agent prompt template.

Optimizes module positioning on DMFB chip to minimize wirelength
while avoiding overlaps and respecting chip boundaries.
"""

from typing import Dict, Any, List
import json

from .base import BasePromptTemplate, Example


class PlacementPrompt(BasePromptTemplate):
    """Prompt template for Placement Agent.

    Optimizes:
    1. Module positions (x, y) on chip
    2. Minimizes total wirelength (sum of Manhattan distances)
    3. Avoids module overlaps
    4. Respects chip boundaries
    """

    TASK_NAME = "placement"
    TASK_DESCRIPTION = "module placement on DMFB chip"

    SYSTEM_PROMPT = """You are an expert DMFB (Digital Microfluidic Biochip) placement optimizer.
Your goal is to position modules on the chip to minimize total wirelength while ensuring:
- No overlapping modules
- All modules within chip boundaries
- Optimal use of chip area

Wirelength = sum of Manhattan distances between connected modules.
"""

    def _format_problem(self, problem: Dict[str, Any]) -> str:
        """Format placement problem."""
        lines = [
            f"Chip Size: {problem.get('chip_width', '?')} x {problem.get('chip_height', '?')}",
            f"Operations: {len(problem.get('operations', []))}",
            "",
            "Module Library:"
        ]

        # Format modules
        modules = problem.get('modules', {})
        for name, mod in modules.items():
            width = mod.get('width', mod.get('w', '?'))
            height = mod.get('height', mod.get('h', '?'))
            lines.append(f"  - {name}: {width}x{height}")

        lines.extend(["", "Operations (with dependencies):"])

        # Format operations
        for op in problem.get('operations', []):
            op_id = op.get('id', op.get('name', '?'))
            op_type = op.get('op_type', op.get('type', '?'))
            module = op.get('module_type', '?')
            deps = op.get('dependencies', [])

            dep_str = f" -> depends on {deps}" if deps else ""
            lines.append(f"  - {op_id}: {op_type} using {module}{dep_str}")

        return "\n".join(lines)

    def _get_task_instructions(self) -> str:
        """Get placement instructions."""
        return """Place each operation's module on the chip.

Optimization Objectives (in priority order):
1. Valid placement: No overlaps, within boundaries
2. Minimize wirelength: Place connected modules close together
3. Compact layout: Minimize bounding box area

Rules:
- Each module must be fully within chip boundaries
- Modules cannot overlap (no shared cells)
- Position is (x, y) of top-left corner
- Coordinate system: (0,0) at top-left, x right, y down
"""

    def _get_output_format(self) -> str:
        """Get placement output format."""
        schema = {
            "type": "object",
            "properties": {
                "placements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "operation_id": {
                                "type": "integer",
                                "description": "Operation ID"
                            },
                            "module_type": {
                                "type": "string",
                                "description": "Module type/name"
                            },
                            "x": {
                                "type": "integer",
                                "description": "X coordinate (top-left)"
                            },
                            "y": {
                                "type": "integer",
                                "description": "Y coordinate (top-left)"
                            },
                            "width": {
                                "type": "integer",
                                "description": "Module width"
                            },
                            "height": {
                                "type": "integer",
                                "description": "Module height"
                            }
                        },
                        "required": ["operation_id", "x", "y"]
                    }
                },
                "metrics": {
                    "type": "object",
                    "properties": {
                        "estimated_wirelength": {
                            "type": "number",
                            "description": "Total Manhattan wirelength estimate"
                        },
                        "bounding_box_area": {
                            "type": "number",
                            "description": "Area of bounding box enclosing all modules"
                        }
                    }
                }
            },
            "required": ["placements"]
        }

        example = {
            "placements": [
                {
                    "operation_id": 0,
                    "module_type": "mixer_2x2",
                    "x": 0,
                    "y": 0,
                    "width": 2,
                    "height": 2
                },
                {
                    "operation_id": 1,
                    "module_type": "detector_1x2",
                    "x": 4,
                    "y": 0,
                    "width": 1,
                    "height": 2
                }
            ],
            "metrics": {
                "estimated_wirelength": 10,
                "bounding_box_area": 24
            }
        }

        return f"""Return a JSON object with this schema:
```json
{json.dumps(schema, indent=2)}
```

Example output:
```json
{json.dumps(example, indent=2)}
```"""

    def create_example(self,
                       problem: Dict[str, Any],
                       placements: List[Dict],
                       explanation: str = None) -> Example:
        """Create a few-shot example for placement.

        Args:
            problem: Problem description
            placements: Solution placements
            explanation: Optional explanation

        Returns:
            Example object
        """
        problem_desc = self._format_problem(problem)
        output = json.dumps({
            "placements": placements,
            "metrics": self._calculate_metrics(problem, placements)
        }, indent=2)

        return Example(
            input=problem_desc,
            output=output,
            explanation=explanation or self._generate_explanation(problem, placements)
        )

    def _calculate_metrics(self,
                          problem: Dict[str, Any],
                          placements: List[Dict]) -> Dict[str, float]:
        """Calculate placement metrics for example."""
        # Simple wirelength estimation
        wirelength = 0.0
        op_positions = {p['operation_id']: (p['x'], p['y']) for p in placements}

        for op in problem.get('operations', []):
            op_id = op.get('id')
            if op_id not in op_positions:
                continue
            x1, y1 = op_positions[op_id]

            for dep_id in op.get('dependencies', []):
                if dep_id in op_positions:
                    x2, y2 = op_positions[dep_id]
                    wirelength += abs(x1 - x2) + abs(y1 - y2)

        # Bounding box area
        if placements:
            min_x = min(p['x'] for p in placements)
            max_x = max(p['x'] + p.get('width', 1) for p in placements)
            min_y = min(p['y'] for p in placements)
            max_y = max(p['y'] + p.get('height', 1) for p in placements)
            area = (max_x - min_x) * (max_y - min_y)
        else:
            area = 0

        return {
            "estimated_wirelength": wirelength,
            "bounding_box_area": area
        }

    def _generate_explanation(self,
                             problem: Dict[str, Any],
                             placements: List[Dict]) -> str:
        """Generate explanation for example solution."""
        return f"Placed {len(placements)} modules minimizing wirelength between dependent operations."
