"""
Base Agent class for DMFB synthesis.

All specialized agents (Placement, Scheduling, Routing) inherit from this.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import time

import sys
sys.path.insert(0, 'src')

from baseline.problem import DMFBProblem
from llm import LLMClient, Message


class AgentStage(Enum):
    """Agent stages in the synthesis pipeline."""
    PLACEMENT = "placement"
    SCHEDULING = "scheduling"
    ROUTING = "routing"


@dataclass
class AgentContext:
    """
    Context passed between agents in the pipeline.

    Contains:
    - problem: Original DMFB problem
    - placement: Placement solution (from Placement Agent)
    - schedule: Schedule solution (from Scheduling Agent)
    - routes: Routing solution (from Routing Agent)
    - metadata: Additional information (iteration count, errors, etc.)
    """
    problem: DMFBProblem
    placement: Optional[List[Dict]] = None
    schedule: Optional[List[Dict]] = None
    routes: Optional[List[Dict]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert context to dictionary."""
        return {
            "problem": self.problem.to_dict(),
            "placement": self.placement,
            "schedule": self.schedule,
            "routes": self.routes,
            "metadata": self.metadata
        }


@dataclass
class AgentResult:
    """
    Result returned by an agent.

    Attributes:
        success: Whether the agent succeeded
        solution: The solution (placement, schedule, or routes)
        error_message: Error message if failed
        iterations: Number of iterations taken
        llm_calls: Number of LLM API calls made
        time_seconds: Time taken
        reasoning: Natural language reasoning from LLM
    """
    success: bool
    solution: Any = None
    error_message: Optional[str] = None
    iterations: int = 0
    llm_calls: int = 0
    time_seconds: float = 0.0
    reasoning: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "solution": self.solution,
            "error_message": self.error_message,
            "iterations": self.iterations,
            "llm_calls": self.llm_calls,
            "time_seconds": self.time_seconds,
            "reasoning": self.reasoning
        }


class BaseAgent(ABC):
    """
    Abstract base class for all DMFB synthesis agents.

    Each agent:
    1. Receives context (problem + previous solutions)
    2. Uses LLM to generate solution
    3. Validates with verifier
    4. Iterates if errors found
    5. Returns result
    """

    def __init__(self,
                 stage: AgentStage,
                 llm_client: LLMClient,
                 max_iterations: int = 5,
                 verbose: bool = True):
        """
        Initialize agent.

        Args:
            stage: Which synthesis stage this agent handles
            llm_client: LLM client for API calls
            max_iterations: Maximum repair iterations
            verbose: Print progress
        """
        self.stage = stage
        self.llm_client = llm_client
        self.max_iterations = max_iterations
        self.verbose = verbose

        # Statistics
        self.total_llm_calls = 0
        self.total_iterations = 0

    @abstractmethod
    def generate_prompt(self, context: AgentContext, errors: List[str] = None) -> str:
        """
        Generate prompt for LLM.

        Args:
            context: Current synthesis context
            errors: Previous errors to fix (for repair iterations)

        Returns:
            Prompt string
        """
        pass

    @abstractmethod
    def parse_response(self, response: str, context: AgentContext) -> Any:
        """
        Parse LLM response into solution format.

        Args:
            response: Raw LLM response
            context: Current context

        Returns:
            Parsed solution
        """
        pass

    @abstractmethod
    def verify_solution(self, solution: Any, context: AgentContext) -> Tuple[bool, List[str]]:
        """
        Verify solution correctness.

        Args:
            solution: Proposed solution
            context: Current context

        Returns:
            (is_valid, list_of_errors)
        """
        pass

    def solve(self, context: AgentContext) -> AgentResult:
        """
        Main solve loop with iterative repair.

        Args:
            context: Synthesis context

        Returns:
            AgentResult with solution or error
        """
        start_time = time.time()
        iterations = 0
        llm_calls = 0
        errors = []
        reasoning = ""

        if self.verbose:
            print(f"\n[{self.stage.value.upper()} AGENT] Starting synthesis...")

        while iterations < self.max_iterations:
            iterations += 1

            # Generate prompt
            prompt = self.generate_prompt(context, errors if errors else None)

            # Call LLM
            try:
                response = self.llm_client.chat(prompt)
                llm_calls += 1
                content = response.content

                # Extract reasoning (first part before JSON)
                if "```" in content:
                    parts = content.split("```")
                    reasoning = parts[0].strip()
                else:
                    reasoning = content[:500]  # First 500 chars

            except Exception as e:
                return AgentResult(
                    success=False,
                    error_message=f"LLM API error: {e}",
                    iterations=iterations,
                    llm_calls=llm_calls,
                    time_seconds=time.time() - start_time
                )

            # Parse solution
            try:
                solution = self.parse_response(content, context)
            except Exception as e:
                errors = [f"Parse error: {e}"]
                if self.verbose:
                    print(f"  Iteration {iterations}: Parse failed - {e}")
                continue

            # Verify solution
            is_valid, errors = self.verify_solution(solution, context)

            if is_valid:
                elapsed = time.time() - start_time
                if self.verbose:
                    print(f"  [OK] Solved in {iterations} iterations, {elapsed:.2f}s")

                self.total_llm_calls += llm_calls
                self.total_iterations += iterations

                return AgentResult(
                    success=True,
                    solution=solution,
                    iterations=iterations,
                    llm_calls=llm_calls,
                    time_seconds=elapsed,
                    reasoning=reasoning
                )
            else:
                if self.verbose:
                    print(f"  Iteration {iterations}: {len(errors)} errors found, repairing...")

        # Max iterations reached
        elapsed = time.time() - start_time
        if self.verbose:
            print(f"  [FAIL] Failed after {iterations} iterations")

        self.total_llm_calls += llm_calls
        self.total_iterations += iterations

        return AgentResult(
            success=False,
            solution=solution,  # Return best effort
            error_message=f"Max iterations ({self.max_iterations}) reached. Last errors: {errors[:3]}",
            iterations=iterations,
            llm_calls=llm_calls,
            time_seconds=elapsed,
            reasoning=reasoning
        )

    def get_system_prompt(self) -> str:
        """
        Get system prompt for this agent.

        Override in subclass for stage-specific instructions.
        """
        return f"""You are a DMFB (Digital Microfluidic Biochip) {self.stage.value} design expert.

Your task is to generate valid {self.stage.value} solutions that satisfy all constraints.

Key constraints:
- Modules cannot overlap
- All modules must fit within the chip boundaries
- Operations must respect dependencies
- Resources cannot be double-booked
- Droplets cannot collide

Respond with:
1. Your reasoning process
2. The solution in JSON format within ```json ... ``` blocks
"""


