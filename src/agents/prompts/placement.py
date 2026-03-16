"""Placement Agent prompt template.

Optimizes module positioning on DMFB chip to minimize wirelength
while avoiding overlaps and respecting chip boundaries.
"""

from typing import Dict, Any, List, Optional
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

    def generate(self,
                 problem: Dict[str, Any],
                 examples: Optional[List[Example]] = None,
                 chain_of_thought: Optional[bool] = None) -> str:
        """Generate complete prompt using seven-section engineering.

        Based on LayoutCopilot paper's seven-section prompt engineering:
        1. Role Definition, 2. Workflow Context, 3. Problem Description,
        4. Task Instructions, 5. Self-Verification, 6. Output Format,
        7. Examples (optional)
        """
        if examples is not None:
            self.examples = examples
        if chain_of_thought is not None:
            self.chain_of_thought = chain_of_thought

        # Build seven sections
        sections = {
            'role_definition': self._get_section1_role(),
            'workflow_context': self._get_section2_workflow(),
            'problem_description': self._format_problem(problem),
            'task_instructions': self._get_section4_task_cot(),
            'self_verification': self._get_section5_verification(),
            'output_format': self._get_section6_output(),
            'examples_section': self._build_examples_section() if self.examples else ""
        }

        # Assemble seven-section prompt
        prompt = f"""## Section 1: Role Definition
{sections['role_definition']}

## Section 2: Workflow Context
{sections['workflow_context']}

## Section 3: Problem Description
{sections['problem_description']}

## Section 4: Task Instructions with Chain-of-Thought
{sections['task_instructions']}

## Section 5: Self-Verification Checklist
{sections['self_verification']}

## Section 6: Output Format & Interaction Guide
{sections['output_format']}

{sections['examples_section']}

## Section 7: Generate Solution
Think step by step following the instructions above, then provide your final solution."""

        return prompt

    def _get_section1_role(self) -> str:
        """Section 1: Role Definition - Professional identity and expertise."""
        return """You are an expert DMFB (Digital Microfluidic Biochip) Placement Optimizer with the following expertise:
- 10+ years of experience in microfluidic chip layout design
- Deep knowledge of electrode array optimization
- Expert in Manhattan distance minimization for droplet routing
- Specialist in constraint satisfaction problems (CSP)

Your decisions are based on:
1. Physical constraints (chip boundaries, module sizes)
2. Electrical constraints (electrode interference)
3. Optimization objectives (wirelength, area utilization)
4. Design best practices (spacing, accessibility)"""

    def _get_section2_workflow(self) -> str:
        """Section 2: Workflow Context - Position in pipeline and impact."""
        return """This is STAGE 1 of 3 in the DMFB synthesis pipeline:
Placement → Scheduling → Routing

Your output directly impacts:
- Stage 2 (Scheduling): Module positions determine operation parallelism
- Stage 3 (Routing): Layout quality affects droplet path complexity
- Final Design: 60% of total chip performance depends on good placement

Pipeline Context:
- Input: Problem specification (operations, dependencies, modules)
- Your Task: Generate valid, optimized module positions
- Output: JSON with placements and metrics
- Next Stage: Scheduling will use your placements to assign operation times"""

    def _get_section4_task_cot(self) -> str:
        """Section 4: Task Instructions with explicit Chain-of-Thought."""
        return """Follow this step-by-step process to generate the placement:

**Step 1: Constraint Analysis**
- Identify all module dimensions and chip boundaries
- List all dependencies between operations
- Calculate minimum required area

**Step 2: Critical Path Identification**
- Find the longest dependency chain
- Identify modules that must be close together
- Prioritize high-wirelength connections

**Step 3: Initial Placement Strategy**
- Place modules with most dependencies first (central position)
- Use [0, 0] as starting corner for first module
- Leave at least 1-cell spacing between modules for routing

**Step 4: Optimization**
- Calculate Manhattan wirelength for all connections
- Check if moving any module reduces total wirelength
- Ensure no boundary violations

**Step 5: Validation**
- Verify all constraints (Section 5 checklist)
- Estimate final metrics (wirelength, area)
- Prepare output JSON

Priority Order:
1. VALIDITY: No overlaps, all within boundaries (MUST)
2. WIRELENGTH: Minimize sum of Manhattan distances (PRIMARY)
3. COMPACTNESS: Minimize bounding box area (SECONDARY)"""

    def _get_section5_verification(self) -> str:
        """Section 5: Self-Verification Checklist - Critical for quality."""
        return """Before outputting your solution, verify ALL items below:

**Boundary Check:**
- [ ] Every module's x ≥ 0 and x + width ≤ chip_width
- [ ] Every module's y ≥ 0 and y + height ≤ chip_height
- [ ] No module extends beyond chip boundaries

**Overlap Check:**
- [ ] For every pair of modules (M1, M2): NOT (M1 overlaps M2)
- [ ] Check: M1.x + M1.width ≤ M2.x OR M2.x + M2.width ≤ M1.x OR M1.y + M1.height ≤ M2.y OR M2.y + M2.height ≤ M1.y
- [ ] No shared cells between any two modules

**Wirelength Check:**
- [ ] Calculate Manhattan distance for each dependency: |x1 - x2| + |y1 - y2|
- [ ] Sum all distances to get total wirelength
- [ ] Verify connected modules are reasonably close (not at opposite corners)

**Accessibility Check:**
- [ ] Modules are not packed too tightly (leave ≥1 cell spacing for droplet routing)
- [ ] No module completely surrounded by others

**Format Check:**
- [ ] All coordinates are integers
- [ ] All operation_ids are unique and valid
- [ ] JSON is syntactically correct

**If ANY check fails, revise your solution before outputting.**"""

    def _get_section6_output(self) -> str:
        """Section 6: Output Format and error handling."""
        schema_info = self._get_output_format()

        return f"""{schema_info}

**Interaction Guidelines:**

1. **Success Case:** Return valid JSON following the schema above
   - Include 'placements' array with all modules
   - Include 'metrics' with wirelength and area estimates
   - Ensure all coordinates are integers

2. **Failure Case:** If you cannot find a valid placement:
   - Return JSON with {{"error": "description of why placement failed"}}
   - Common failure reasons: "Insufficient chip area", "Module size mismatch"

3. **Error Correction:** If previous attempt had violations:
   - Address each violation specifically in your thinking
   - Show how you fixed overlaps or boundary issues
   - Re-verify all constraints

**Remember:** A valid placement with higher wirelength is better than an invalid "optimal" placement."""
