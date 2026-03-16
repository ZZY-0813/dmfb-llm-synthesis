"""Base prompt template for DMFB Agents.

Provides foundation for all prompt templates with:
- Few-shot example management
- Variable substitution
- Output format specification
- Chain-of-Thought support
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json


@dataclass
class Example:
    """A single few-shot example."""
    input: str
    output: str
    explanation: Optional[str] = None


class PromptTemplateError(Exception):
    """Prompt template error."""
    pass


class BasePromptTemplate(ABC):
    """Base class for all prompt templates.

    Usage:
        template = PlacementPrompt()
        prompt = template.generate(
            problem=problem_data,
            examples=similar_examples,
            chain_of_thought=True
        )
    """

    # Template metadata (override in subclass)
    TASK_NAME = "base"
    TASK_DESCRIPTION = "Base task"

    # Base system prompt (override in subclass)
    SYSTEM_PROMPT = """You are an expert in Digital Microfluidic Biochip (DMFB) design automation.
Your task is to optimize {task_description}.
Always provide valid, feasible solutions that respect all constraints."""

    # Base user prompt template (override in subclass)
    USER_TEMPLATE = """## Problem

{problem_description}

## Task

{task_instructions}

## Output Format

{output_format}

{examples_section}
{chain_of_thought_section}
Generate your solution now:"""

    def __init__(self):
        """Initialize template."""
        self.examples: List[Example] = []
        self.chain_of_thought = True

    def set_examples(self, examples: List[Example]):
        """Set few-shot examples.

        Args:
            examples: List of Example objects
        """
        self.examples = examples

    def add_example(self, example: Example):
        """Add a few-shot example."""
        self.examples.append(example)

    def set_chain_of_thought(self, enabled: bool):
        """Enable/disable Chain-of-Thought prompting."""
        self.chain_of_thought = enabled

    def generate(self,
                 problem: Dict[str, Any],
                 examples: Optional[List[Example]] = None,
                 chain_of_thought: Optional[bool] = None) -> str:
        """Generate complete prompt.

        Args:
            problem: Problem data dictionary
            examples: Optional few-shot examples (uses self.examples if None)
            chain_of_thought: Optional CoT flag (uses self.chain_of_thought if None)

        Returns:
            Complete prompt string
        """
        if examples is not None:
            self.examples = examples
        if chain_of_thought is not None:
            self.chain_of_thought = chain_of_thought

        # Build sections
        problem_desc = self._format_problem(problem)
        task_instructions = self._get_task_instructions()
        output_format = self._get_output_format()
        examples_section = self._build_examples_section()
        cot_section = self._build_cot_section()

        # Assemble user prompt
        user_prompt = self.USER_TEMPLATE.format(
            problem_description=problem_desc,
            task_instructions=task_instructions,
            output_format=output_format,
            examples_section=examples_section,
            chain_of_thought_section=cot_section
        )

        return user_prompt

    def get_system_prompt(self) -> str:
        """Get system prompt."""
        return self.SYSTEM_PROMPT.format(
            task_description=self.TASK_DESCRIPTION
        )

    @abstractmethod
    def _format_problem(self, problem: Dict[str, Any]) -> str:
        """Format problem description.

        Args:
            problem: Problem data

        Returns:
            Formatted problem string
        """
        pass

    @abstractmethod
    def _get_task_instructions(self) -> str:
        """Get task-specific instructions.

        Returns:
            Task instruction string
        """
        pass

    @abstractmethod
    def _get_output_format(self) -> str:
        """Get output format specification.

        Returns:
            Output format string (usually JSON schema)
        """
        pass

    def _build_examples_section(self) -> str:
        """Build few-shot examples section."""
        if not self.examples:
            return ""

        sections = ["## Examples\n"]
        for i, ex in enumerate(self.examples[:3], 1):  # Max 3 examples
            sections.append(f"### Example {i}")
            sections.append(f"Input:\n{ex.input}\n")
            sections.append(f"Output:\n{ex.output}\n")
            if ex.explanation:
                sections.append(f"Explanation: {ex.explanation}\n")

        return "\n".join(sections)

    def _build_cot_section(self) -> str:
        """Build Chain-of-Thought section."""
        if not self.chain_of_thought:
            return ""

        return """## Instructions

Think step by step:
1. Analyze the problem constraints
2. Identify critical path and dependencies
3. Apply optimization strategy
4. Validate feasibility
5. Generate final solution

"""

    def _json_schema_to_example(self, schema: Dict[str, Any]) -> str:
        """Convert JSON schema to example format."""
        example = {}
        for key, value in schema.get("properties", {}).items():
            if value.get("type") == "array":
                example[key] = []
            elif value.get("type") == "object":
                example[key] = {}
            elif value.get("type") == "integer":
                example[key] = 0
            elif value.get("type") == "number":
                example[key] = 0.0
            elif value.get("type") == "boolean":
                example[key] = True
            else:
                example[key] = "string"

        return json.dumps(example, indent=2)


class ProblemFormatter:
    """Utility to format DMFB problems for prompts."""

    @staticmethod
    def format_chip(size: tuple) -> str:
        """Format chip size."""
        return f"{size[0]}x{size[1]}"

    @staticmethod
    def format_operations(operations: List[Dict]) -> str:
        """Format operations list."""
        lines = []
        for op in operations:
            deps = f" (depends on: {op.get('dependencies', [])})" if op.get('dependencies') else ""
            lines.append(f"- {op.get('name', op.get('id', 'unknown'))}: "
                        f"{op.get('op_type', 'unknown')}{deps}")
        return "\n".join(lines)

    @staticmethod
    def format_modules(modules: Dict[str, Any]) -> str:
        """Format module library."""
        lines = []
        for name, mod in modules.items():
            size = f"{mod.get('width', '?')}x{mod.get('height', '?')}"
            time = mod.get('exec_time', mod.get('duration', '?'))
            lines.append(f"- {name}: {size}, execution time: {time}")
        return "\n".join(lines)