class MasterAgent:
    """
    Master agent that coordinates the synthesis pipeline.

    Orchestrates Placement → Scheduling → Routing agents.
    """

    def __init__(self,
                 placement_agent: BaseAgent,
                 scheduling_agent: BaseAgent,
                 routing_agent: BaseAgent,
                 verbose: bool = True):
        self.placement_agent = placement_agent
        self.scheduling_agent = scheduling_agent
        self.routing_agent = routing_agent
        self.verbose = verbose

    def synthesize(self, problem: DMFBProblem) -> Dict[str, Any]:
        """
        Run full synthesis pipeline.

        Args:
            problem: DMFB problem to solve

        Returns:
            Complete solution with all stages
        """
        start_time = time.time()

        if self.verbose:
            print("\n" + "=" * 60)
            print(f"DMFB SYNTHESIS: {problem.name}")
            print(f"Operations: {len(problem.operations)}, Grid: {problem.chip_width}x{problem.chip_height}")
            print("=" * 60)

        # Create initial context
        context = AgentContext(problem=problem)
        results = {}

        # Stage 1: Placement
        placement_result = self.placement_agent.solve(context)
        results["placement"] = placement_result

        if not placement_result.success:
            if self.verbose:
                print("\n[FAIL] PLACEMENT FAILED - Cannot proceed")
            return self._finalize_results(results, problem, time.time() - start_time)

        context.placement = placement_result.solution

        # Stage 2: Scheduling
        schedule_result = self.scheduling_agent.solve(context)
        results["scheduling"] = schedule_result

        if not schedule_result.success:
            if self.verbose:
                print("\n[FAIL] SCHEDULING FAILED - Cannot proceed")
            return self._finalize_results(results, problem, time.time() - start_time)

        context.schedule = schedule_result.solution

        # Stage 3: Routing
        routing_result = self.routing_agent.solve(context)
        results["routing"] = routing_result

        if not routing_result.success:
            if self.verbose:
                print("\n⚠️ ROUTING FAILED - Partial solution available")
        else:
            context.routes = routing_result.solution
            if self.verbose:
                print("\n✅ ALL STAGES COMPLETE")

        return self._finalize_results(results, problem, time.time() - start_time)

    def _finalize_results(self, results: Dict, problem: DMFBProblem,
                          total_time: float) -> Dict[str, Any]:
        """Finalize and format results."""
        total_llm_calls = sum(r.llm_calls for r in results.values())
        total_iterations = sum(r.iterations for r in results.values())

        return {
            "problem": problem.to_dict(),
            "solution": {
                "placement": results.get("placement", AgentResult(False)).solution,
                "schedule": results.get("scheduling", AgentResult(False)).solution,
                "routes": results.get("routing", AgentResult(False)).solution,
            },
            "results": {k: v.to_dict() for k, v in results.items()},
            "summary": {
                "success_placement": results.get("placement", AgentResult(False)).success,
                "success_scheduling": results.get("scheduling", AgentResult(False)).success,
                "success_routing": results.get("routing", AgentResult(False)).success,
                "total_time_seconds": total_time,
                "total_llm_calls": total_llm_calls,
                "total_iterations": total_iterations,
            }
        }
