"""
Pure Python fallback adapter.

Provides baseline implementations using the algorithms in:
- placement_ga.py
- scheduling_list.py
- routing_astar.py

This adapter is always available and serves as the default/fallback.
"""

from typing import Dict, Tuple, Optional, List
import time

from .base_adapter import BaseAdapter
from ..problem import DMFBProblem
from ..placement_ga import PlacementGA, PlacementIndividual
from ..scheduling_list import ListScheduler
from ..routing_astar import AStarRouter


class PythonFallbackAdapter(BaseAdapter):
    """
    Pure Python implementation of DMFB synthesis algorithms.

    This adapter is always available and provides:
    - GA-based placement
    - List scheduling (ASAP, ALAP, mobility-based)
    - A* routing with conflict resolution

    While not as optimized as external C++ tools, it is sufficient
    for small-to-medium problems and generating training data.
    """

    def __init__(self, seed: int = 42):
        """
        Initialize Python fallback adapter.

        Args:
            seed: Random seed for reproducibility
        """
        self.seed = seed
        super().__init__(None)  # No external tool needed

    def _validate_installation(self):
        """Python fallback is always available."""
        pass  # Nothing to validate

    def solve_placement(self, problem: DMFBProblem,
                       algorithm: str = "ga",
                       **kwargs) -> Dict[int, Tuple[int, int]]:
        """
        Solve placement using GA.

        Args:
            problem: DMFB problem instance
            algorithm: "ga" (only option currently)
            **kwargs: Passed to PlacementGA

        Returns:
            Dictionary mapping operation ID to (x, y) position
        """
        if algorithm != "ga":
            raise ValueError(f"Unknown placement algorithm: {algorithm}")

        ga = PlacementGA(problem, seed=self.seed, **kwargs)
        best = ga.solve(verbose=kwargs.get('verbose', False))

        return best.positions

    def solve_scheduling(self, problem: DMFBProblem,
                        placement: Optional[Dict[int, Tuple[int, int]]] = None,
                        algorithm: str = "list",
                        **kwargs) -> Dict[int, Tuple[int, int]]:
        """
        Solve scheduling using list scheduling.

        Args:
            problem: DMFB problem instance
            placement: Optional placement (not used by list scheduler)
            algorithm: "list" (only option currently)
            **kwargs: Priority strategy and other options

        Returns:
            Dictionary mapping operation ID to (start_time, end_time)
        """
        if algorithm != "list":
            raise ValueError(f"Unknown scheduling algorithm: {algorithm}")

        scheduler = ListScheduler(problem)
        priority_strategy = kwargs.get('priority_strategy', 'asap')
        result = scheduler.solve(priority_strategy=priority_strategy,
                                placement=placement)

        return result['schedule']

    def solve_routing(self, problem: DMFBProblem,
                     placement: Dict[int, Tuple[int, int]],
                     schedule: Dict[int, Tuple[int, int]],
                     algorithm: str = "astar",
                     **kwargs) -> Dict[int, List[Tuple[int, int, int]]]:
        """
        Solve routing using A* search.

        Args:
            problem: DMFB problem instance
            placement: Module positions
            schedule: Operation schedule
            algorithm: "astar" (only option currently)
            **kwargs: Routing strategy and other options

        Returns:
            Dictionary mapping droplet ID to path
        """
        if algorithm != "astar":
            raise ValueError(f"Unknown routing algorithm: {algorithm}")

        # Create router
        router = AStarRouter(problem)

        # Add module obstacles
        op_map = {op.id: op for op in problem.operations}
        for op_id, (x, y) in placement.items():
            op = op_map.get(op_id)
            if op:
                module = problem.modules[op.module_type]
                router.add_obstacle(x, y, module.width, module.height)

        # Generate droplets from schedule and placement
        droplets = self._generate_droplets(problem, placement, schedule)

        # Route
        strategy = kwargs.get('strategy', 'prioritized')
        return router.route_multiple(droplets, strategy=strategy)

    def _generate_droplets(self, problem: DMFBProblem,
                          placement: Dict[int, Tuple[int, int]],
                          schedule: Dict[int, Tuple[int, int]]) -> List:
        """Generate droplets from schedule for routing."""
        from ..problem import Droplet

        droplets = []
        droplet_id = 0
        op_map = {op.id: op for op in problem.operations}

        # For each operation that has dependencies,
        # create droplets from predecessor output to this operation's input
        for op in problem.operations:
            if not op.dependencies:
                continue

            start_time, end_time = schedule[op.id]

            for dep_id in op.dependencies:
                # Droplet moves from dep's position to this op's position
                start_pos = placement[dep_id]
                end_pos = placement[op.id]

                # Estimate deadline based on operation start time
                deadline = start_time

                droplet = Droplet(
                    id=droplet_id,
                    start=start_pos,
                    end=end_pos,
                    start_time=schedule[dep_id][1],  # Depart when predecessor finishes
                    deadline=deadline,
                    operation_id=op.id
                )
                droplets.append(droplet)
                droplet_id += 1

        return droplets

    def solve_full(self, problem: DMFBProblem,
                   placement_kwargs: Optional[Dict] = None,
                   scheduling_kwargs: Optional[Dict] = None,
                   routing_kwargs: Optional[Dict] = None) -> Dict:
        """
        Run complete synthesis pipeline with detailed statistics.

        Overrides base implementation to provide more detailed output.
        """
        import time

        start_time = time.time()

        # Step 1: Placement
        t0 = time.time()
        placement = self.solve_placement(
            problem,
            **(placement_kwargs or {})
        )
        placement_time = time.time() - t0

        # Step 2: Scheduling
        t0 = time.time()
        schedule = self.solve_scheduling(
            problem,
            placement,
            **(scheduling_kwargs or {})
        )
        scheduling_time = time.time() - t0

        # Step 3: Routing
        t0 = time.time()
        routing = self.solve_routing(
            problem,
            placement,
            schedule,
            **(routing_kwargs or {})
        )
        routing_time = time.time() - t0

        total_time = time.time() - start_time

        # Calculate makespan
        makespan = max(end for start, end in schedule.values()) if schedule else 0

        # Count successful routes
        successful_routes = sum(1 for path in routing.values() if path is not None)

        return {
            'placement': placement,
            'schedule': schedule,
            'routing': routing,
            'makespan': makespan,
            'cpu_time': total_time,
            'placement_time': placement_time,
            'scheduling_time': scheduling_time,
            'routing_time': routing_time,
            'num_routes': len(routing),
            'successful_routes': successful_routes,
            'routing_success_rate': successful_routes / len(routing) if routing else 0
        }
