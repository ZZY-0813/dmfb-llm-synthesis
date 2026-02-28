"""
List Scheduling Algorithm for DMFB.

Schedules operations based on a priority list, respecting:
- Dependency constraints
- Resource constraints (module availability)
- Optional: placement-based timing
"""

import heapq
from typing import Dict, Tuple, List, Set, Optional
from collections import defaultdict
from dataclasses import dataclass

from .problem import DMFBProblem, Operation, Module


@dataclass
class ScheduledOperation:
    """An operation with its scheduled time slot."""
    operation: Operation
    start_time: int
    end_time: int
    module_instance: Optional[str] = None  # If multiple modules of same type


class ListScheduler:
    """
    List scheduling algorithm for DMFB.

    Uses priority-based scheduling with ASAP (As Soon As Possible) heuristic.
    Supports both operation scheduling and binding to physical modules.

    Example:
        >>> problem = DMFBProblem(...)
        >>> scheduler = ListScheduler(problem)
        >>> schedule = scheduler.solve()
        >>> print(f"Makespan: {schedule['makespan']}")
        >>> for op_id, (start, end) in schedule['schedule'].items():
        ...     print(f"Op {op_id}: [{start}, {end})")
    """

    def __init__(self, problem: DMFBProblem,
                 module_instances: Optional[Dict[str, int]] = None):
        """
        Initialize scheduler.

        Args:
            problem: DMFB problem instance
            module_instances: Number of instances for each module type.
                            If None, assumes unlimited resources.
        """
        self.problem = problem
        self.module_instances = module_instances or {}

        # Build operation lookup
        self.op_map = {op.id: op for op in problem.operations}

        # Precompute ASAP/ALAP times for prioritization
        self.asap = self._compute_asap()
        self.alap = self._compute_alap()

    def solve(self, priority_strategy: str = "asap",
              placement: Optional[Dict[int, Tuple[int, int]]] = None) -> Dict:
        """
        Execute list scheduling.

        Args:
            priority_strategy: How to prioritize operations ("asap", "alap", "mobility", "critical_path")
            placement: Optional placement for calculating transfer delays

        Returns:
            Dictionary with:
            - 'schedule': {op_id: (start_time, end_time)}
            - 'makespan': total completion time
            - 'module_usage': resource utilization stats
        """
        schedule = {}  # op_id -> (start, end)
        completed = set()

        # Track module availability: module_type -> list of (available_time, instance_id)
        # Using a simple approach: track when each instance becomes available
        module_available = defaultdict(list)  # mtype -> [available_time, ...]
        for mtype in self.problem.modules:
            count = self.module_instances.get(mtype, float('inf'))
            if count == float('inf'):
                # Unlimited resources - use single instance with immediate availability
                module_available[mtype] = [0]
            else:
                module_available[mtype] = [0] * int(count)

        current_time = 0
        priorities = self._calculate_priorities(priority_strategy)

        while len(completed) < len(self.problem.operations):
            # Find all ready operations (dependencies satisfied)
            ready = []
            for op in self.problem.operations:
                if op.id in completed or op.id in schedule:
                    continue
                if all(dep in completed for dep in op.dependencies):
                    ready.append(op.id)

            if not ready:
                # No ready operations - advance time to next completion
                if schedule:
                    current_time = min(
                        end for op_id, (start, end) in schedule.items()
                        if op_id not in completed
                    )
                    # Mark all operations that complete by this time as completed
                    for op_id, (start, end) in list(schedule.items()):
                        if end <= current_time and op_id not in completed:
                            completed.add(op_id)
                continue

            # Sort ready operations by priority
            ready.sort(key=lambda x: priorities[x], reverse=True)
            scheduled_this_cycle = []

            for op_id in ready:
                op = self.op_map[op_id]
                mtype = op.module_type
                duration = op.get_duration(self.problem.modules)

                # Find earliest start based on dependencies
                earliest_dep = current_time
                for dep_id in op.dependencies:
                    if dep_id in schedule:
                        earliest_dep = max(earliest_dep, schedule[dep_id][1])

                # Find module availability
                if self.module_instances.get(mtype, float('inf')) == float('inf'):
                    # Unlimited resources
                    start_time = earliest_dep
                else:
                    # Find earliest available module instance
                    earliest_avail = min(module_available[mtype])
                    start_time = max(earliest_dep, earliest_avail)
                    # Reserve this module instance
                    idx = module_available[mtype].index(earliest_avail)
                    module_available[mtype][idx] = start_time + duration

                end_time = start_time + duration
                schedule[op_id] = (start_time, end_time)
                scheduled_this_cycle.append(op_id)

                # Check if this operation completes immediately (duration 0)
                if end_time <= current_time:
                    completed.add(op_id)

            # If no progress was made, advance time
            if not scheduled_this_cycle:
                if schedule:
                    current_time = min(
                        end for op_id, (start, end) in schedule.items()
                        if op_id not in completed
                    )
                    for op_id, (start, end) in list(schedule.items()):
                        if end <= current_time and op_id not in completed:
                            completed.add(op_id)
                else:
                    current_time += 1

        makespan = max(end for start, end in schedule.values())

        # Calculate module usage statistics
        module_usage = defaultdict(lambda: {'used_time': 0, 'total_time': 0})
        for mtype in self.problem.modules:
            count = self.module_instances.get(mtype, len(self.problem.operations))
            if count == float('inf'):
                count = 1
            module_usage[mtype]['total_time'] = makespan * int(count)

        for op_id, (start, end) in schedule.items():
            op = self.op_map[op_id]
            duration = end - start
            module_usage[op.module_type]['used_time'] += duration

        return {
            'schedule': schedule,
            'makespan': makespan,
            'module_usage': dict(module_usage),
            'priority_strategy': priority_strategy
        }

    def _compute_asap(self) -> Dict[int, int]:
        """Compute ASAP (As Soon As Possible) times."""
        asap = {op.id: 0 for op in self.problem.operations}
        topo_order = self.problem.topological_sort()

        for op_id in topo_order:
            op = self.op_map[op_id]
            duration = op.get_duration(self.problem.modules)
            finish_time = asap[op_id] + duration
            for succ in self.problem.operations:
                if op_id in succ.dependencies:
                    asap[succ.id] = max(asap[succ.id], finish_time)

        return asap

    def _compute_alap(self) -> Dict[int, int]:
        """Compute ALAP (As Late As Possible) times."""
        asap = self._compute_asap()
        cp_length = max(asap[op.id] + op.get_duration(self.problem.modules)
                       for op in self.problem.operations)

        alap = {op.id: cp_length for op in self.problem.operations}
        topo_order = self.problem.topological_sort()

        for op_id in reversed(topo_order):
            op = self.op_map[op_id]
            duration = op.get_duration(self.problem.modules)
            successors = [o for o in self.problem.operations if op_id in o.dependencies]
            if successors:
                min_succ_start = min(alap[s.id] for s in successors)
                alap[op_id] = min_succ_start - duration

        return alap

    def _calculate_priorities(self, strategy: str) -> Dict[int, float]:
        """Calculate scheduling priorities for operations."""
        priorities = {}

        for op in self.problem.operations:
            if strategy == "asap":
                priorities[op.id] = -self.asap[op.id]
            elif strategy == "alap":
                priorities[op.id] = -self.alap[op.id]
            elif strategy == "mobility":
                mobility = self.alap[op.id] - self.asap[op.id]
                priorities[op.id] = -mobility
            elif strategy == "critical_path":
                cp_len = self._longest_path_to_sink(op.id)
                priorities[op.id] = cp_len
            else:
                priorities[op.id] = -op.id

        return priorities

    def _longest_path_to_sink(self, op_id: int, memo: Optional[Dict] = None) -> int:
        """Calculate longest path from this operation to any sink."""
        if memo is None:
            memo = {}

        if op_id in memo:
            return memo[op_id]

        op = self.op_map[op_id]
        duration = op.get_duration(self.problem.modules)
        successors = [o for o in self.problem.operations if op_id in o.dependencies]

        if not successors:
            memo[op_id] = duration
            return duration

        max_succ_path = max(
            self._longest_path_to_sink(s.id, memo)
            for s in successors
        )

        memo[op_id] = duration + max_succ_path
        return memo[op_id]

    def validate_schedule(self, schedule: Dict[int, Tuple[int, int]]) -> List[str]:
        """Validate that a schedule satisfies all constraints."""
        violations = []

        for op_id, (start, end) in schedule.items():
            op = self.op_map[op_id]
            expected_duration = op.get_duration(self.problem.modules)
            if end - start != expected_duration:
                violations.append(
                    f"Op {op_id}: Duration mismatch ({end-start} vs {expected_duration})"
                )

            for dep_id in op.dependencies:
                if dep_id not in schedule:
                    violations.append(f"Op {op_id}: Missing dependency {dep_id}")
                    continue
                dep_end = schedule[dep_id][1]
                if start < dep_end:
                    violations.append(
                        f"Op {op_id}: Starts at {start} before dependency "
                        f"{dep_id} ends at {dep_end}"
                    )

        return violations
