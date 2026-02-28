"""
Core data structures for DMFB synthesis problems.

This module defines the fundamental data structures used throughout
the DMFB synthesis framework, including chip specifications,
modules, operations, and droplets.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
from enum import Enum
import json
import numpy as np


class ModuleType(Enum):
    """Types of functional modules in DMFB."""
    MIXER = "mixer"
    HEATER = "heater"
    DETECTOR = "detector"
    STORAGE = "storage"
    DISPENSER = "dispenser"
    WASTE = "waste"


@dataclass
class Module:
    """
    A functional module on the DMFB chip.

    Attributes:
        name: Unique identifier for this module type
        type: Module type (mixer, heater, etc.)
        width: Width in electrodes
        height: Height in electrodes
        exec_time: Execution time in ticks
        position: Optional fixed position (x, y) if pre-placed
    """
    name: str
    type: ModuleType
    width: int
    height: int
    exec_time: int
    position: Optional[Tuple[int, int]] = None

    def area(self) -> int:
        """Return the area of this module in electrodes."""
        return self.width * self.height

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "type": self.type.value,
            "width": self.width,
            "height": self.height,
            "exec_time": self.exec_time,
            "position": self.position
        }

    @staticmethod
    def from_dict(data: dict) -> "Module":
        """Create Module from dictionary."""
        return Module(
            name=data["name"],
            type=ModuleType(data["type"]),
            width=data["width"],
            height=data["height"],
            exec_time=data["exec_time"],
            position=tuple(data["position"]) if data.get("position") else None
        )


@dataclass
class Operation:
    """
    An operation to be performed on the DMFB.

    Attributes:
        id: Unique operation identifier
        op_type: Operation type (mix, heat, detect, etc.)
        module_type: Required module type
        dependencies: List of operation IDs that must complete before this one
        duration: Execution duration in ticks (overrides module default if set)
        inputs: Input droplet IDs (for tracking)
        outputs: Output droplet IDs (for tracking)
    """
    id: int
    op_type: str
    module_type: str
    dependencies: List[int] = field(default_factory=list)
    duration: Optional[int] = None
    inputs: List[int] = field(default_factory=list)
    outputs: List[int] = field(default_factory=list)

    def get_duration(self, modules: Dict[str, Module]) -> int:
        """Get execution duration, using module default if not specified."""
        if self.duration is not None:
            return self.duration
        return modules[self.module_type].exec_time

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "op_type": self.op_type,
            "module_type": self.module_type,
            "dependencies": self.dependencies,
            "duration": self.duration,
            "inputs": self.inputs,
            "outputs": self.outputs
        }

    @staticmethod
    def from_dict(data: dict) -> "Operation":
        """Create Operation from dictionary."""
        return Operation(
            id=data["id"],
            op_type=data["op_type"],
            module_type=data["module_type"],
            dependencies=data.get("dependencies", []),
            duration=data.get("duration"),
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", [])
        )


@dataclass
class Droplet:
    """
    A droplet to be routed on the DMFB.

    Attributes:
        id: Unique droplet identifier
        start: Starting position (x, y)
        end: Destination position (x, y)
        start_time: Earliest start time
        deadline: Latest arrival time
        operation_id: Associated operation ID
        volume: Droplet volume (in normalized units)
    """
    id: int
    start: Tuple[int, int]
    end: Tuple[int, int]
    start_time: int
    deadline: int
    operation_id: Optional[int] = None
    volume: float = 1.0
    path: List[Tuple[int, int, int]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "start": list(self.start),
            "end": list(self.end),
            "start_time": self.start_time,
            "deadline": self.deadline,
            "operation_id": self.operation_id,
            "volume": self.volume,
            "path": [list(p) for p in self.path]
        }

    @staticmethod
    def from_dict(data: dict) -> "Droplet":
        """Create Droplet from dictionary."""
        d = Droplet(
            id=data["id"],
            start=tuple(data["start"]),
            end=tuple(data["end"]),
            start_time=data["start_time"],
            deadline=data["deadline"],
            operation_id=data.get("operation_id"),
            volume=data.get("volume", 1.0)
        )
        if "path" in data:
            d.path = [tuple(p) for p in data["path"]]
        return d


@dataclass
class DMFBProblem:
    """
    A complete DMFB synthesis problem.

    Attributes:
        name: Problem instance name
        chip_width: Chip width in electrodes
        chip_height: Chip height in electrodes
        modules: Dictionary of module types
        operations: List of operations to schedule
        droplets: Optional list of droplets (for routing-only problems)
    """
    name: str
    chip_width: int
    chip_height: int
    modules: Dict[str, Module]
    operations: List[Operation]
    droplets: Optional[List[Droplet]] = None

    def __post_init__(self):
        """Validate the problem instance."""
        if self.chip_width <= 0 or self.chip_height <= 0:
            raise ValueError("Chip dimensions must be positive")
        if not self.operations:
            raise ValueError("At least one operation required")

        # Validate operation dependencies
        op_ids = {op.id for op in self.operations}
        for op in self.operations:
            for dep in op.dependencies:
                if dep not in op_ids:
                    raise ValueError(f"Operation {op.id} depends on unknown operation {dep}")

    def get_dependency_graph(self) -> Dict[int, Set[int]]:
        """Build dependency graph as adjacency list."""
        graph = {op.id: set() for op in self.operations}
        for op in self.operations:
            for dep in op.dependencies:
                graph[dep].add(op.id)
        return graph

    def topological_sort(self) -> List[int]:
        """
        Return a topological sort of operations.

        Raises:
            ValueError: If dependency graph contains cycles.
        """
        from collections import deque

        # Calculate in-degrees
        in_degree = {op.id: 0 for op in self.operations}
        for op in self.operations:
            for dep in op.dependencies:
                in_degree[op.id] += 1

        # Kahn's algorithm
        queue = deque([op_id for op_id, deg in in_degree.items() if deg == 0])
        result = []

        while queue:
            op_id = queue.popleft()
            result.append(op_id)

            # Find all operations that depend on this one
            for op in self.operations:
                if op_id in op.dependencies:
                    in_degree[op.id] -= 1
                    if in_degree[op.id] == 0:
                        queue.append(op.id)

        if len(result) != len(self.operations):
            raise ValueError("Dependency graph contains cycles")

        return result

    def get_critical_path_length(self) -> int:
        """
        Calculate the critical path length (lower bound on makespan).

        Returns:
            Minimum possible makespan ignoring resource constraints.
        """
        # Longest path in DAG
        topo_order = self.topological_sort()
        earliest_start = {op.id: 0 for op in self.operations}

        for op_id in topo_order:
            op = next(o for o in self.operations if o.id == op_id)
            duration = op.get_duration(self.modules)
            finish_time = earliest_start[op_id] + duration

            # Update successors
            for succ in self.operations:
                if op_id in succ.dependencies:
                    earliest_start[succ.id] = max(earliest_start[succ.id], finish_time)

        return max(earliest_start[op.id] + op.get_duration(self.modules)
                  for op in self.operations)

    def estimate_resource_usage(self) -> Dict[str, int]:
        """Estimate maximum concurrent usage of each resource type."""
        usage = {name: 0 for name in self.modules}
        # This is a simplified estimate
        for op in self.operations:
            if op.module_type in usage:
                usage[op.module_type] += 1
        return usage

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "chip_width": self.chip_width,
            "chip_height": self.chip_height,
            "modules": {k: v.to_dict() for k, v in self.modules.items()},
            "operations": [op.to_dict() for op in self.operations],
            "droplets": [d.to_dict() for d in self.droplets] if self.droplets else None
        }

    @staticmethod
    def from_dict(data: dict) -> "DMFBProblem":
        """Create DMFBProblem from dictionary."""
        return DMFBProblem(
            name=data.get("name", "unnamed"),
            chip_width=data["chip_width"],
            chip_height=data["chip_height"],
            modules={k: Module.from_dict(v) for k, v in data["modules"].items()},
            operations=[Operation.from_dict(op) for op in data["operations"]],
            droplets=[Droplet.from_dict(d) for d in data["droplets"]] if data.get("droplets") else None
        )

    def save(self, filepath: str):
        """Save problem to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @staticmethod
    def load(filepath: str) -> "DMFBProblem":
        """Load problem from JSON file."""
        with open(filepath) as f:
            return DMFBProblem.from_dict(json.load(f))

    def __repr__(self) -> str:
        return (f"DMFBProblem({self.name}: {len(self.operations)} ops, "
                f"{self.chip_width}x{self.chip_height} grid, "
                f"CPL={self.get_critical_path_length()})")
