"""
A* Routing Algorithm for DMFB Droplets.

Implements 3D (x, y, t) pathfinding with:
- Static obstacles (placed modules)
- Dynamic obstacles (other droplets)
- Fluidic constraints (electrode interference)
- Deadlock detection and resolution
"""

import heapq
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
from dataclasses import dataclass, field

from .problem import DMFBProblem, Droplet


@dataclass(order=True)
class AStarNode:
    """
    Node in A* search tree.

    Ordered by f_score for priority queue.
    """
    f_score: int
    g_score: int = field(compare=False)
    x: int = field(compare=False)
    y: int = field(compare=False)
    t: int = field(compare=False)
    parent: Optional[Tuple] = field(default=None, compare=False)

    def pos(self) -> Tuple[int, int, int]:
        """Return position tuple (x, y, t)."""
        return (self.x, self.y, self.t)


class AStarRouter:
    """
    A* based router for DMFB droplets.

    Performs 3D search (x, y, time) to find collision-free paths.
    Supports prioritized planning and iterative conflict resolution.

    Example:
        >>> problem = DMFBProblem(...)
        >>> router = AStarRouter(problem)
        >>>
        >>> # Add static obstacles (modules)
        >>> for op_id, (x, y) in placement.items():
        ...     router.add_obstacle(x, y, width, height)
        >>>
        >>> # Route droplets
        >>> paths = router.route_multiple(droplets)
    """

    # Fluidic constraint: minimum spacing between droplets (in electrodes)
    FLUIDIC_CONSTRAINT = 1

    def __init__(self, problem: DMFBProblem):
        """
        Initialize router.

        Args:
            problem: DMFB problem with chip dimensions
        """
        self.problem = problem
        self.width = problem.chip_width
        self.height = problem.chip_height

        # Static obstacles (modules) - never change
        self.static_obstacles: Set[Tuple[int, int]] = set()

        # Dynamic reservations (x, y, t) -> droplet_id
        self.reservations: Dict[Tuple[int, int, int], int] = {}

        # Reservation table for fluidic constraint (blocked cells due to nearby droplets)
        self.blocked_cells: Dict[Tuple[int, int, int], int] = {}

    def add_obstacle(self, x: int, y: int, width: int = 1, height: int = 1):
        """
        Add a static rectangular obstacle.

        Args:
            x, y: Top-left corner
            width, height: Dimensions
        """
        for dx in range(width):
            for dy in range(height):
                self.static_obstacles.add((x + dx, y + dy))

    def clear_obstacles(self):
        """Remove all static obstacles."""
        self.static_obstacles.clear()

    def route_single(self, droplet: Droplet,
                     avoid_droplets: Optional[Set[int]] = None) -> Optional[List[Tuple[int, int, int]]]:
        """
        Route a single droplet using A* search.

        Args:
            droplet: Droplet to route
            avoid_droplets: Set of droplet IDs to avoid (if None, avoid all)

        Returns:
            Path as list of (x, y, t) tuples, or None if no path found
        """
        avoid_droplets = avoid_droplets or set()
        start = (droplet.start[0], droplet.start[1], droplet.start_time)
        goal = droplet.end

        # Priority queue: (f_score, counter, node)
        counter = 0
        open_set = [(self._heuristic(droplet.start, goal), counter,
                    AStarNode(f_score=0, g_score=0,
                             x=start[0], y=start[1], t=start[2]))]

        # Closed set: (x, y, t) -> g_score
        closed_set: Dict[Tuple[int, int, int], int] = {}

        # For path reconstruction
        came_from: Dict[Tuple[int, int, int], Tuple[int, int, int]] = {}

        while open_set:
            f, _, current = heapq.heappop(open_set)

            # Check if reached goal
            if (current.x, current.y) == goal:
                # Reconstruct path
                path = []
                node = (current.x, current.y, current.t)
                while node in came_from:
                    path.append(node)
                    node = came_from[node]
                path.append(start)
                path.reverse()
                return path

            # Skip if already processed with better g_score
            pos = current.pos()
            if pos in closed_set and closed_set[pos] <= current.g_score:
                continue
            closed_set[pos] = current.g_score

            # Expand neighbors
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)]:  # 4-direction + wait
                nx, ny = current.x + dx, current.y + dy
                nt = current.t + 1

                # Check deadline
                if nt > droplet.deadline:
                    continue

                # Check bounds
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue

                # Check static obstacles
                if (nx, ny) in self.static_obstacles:
                    continue

                # Check reservations
                if not self._is_valid_move(nx, ny, nt, droplet.id, avoid_droplets):
                    continue

                new_g = current.g_score + 1
                new_pos = (nx, ny, nt)

                if new_pos in closed_set and closed_set[new_pos] <= new_g:
                    continue

                new_f = new_g + self._heuristic((nx, ny), goal)
                counter += 1
                heapq.heappush(open_set, (new_f, counter,
                                         AStarNode(f_score=new_f, g_score=new_g,
                                                  x=nx, y=ny, t=nt)))
                came_from[new_pos] = pos

        return None  # No path found

    def route_multiple(self, droplets: List[Droplet],
                       strategy: str = "prioritized") -> Dict[int, List[Tuple[int, int, int]]]:
        """
        Route multiple droplets with conflict avoidance.

        Args:
            droplets: List of droplets to route
            strategy: "prioritized" (route in order), "iterative" (resolve conflicts)

        Returns:
            Dictionary mapping droplet_id to path
        """
        if strategy == "prioritized":
            return self._route_prioritized(droplets)
        elif strategy == "iterative":
            return self._route_iterative(droplets)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _route_prioritized(self, droplets: List[Droplet]) -> Dict[int, List[Tuple[int, int, int]]]:
        """
        Route droplets in priority order.
        Earlier droplets reserve space; later ones must avoid them.
        """
        # Sort by deadline (earlier deadline = higher priority)
        sorted_droplets = sorted(droplets, key=lambda d: d.deadline)

        results = {}
        self.reservations.clear()
        self.blocked_cells.clear()

        for droplet in sorted_droplets:
            path = self.route_single(droplet)

            if path:
                results[droplet.id] = path
                self._add_reservations(droplet.id, path)
            else:
                print(f"Warning: Could not route droplet {droplet.id}")
                results[droplet.id] = None

        return results

    def _route_iterative(self, droplets: List[Droplet],
                        max_iterations: int = 10) -> Dict[int, List[Tuple[int, int, int]]]:
        """
        Iterative routing with conflict resolution.

        If droplets collide, re-route with updated priorities.
        """
        # Initial prioritized routing
        results = self._route_prioritized(droplets)

        for iteration in range(max_iterations):
            # Check for conflicts
            conflicts = self._detect_conflicts(results)

            if not conflicts:
                break

            print(f"Iteration {iteration + 1}: Resolving {len(conflicts)} conflicts")

            # Increase priority of conflicting droplets and re-route
            for conflict in conflicts:
                # Simple strategy: re-route the later droplet
                later_id = max(conflict['droplets'])
                droplet = next(d for d in droplets if d.id == later_id)

                # Remove old reservations
                if later_id in results and results[later_id]:
                    self._remove_reservations(later_id, results[later_id])

                # Re-route avoiding other droplets
                other_droplets = set(conflict['droplets']) - {later_id}
                new_path = self.route_single(droplet, avoid_droplets=other_droplets)

                if new_path:
                    results[later_id] = new_path
                    self._add_reservations(later_id, new_path)

        return results

    def _is_valid_move(self, x: int, y: int, t: int,
                      droplet_id: int, avoid_droplets: Set[int]) -> bool:
        """
        Check if a move is valid (not blocked).

        Checks:
        - Direct collision
        - Fluidic constraint (electrode interference)
        """
        # Check direct reservation
        if (x, y, t) in self.reservations:
            other_id = self.reservations[(x, y, t)]
            if other_id != droplet_id and other_id not in avoid_droplets:
                return False

        # Check fluidic constraint (block adjacent cells)
        for dx in range(-self.FLUIDIC_CONSTRAINT, self.FLUIDIC_CONSTRAINT + 1):
            for dy in range(-self.FLUIDIC_CONSTRAINT, self.FLUIDIC_CONSTRAINT + 1):
                if dx == 0 and dy == 0:
                    continue
                blocked_key = (x + dx, y + dy, t)
                if blocked_key in self.blocked_cells:
                    other_id = self.blocked_cells[blocked_key]
                    if other_id != droplet_id and other_id not in avoid_droplets:
                        return False

        return True

    def _add_reservations(self, droplet_id: int, path: List[Tuple[int, int, int]]):
        """Add path to reservation tables."""
        for x, y, t in path:
            self.reservations[(x, y, t)] = droplet_id

            # Block adjacent cells for fluidic constraint
            for dx in range(-self.FLUIDIC_CONSTRAINT, self.FLUIDIC_CONSTRAINT + 1):
                for dy in range(-self.FLUIDIC_CONSTRAINT, self.FLUIDIC_CONSTRAINT + 1):
                    self.blocked_cells[(x + dx, y + dy, t)] = droplet_id

    def _remove_reservations(self, droplet_id: int, path: List[Tuple[int, int, int]]):
        """Remove path from reservation tables."""
        for x, y, t in path:
            key = (x, y, t)
            if key in self.reservations and self.reservations[key] == droplet_id:
                del self.reservations[key]

            for dx in range(-self.FLUIDIC_CONSTRAINT, self.FLUIDIC_CONSTRAINT + 1):
                for dy in range(-self.FLUIDIC_CONSTRAINT, self.FLUIDIC_CONSTRAINT + 1):
                    blocked_key = (x + dx, y + dy, t)
                    if blocked_key in self.blocked_cells and \
                       self.blocked_cells[blocked_key] == droplet_id:
                        del self.blocked_cells[blocked_key]

    def _detect_conflicts(self, results: Dict[int, List[Tuple[int, int, int]]]) -> List[Dict]:
        """Detect conflicts between routed droplets."""
        conflicts = []
        occupancy = {}  # (x, y, t) -> droplet_id

        for droplet_id, path in results.items():
            if not path:
                continue

            for x, y, t in path:
                key = (x, y, t)
                if key in occupancy:
                    other_id = occupancy[key]
                    conflicts.append({
                        'type': 'collision',
                        'position': (x, y),
                        'time': t,
                        'droplets': [other_id, droplet_id]
                    })
                occupancy[key] = droplet_id

        return conflicts

    def _heuristic(self, pos: Tuple[int, int], goal: Tuple[int, int]) -> int:
        """Manhattan distance heuristic."""
        return abs(pos[0] - goal[0]) + abs(pos[1] - goal[1])

    def validate_routes(self, routes: Dict[int, List[Tuple[int, int, int]]]) -> List[str]:
        """Validate that routes satisfy all constraints."""
        violations = []

        # Check for collisions
        occupancy = {}
        for droplet_id, path in routes.items():
            if not path:
                violations.append(f"Droplet {droplet_id}: No path found")
                continue

            for i, (x, y, t) in enumerate(path):
                # Check bounds
                if not (0 <= x < self.width and 0 <= y < self.height):
                    violations.append(f"Droplet {droplet_id}: Out of bounds at ({x}, {y})")

                # Check static obstacles
                if (x, y) in self.static_obstacles:
                    violations.append(f"Droplet {droplet_id}: Passes through obstacle at ({x}, {y})")

                # Check collision
                key = (x, y, t)
                if key in occupancy:
                    violations.append(
                        f"Collision: Droplets {occupancy[key]} and {droplet_id} at ({x}, {y}, {t})"
                    )
                occupancy[key] = droplet_id

                # Check continuity (adjacent positions)
                if i > 0:
                    px, py, pt = path[i - 1]
                    if t != pt + 1:
                        violations.append(f"Droplet {droplet_id}: Time discontinuity at step {i}")
                    if abs(x - px) + abs(y - py) > 1:
                        violations.append(f"Droplet {droplet_id}: Jump at step {i}")

        return violations

    def get_route_statistics(self, routes: Dict[int, List[Tuple[int, int, int]]]) -> Dict:
        """Calculate statistics for a set of routes."""
        total_length = sum(len(path) for path in routes.values() if path)
        successful = sum(1 for path in routes.values() if path)

        return {
            'total_routes': len(routes),
            'successful_routes': successful,
            'failed_routes': len(routes) - successful,
            'total_path_length': total_length,
            'avg_path_length': total_length / successful if successful > 0 else 0,
            'max_time': max((path[-1][2] for path in routes.values() if path), default=0)
        }
