"""
Base adapter interface for external DMFB tools.

All adapters must implement this interface to provide a unified API.
"""

from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional, List
from pathlib import Path

from ..problem import DMFBProblem


class AdapterError(Exception):
    """Error raised by adapters."""
    pass


class BaseAdapter(ABC):
    """
    Abstract base class for DMFB tool adapters.

    All adapters must implement:
    - solve_placement(): Layout synthesis
    - solve_scheduling(): Operation scheduling
    - solve_routing(): Droplet routing
    - solve_full(): Complete synthesis pipeline
    """

    def __init__(self, tool_path: Optional[str] = None):
        """
        Initialize adapter.

        Args:
            tool_path: Path to the external tool executable
        """
        self.tool_path = Path(tool_path) if tool_path else None
        self._validate_installation()

    @abstractmethod
    def _validate_installation(self):
        """Check if the external tool is properly installed."""
        pass

    @abstractmethod
    def solve_placement(self, problem: DMFBProblem, **kwargs) -> Dict[int, Tuple[int, int]]:
        """
        Solve placement problem.

        Args:
            problem: DMFB problem instance
            **kwargs: Algorithm-specific parameters

        Returns:
            Dictionary mapping operation ID to (x, y) position
        """
        pass

    @abstractmethod
    def solve_scheduling(self, problem: DMFBProblem,
                        placement: Optional[Dict[int, Tuple[int, int]]] = None,
                        **kwargs) -> Dict[int, Tuple[int, int]]:
        """
        Solve scheduling problem.

        Args:
            problem: DMFB problem instance
            placement: Optional placement for location-aware scheduling
            **kwargs: Algorithm-specific parameters

        Returns:
            Dictionary mapping operation ID to (start_time, end_time)
        """
        pass

    @abstractmethod
    def solve_routing(self, problem: DMFBProblem,
                     placement: Dict[int, Tuple[int, int]],
                     schedule: Dict[int, Tuple[int, int]],
                     **kwargs) -> Dict[int, List[Tuple[int, int, int]]]:
        """
        Solve routing problem.

        Args:
            problem: DMFB problem instance
            placement: Module positions
            schedule: Operation schedule
            **kwargs: Algorithm-specific parameters

        Returns:
            Dictionary mapping droplet ID to path [(x, y, t), ...]
        """
        pass

    def solve_full(self, problem: DMFBProblem, **kwargs) -> Dict:
        """
        Run complete synthesis pipeline.

        Default implementation runs placement -> scheduling -> routing.
        Adapters may override for more integrated approaches.

        Returns:
            Dictionary with:
            - 'placement': placement solution
            - 'schedule': scheduling solution
            - 'routing': routing solution
            - 'makespan': total completion time
            - 'cpu_time': computation time
        """
        import time

        start_time = time.time()

        # Step 1: Placement
        placement = self.solve_placement(problem, **kwargs.get('placement_kwargs', {}))

        # Step 2: Scheduling
        schedule = self.solve_scheduling(problem, placement,
                                        **kwargs.get('scheduling_kwargs', {}))

        # Step 3: Routing
        routing = self.solve_routing(problem, placement, schedule,
                                    **kwargs.get('routing_kwargs', {}))

        elapsed = time.time() - start_time

        makespan = max(end for start, end in schedule.values()) if schedule else 0

        return {
            'placement': placement,
            'schedule': schedule,
            'routing': routing,
            'makespan': makespan,
            'cpu_time': elapsed
        }

    def is_available(self) -> bool:
        """Check if this adapter is available for use."""
        try:
            self._validate_installation()
            return True
        except AdapterError:
            return False
