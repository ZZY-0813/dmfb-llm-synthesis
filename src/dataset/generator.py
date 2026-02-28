"""
DMFB problem instance generator.

Generates diverse problem instances for:
- Training data generation
- Algorithm evaluation
- Stress testing

Supports various patterns: linear chains, parallel branches, forks/joins,
random DAGs, and application-specific patterns (PCR, drug screening, etc.)
"""

import random
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from ..baseline.problem import DMFBProblem, Module, Operation, ModuleType


@dataclass
class GenerationConfig:
    """Configuration for problem generation."""
    chip_sizes: List[Tuple[int, int]] = None
    num_operations_range: Tuple[int, int] = (10, 100)
    module_types: List[str] = None
    dag_patterns: List[str] = None
    seed: Optional[int] = None

    def __post_init__(self):
        if self.chip_sizes is None:
            self.chip_sizes = [(32, 32), (64, 64)]
        if self.module_types is None:
            self.module_types = ['mix', 'heat', 'detect']
        if self.dag_patterns is None:
            self.dag_patterns = ['linear', 'parallel', 'random']


class ProblemGenerator:
    """
    Generator for DMFB synthesis problem instances.

    Example:
        >>> gen = ProblemGenerator(seed=42)
        >>>
        >>> # Generate a single problem
        >>> problem = gen.generate(num_ops=50, pattern='random')
        >>>
        >>> # Generate a dataset
        >>> gen.generate_dataset(
        ...     output_dir='data/training',
        ...     sizes=[20, 50, 100],
        ...     num_per_size=100
        ... )
    """

    # Standard module library
    DEFAULT_MODULES = {
        'mixer_3x3': Module('mixer_3x3', ModuleType.MIXER, 3, 3, 5),
        'mixer_4x4': Module('mixer_4x4', ModuleType.MIXER, 4, 4, 8),
        'heater_2x2': Module('heater_2x2', ModuleType.HEATER, 2, 2, 10),
        'detector_1x1': Module('detector_1x1', ModuleType.DETECTOR, 1, 1, 2),
        'storage_2x2': Module('storage_2x2', ModuleType.STORAGE, 2, 2, 1),
    }

    def __init__(self, config: Optional[GenerationConfig] = None,
                 seed: Optional[int] = None):
        """
        Initialize generator.

        Args:
            config: Generation configuration
            seed: Random seed (overrides config.seed if provided)
        """
        self.config = config or GenerationConfig()
        if seed is not None:
            self.config.seed = seed

        if self.config.seed:
            random.seed(self.config.seed)

    def generate(self,
                 num_ops: int,
                 chip_size: Tuple[int, int] = (64, 64),
                 pattern: str = 'random',
                 name: Optional[str] = None) -> DMFBProblem:
        """
        Generate a single problem instance.

        Args:
            num_ops: Number of operations
            chip_size: (width, height) of chip
            pattern: DAG pattern ('linear', 'parallel', 'fork_join', 'random', 'pcr')
            name: Problem name (auto-generated if None)

        Returns:
            DMFBProblem instance
        """
        if name is None:
            name = f"{pattern}_{num_ops}_{random.randint(1000, 9999)}"

        # Select module library (subset for this problem)
        modules = self._select_modules(num_ops)

        # Generate operations
        operations = self._generate_operations(num_ops, modules)

        # Generate dependency graph
        dependencies = self._generate_dag(num_ops, pattern)
        for i, deps in enumerate(dependencies):
            operations[i].dependencies = deps

        return DMFBProblem(
            name=name,
            chip_width=chip_size[0],
            chip_height=chip_size[1],
            modules=modules,
            operations=operations
        )

    def generate_dataset(self,
                         output_dir: str,
                         sizes: List[int],
                         num_per_size: int = 100,
                         patterns: Optional[List[str]] = None,
                         formats: List[str] = None):
        """
        Generate a dataset of problems.

        Args:
            output_dir: Output directory
            sizes: List of problem sizes (number of operations)
            num_per_size: Number of problems per size
            patterns: List of patterns to generate (default: all)
            formats: Output formats ('json', 'txt')
        """
        if patterns is None:
            patterns = self.config.dag_patterns

        if formats is None:
            formats = ['json']

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        total_generated = 0

        for size in sizes:
            for pattern in patterns:
                print(f"\nGenerating {num_per_size} problems: "
                      f"size={size}, pattern={pattern}")

                for i in range(num_per_size):
                    # Vary chip size based on problem size
                    chip_size = self._select_chip_size(size)

                    problem = self.generate(
                        num_ops=size,
                        chip_size=chip_size,
                        pattern=pattern,
                        name=f"{pattern}_{size}_{i:04d}"
                    )

                    # Save in requested formats
                    for fmt in formats:
                        self._save_problem(problem, output_path, fmt)

                    total_generated += 1

        print(f"\n{'='*50}")
        print(f"Dataset generation complete!")
        print(f"Total problems: {total_generated}")
        print(f"Output directory: {output_path.absolute()}")

    def _select_modules(self, num_ops: int) -> Dict[str, Module]:
        """Select appropriate module library for problem size."""
        # For small problems, use fewer module types
        if num_ops < 20:
            selected = ['mixer_3x3', 'heater_2x2', 'detector_1x1']
        elif num_ops < 50:
            selected = ['mixer_3x3', 'mixer_4x4', 'heater_2x2', 'detector_1x1']
        else:
            selected = list(self.DEFAULT_MODULES.keys())

        return {k: self.DEFAULT_MODULES[k] for k in selected}

    def _generate_operations(self, num_ops: int,
                            modules: Dict[str, Module]) -> List[Operation]:
        """Generate operations with random types."""
        operations = []
        module_names = list(modules.keys())

        for i in range(1, num_ops + 1):
            # Select module type based on typical assay patterns
            if i == num_ops:  # Last operation is usually detection
                module_type = 'detector_1x1' if 'detector_1x1' in modules else random.choice(module_names)
            elif i == 1:  # First operations are often mixing
                module_type = 'mixer_3x3' if 'mixer_3x3' in modules else random.choice(module_names)
            else:
                module_type = random.choice(module_names)

            module = modules[module_type]

            op = Operation(
                id=i,
                op_type=module.type.value,
                module_type=module_type,
                dependencies=[]
            )
            operations.append(op)

        return operations

    def _generate_dag(self, n: int, pattern: str) -> List[List[int]]:
        """Generate dependency graph based on pattern."""
        if pattern == 'linear':
            return self._linear_dag(n)
        elif pattern == 'parallel':
            return self._parallel_dag(n)
        elif pattern == 'fork_join':
            return self._fork_join_dag(n)
        elif pattern == 'pcr':
            return self._pcr_dag(n)
        elif pattern == 'random':
            return self._random_dag(n)
        else:
            raise ValueError(f"Unknown pattern: {pattern}")

    def _linear_dag(self, n: int) -> List[List[int]]:
        """Linear chain: 1 -> 2 -> 3 -> ..."""
        deps = [[] for _ in range(n)]
        for i in range(1, n):
            deps[i] = [i]  # 1-indexed: operation i+1 depends on i
        return deps

    def _parallel_dag(self, n: int) -> List[List[int]]:
        """Multiple parallel chains meeting at join points."""
        deps = [[] for _ in range(n)]

        # Create 2-3 parallel branches
        num_branches = min(3, max(2, n // 10))
        branch_size = n // num_branches

        # Build branches
        for branch in range(num_branches):
            start = branch * branch_size
            end = start + branch_size if branch < num_branches - 1 else n

            for i in range(start + 1, end):
                deps[i] = [i]  # Within-branch dependency

        # Add occasional cross-branch dependencies
        for i in range(n):
            if random.random() < 0.1 and i > 0:  # 10% chance
                potential_deps = list(range(1, i))
                if potential_deps:
                    extra_dep = random.choice(potential_deps)
                    if extra_dep not in deps[i]:
                        deps[i].append(extra_dep)

        return deps

    def _fork_join_dag(self, n: int) -> List[List[int]]:
        """Fork into parallel branches then join."""
        deps = [[] for _ in range(n)]

        if n < 5:
            return self._linear_dag(n)

        # Fork point: operation 1
        # Join point: operation n
        fork_size = min(5, n // 3)
        join_size = min(5, n // 3)
        parallel_size = n - fork_size - join_size

        # Fork section
        for i in range(1, fork_size):
            deps[i] = [i]

        # Parallel section depends on fork
        for i in range(fork_size, fork_size + parallel_size):
            deps[i] = [fork_size] if fork_size > 0 else []

        # Join section depends on parallel section
        for i in range(fork_size + parallel_size, n):
            deps[i] = list(range(fork_size + 1, fork_size + parallel_size + 1))

        return deps

    def _pcr_dag(self, n: int) -> List[List[int]]:
        """
        PCR (Polymerase Chain Reaction) pattern.
        Cycles of: mix -> heat -> (optionally detect)
        """
        deps = [[] for _ in range(n)]

        # Assume 3 operations per cycle: mix, heat, detect
        cycle_size = 3
        num_cycles = n // cycle_size

        op_idx = 0
        for cycle in range(num_cycles):
            cycle_start = op_idx + 1

            # Operations within cycle
            for i in range(cycle_size):
                if op_idx >= n:
                    break

                if i == 0:  # Mix: depends on previous cycle's detect
                    if cycle > 0:
                        deps[op_idx] = [op_idx]  # Previous operation
                else:  # Heat/Detect: depends on previous in cycle
                    deps[op_idx] = [op_idx]

                op_idx += 1

        return deps

    def _random_dag(self, n: int, edge_prob: float = 0.15) -> List[List[int]]:
        """Random DAG with controlled edge probability."""
        deps = [[] for _ in range(n)]

        for i in range(1, n):
            # Each operation depends on 1-3 previous operations
            num_deps = random.randint(1, min(3, i))
            potential = list(range(1, i + 1))

            # Prefer recent dependencies (temporal locality)
            weights = [1.0 / (i - j + 1) for j in range(i)]
            total = sum(weights)
            weights = [w / total for w in weights]

            selected = random.choices(potential, weights=weights, k=num_deps)
            deps[i] = list(set(selected))  # Remove duplicates

        return deps

    def _select_chip_size(self, num_ops: int) -> Tuple[int, int]:
        """Select appropriate chip size for problem size."""
        if num_ops < 20:
            return (32, 32)
        elif num_ops < 50:
            return (48, 48)
        elif num_ops < 100:
            return (64, 64)
        else:
            return (96, 96)

    def _save_problem(self, problem: DMFBProblem, output_dir: Path, fmt: str):
        """Save problem in specified format."""
        if fmt == 'json':
            filepath = output_dir / f"{problem.name}.json"
            with open(filepath, 'w') as f:
                json.dump(problem.to_dict(), f, indent=2)

        elif fmt == 'txt':
            # Simple text format for external tools
            filepath = output_dir / f"{problem.name}.txt"
            with open(filepath, 'w') as f:
                f.write(f"GRID {problem.chip_width} {problem.chip_height}\n")
                for name, mod in problem.modules.items():
                    f.write(f"MODULE {name} {mod.width} {mod.height} {mod.exec_time}\n")
                for op in problem.operations:
                    deps = ','.join(map(str, op.dependencies)) if op.dependencies else '0'
                    f.write(f"OP {op.id} {op.op_type} {op.module_type} {deps}\n")


def load_problem_dataset(directory: str) -> List[DMFBProblem]:
    """Load all problems from a directory."""
    path = Path(directory)
    problems = []

    for file in path.glob("*.json"):
        with open(file) as f:
            data = json.load(f)
            problems.append(DMFBProblem.from_dict(data))

    return sorted(problems, key=lambda p: p.name)
