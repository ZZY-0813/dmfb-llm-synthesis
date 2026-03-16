"""Master Agent for DMFB synthesis pipeline.

Coordinates Placement → Scheduling → Routing in sequence.

Usage:
    master = MasterAgent(llm_client)
    result = master.synthesize(problem_dict)

    if result['success']:
        print(f"Placement: {result['placement']}")
        print(f"Schedule: {result['schedule']}")
        print(f"Routes: {result['routes']}")
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import time

from llm.client import LLMClient
from agents.base_agent import AgentContext
from baseline.problem import DMFBProblem, Operation, Module, ModuleType


@dataclass
class PipelineStage:
    """Result of a single pipeline stage."""
    name: str
    success: bool
    solution: Optional[Dict[str, Any]] = None
    violations: List[Dict[str, Any]] = field(default_factory=list)
    duration: float = 0.0
    iterations: int = 0
    error: Optional[str] = None


class MasterAgent:
    """Master agent coordinating the full DMFB synthesis pipeline.

    Pipeline:
    1. Placement: Position modules on chip
    2. Scheduling: Assign operation start/end times
    3. Routing: Plan droplet paths
    """

    def __init__(self,
                 llm_client: LLMClient,
                 max_iterations_per_stage: int = 3):
        """Initialize Master Agent."""
        self.llm = llm_client
        self.max_iterations = max_iterations_per_stage

        # Import sub-agents
        from agents.placement_agent import PlacementAgent
        from agents.scheduling_agent import SchedulingAgent
        from agents.routing_agent import RoutingAgent

        # Create sub-agents
        self.placement_agent = PlacementAgent(llm_client, max_iterations_per_stage)
        self.scheduling_agent = SchedulingAgent(llm_client, max_iterations_per_stage)
        self.routing_agent = RoutingAgent(llm_client, max_iterations_per_stage)

    def _dict_to_problem(self, problem_dict: Dict[str, Any]) -> DMFBProblem:
        """Convert dictionary to DMFBProblem object."""
        # Convert operations
        operations = []
        for op_dict in problem_dict.get('operations', []):
            operations.append(Operation(
                id=op_dict['id'],
                op_type=op_dict['op_type'],
                module_type=op_dict['module_type'],
                dependencies=op_dict.get('dependencies', [])
            ))

        # Convert modules
        modules = {}
        for mod_id, mod_dict in problem_dict.get('modules', {}).items():
            # Determine module type from name
            mod_type = ModuleType.MIXER
            if 'detect' in mod_id.lower():
                mod_type = ModuleType.DETECTOR
            elif 'heat' in mod_id.lower():
                mod_type = ModuleType.HEATER
            elif 'storage' in mod_id.lower():
                mod_type = ModuleType.STORAGE

            modules[mod_id] = Module(
                name=mod_id,
                type=mod_type,
                width=mod_dict['width'],
                height=mod_dict['height'],
                exec_time=mod_dict.get('exec_time', 1)
            )

        return DMFBProblem(
            name="master_problem",
            chip_width=problem_dict.get('chip_width', 10),
            chip_height=problem_dict.get('chip_height', 10),
            modules=modules,
            operations=operations
        )

    def synthesize(self, problem_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Run full synthesis pipeline.

        Args:
            problem_dict: Problem specification as dictionary

        Returns:
            Result dictionary with all stage results
        """
        print(f"\n{'='*70}")
        print("Master Agent: Starting Synthesis Pipeline")
        print(f"{'='*70}")
        print(f"Problem: {len(problem_dict.get('operations', []))} operations")
        print(f"Chip: {problem_dict.get('chip_width', '?')}x{problem_dict.get('chip_height', '?')}")

        # Convert dict to DMFBProblem
        problem = self._dict_to_problem(problem_dict)

        results = {
            'success': False,
            'placement': None,
            'schedule': None,
            'routes': None,
            'error': None
        }

        # Stage 1: Placement
        placement_stage = self._run_placement(problem)
        results['placement'] = placement_stage.get('solution')

        if not placement_stage.get('success'):
            results['error'] = f"Placement failed: {placement_stage.get('error')}"
            return results

        # Stage 2: Scheduling
        scheduling_stage = self._run_scheduling(problem, results['placement'])
        results['schedule'] = scheduling_stage.get('solution')

        if not scheduling_stage.get('success'):
            results['error'] = f"Scheduling failed: {scheduling_stage.get('error')}"
            return results

        # Stage 3: Routing
        routing_stage = self._run_routing(problem, results['placement'], results['schedule'])
        results['routes'] = routing_stage.get('solution')

        if not routing_stage.get('success'):
            results['error'] = f"Routing failed: {routing_stage.get('error')}"
            return results

        # Success!
        results['success'] = True
        results['duration'] = placement_stage.get('duration', 0) + \
                             scheduling_stage.get('duration', 0) + \
                             routing_stage.get('duration', 0)

        print(f"\n{'='*70}")
        print("Pipeline Summary")
        print(f"{'='*70}")
        print("Overall: SUCCESS")
        print(f"  Placement: {len(results['placement'].get('placements', []))} modules")
        print(f"  Scheduling: makespan={results['schedule'].get('makespan', 0)}")
        print(f"  Routing: {len(results['routes'].get('droplet_paths', []))} droplets")
        print(f"{'='*70}")

        return results

    def _run_placement(self, problem: DMFBProblem) -> Dict[str, Any]:
        """Run placement stage."""
        print(f"\n[Stage 1/3] Placement")
        print("-" * 70)

        start_time = time.time()

        try:
            # Create context for placement
            context = AgentContext(problem=problem)

            # Run placement agent
            result = self.placement_agent.solve(context)

            duration = time.time() - start_time

            print(f"Result: {'SUCCESS' if result.success else 'FAIL'}")
            print(f"Duration: {duration:.2f}s")
            print(f"Iterations: {result.iterations}")

            if result.success:
                # Format solution for next stage
                placements = result.solution if isinstance(result.solution, list) else []
                solution_dict = {
                    'placements': [
                        {
                            'module_id': p.get('module_id', f'module_{i}'),
                            'x': p.get('x', 0),
                            'y': p.get('y', 0),
                            'width': p.get('width', 2),
                            'height': p.get('height', 2)
                        }
                        for i, p in enumerate(placements)
                    ]
                }
                print(f"Placements: {len(placements)} modules")

                return {
                    'success': True,
                    'solution': solution_dict,
                    'duration': duration
                }
            else:
                return {
                    'success': False,
                    'error': result.error_message,
                    'duration': duration
                }

        except Exception as e:
            duration = time.time() - start_time
            print(f"ERROR: {e}")
            return {
                'success': False,
                'error': str(e),
                'duration': duration
            }

    def _run_scheduling(self,
                       problem: DMFBProblem,
                       placement: Dict[str, Any]) -> Dict[str, Any]:
        """Run scheduling stage."""
        print(f"\n[Stage 2/3] Scheduling")
        print("-" * 70)

        start_time = time.time()

        try:
            # Create context with placement
            context = AgentContext(
                problem=problem,
                placement=placement.get('placements', [])
            )

            # Run scheduling agent
            result = self.scheduling_agent.solve(context)

            duration = time.time() - start_time

            print(f"Result: {'SUCCESS' if result.success else 'FAIL'}")
            print(f"Duration: {duration:.2f}s")
            print(f"Iterations: {result.iterations}")

            if result.success:
                schedule = result.solution if isinstance(result.solution, list) else []

                # Calculate makespan
                makespan = max(s.get('end_time', 0) for s in schedule) if schedule else 0

                solution_dict = {
                    'schedule': schedule,
                    'makespan': makespan
                }

                print(f"Schedule: {len(schedule)} operations, makespan={makespan}")

                return {
                    'success': True,
                    'solution': solution_dict,
                    'duration': duration
                }
            else:
                return {
                    'success': False,
                    'error': result.error_message,
                    'duration': duration
                }

        except Exception as e:
            duration = time.time() - start_time
            print(f"ERROR: {e}")
            return {
                'success': False,
                'error': str(e),
                'duration': duration
            }

    def _run_routing(self,
                    problem: DMFBProblem,
                    placement: Dict[str, Any],
                    schedule: Dict[str, Any]) -> Dict[str, Any]:
        """Run routing stage."""
        print(f"\n[Stage 3/3] Routing")
        print("-" * 70)

        start_time = time.time()

        try:
            # Create context with placement and schedule
            context = AgentContext(
                problem=problem,
                placement=placement.get('placements', []),
                schedule=schedule.get('schedule', [])
            )

            # Run routing agent
            result = self.routing_agent.solve(context)

            duration = time.time() - start_time

            print(f"Result: {'SUCCESS' if result.success else 'FAIL'}")
            print(f"Duration: {duration:.2f}s")
            print(f"Iterations: {result.iterations}")

            if result.success:
                droplet_paths = result.solution if isinstance(result.solution, list) else []

                # Calculate total routing time
                total_time = 0
                for dp in droplet_paths:
                    path = dp.get('path', [])
                    if path:
                        total_time = max(total_time, max(p.get('t', 0) for p in path))

                solution_dict = {
                    'droplet_paths': droplet_paths,
                    'total_routing_time': total_time
                }

                print(f"Routes: {len(droplet_paths)} droplets, total_time={total_time}")

                return {
                    'success': True,
                    'solution': solution_dict,
                    'duration': duration
                }
            else:
                return {
                    'success': False,
                    'error': result.error_message,
                    'duration': duration
                }

        except Exception as e:
            duration = time.time() - start_time
            print(f"ERROR: {e}")
            return {
                'success': False,
                'error': str(e),
                'duration': duration
            }
