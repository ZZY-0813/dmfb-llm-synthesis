"""Scheduling Agent prompt template.

Optimizes operation execution order to minimize makespan
while respecting dependencies and resource constraints.
"""

from typing import Dict, Any, List
import json

from .base import BasePromptTemplate, Example


class SchedulingPrompt(BasePromptTemplate):
    """Prompt template for Scheduling Agent.

    Optimizes:
    1. Operation start times
    2. Minimizes makespan (total completion time)
    3. Respects dependency constraints
    4. Handles resource conflicts (module availability)
    """

    TASK_NAME = "scheduling"
    TASK_DESCRIPTION = "operation scheduling on DMFB"

    SYSTEM_PROMPT = """You are an expert DMFB (Digital Microfluidic Biochip) scheduling optimizer.
Your goal is to schedule operations to minimize makespan (total completion time) while ensuring:
- All dependencies are satisfied (operation starts after predecessors finish)
- Resource constraints respected (modules not double-booked)
- Efficient parallelism (independent operations can overlap)
"""

    def _format_problem(self, problem: Dict[str, Any]) -> str:
        """Format scheduling problem."""
        lines = [
            f"Chip Size: {problem.get('chip_width', '?')} x {problem.get('chip_height', '?')}",
            f"Operations: {len(problem.get('operations', []))}",
            "",
            "Modules (with execution times):"
        ]

        # Format modules
        modules = problem.get('modules', {})
        for name, mod in modules.items():
            exec_time = mod.get('exec_time', mod.get('duration', '?'))
            width = mod.get('width', '?')
            height = mod.get('height', '?')
            lines.append(f"  - {name}: {width}x{height}, exec_time={exec_time}")

        lines.extend(["", "Operations (with dependencies):"])

        # Format operations with dependencies
        for op in problem.get('operations', []):
            op_id = op.get('id', op.get('name', '?'))
            op_type = op.get('op_type', op.get('type', '?'))
            module = op.get('module_type', '?')
            deps = op.get('dependencies', [])

            # Get duration from module
            mod_info = modules.get(module, {})
            duration = mod_info.get('exec_time', mod_info.get('duration', '?'))

            dep_str = f" -> depends on {deps}" if deps else ""
            lines.append(f"  - {op_id}: {op_type} using {module} (duration={duration}){dep_str}")

        return "\n".join(lines)

    def _get_task_instructions(self) -> str:
        """Get scheduling instructions."""
        return """Schedule each operation with start and end times.

Optimization Objectives (in priority order):
1. Valid schedule: Respect all dependencies
2. Minimize makespan: Finish all operations as soon as possible
3. Resource efficiency: Maximize module utilization

Rules:
- Operation cannot start before all dependencies finish
- Each module can only execute one operation at a time
- Operations are non-preemptive (once started, must complete)
- Independent operations can execute in parallel on different modules
- Minimize idle time while respecting constraints

Scheduling Strategy:
- Use ASAP (As Soon As Possible) for critical path operations
- Use ALAP (As Late As Possible) for non-critical operations to reduce resource pressure
- Balance parallelism with resource constraints
"""

    def _get_output_format(self) -> str:
        """Get scheduling output format."""
        schema = {
            "type": "object",
            "properties": {
                "schedule": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "operation_id": {
                                "type": "integer",
                                "description": "Operation ID"
                            },
                            "start_time": {
                                "type": "integer",
                                "description": "Start time step"
                            },
                            "end_time": {
                                "type": "integer",
                                "description": "End time step"
                            },
                            "module_id": {
                                "type": "string",
                                "description": "Assigned module"
                            }
                        },
                        "required": ["operation_id", "start_time", "end_time", "module_id"]
                    }
                },
                "makespan": {
                    "type": "integer",
                    "description": "Total completion time (max end_time)"
                },
                "critical_path": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of operation IDs on critical path"
                }
            },
            "required": ["schedule", "makespan"]
        }

        example = {
            "schedule": [
                {
                    "operation_id": 0,
                    "start_time": 0,
                    "end_time": 3,
                    "module_id": "mixer_2x2"
                },
                {
                    "operation_id": 1,
                    "start_time": 3,
                    "end_time": 5,
                    "module_id": "detector_1x2"
                },
                {
                    "operation_id": 2,
                    "start_time": 0,
                    "end_time": 4,
                    "module_id": "heater_2x2"
                }
            ],
            "makespan": 5,
            "critical_path": [0, 1]
        }

        return f"""Return a JSON object with this schema:
```json
{json.dumps(schema, indent=2)}
```

Example output:
```json
{json.dumps(example, indent=2)}
```

Note: Times are integer time steps. Operations can overlap if on different modules and independent."""

    def create_example(self,
                       problem: Dict[str, Any],
                       schedule: List[Dict],
                       makespan: int,
                       explanation: str = None) -> Example:
        """Create a few-shot example for scheduling."""
        problem_desc = self._format_problem(problem)

        # Calculate critical path
        critical_path = self._calculate_critical_path(problem, schedule)

        output = json.dumps({
            "schedule": schedule,
            "makespan": makespan,
            "critical_path": critical_path
        }, indent=2)

        return Example(
            input=problem_desc,
            output=output,
            explanation=explanation or f"Schedule achieves makespan {makespan} with {len(schedule)} operations."
        )

    def _calculate_critical_path(self,
                                problem: Dict[str, Any],
                                schedule: List[Dict]) -> List[int]:
        """Calculate critical path for example."""
        # Build schedule lookup
        sched_dict = {s['operation_id']: s for s in schedule}

        # Calculate longest path
        memo = {}

        def longest_path(op_id):
            if op_id in memo:
                return memo[op_id]

            op = next((o for o in problem.get('operations', [])
                      if o.get('id') == op_id), None)
            if not op:
                return 0, [op_id]

            deps = op.get('dependencies', [])
            if not deps:
                duration = sched_dict.get(op_id, {}).get('end_time', 0) - \
                          sched_dict.get(op_id, {}).get('start_time', 0)
                memo[op_id] = (duration, [op_id])
                return memo[op_id]

            max_len = 0
            max_path = []
            for dep_id in deps:
                length, path = longest_path(dep_id)
                if length > max_len:
                    max_len = length
                    max_path = path

            duration = sched_dict.get(op_id, {}).get('end_time', 0) - \
                      sched_dict.get(op_id, {}).get('start_time', 0)
            memo[op_id] = (max_len + duration, max_path + [op_id])
            return memo[op_id]

        # Find longest path
        max_length = 0
        critical_path = []
        for op in problem.get('operations', []):
            op_id = op.get('id')
            length, path = longest_path(op_id)
            if length > max_length:
                max_length = length
                critical_path = path

        return critical_path