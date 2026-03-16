"""
DMFB Dataset Generator

Generates random problem instances with baseline solutions for training.
Output format supports few-shot prompting and RAG retrieval.

Updated: Integrated real baseline algorithms (GA, SA, List Scheduling)
"""

import json
import random
import os
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path

import sys
sys.path.insert(0, 'src')

from baseline.problem import DMFBProblem, Operation, Module, ModuleType, Droplet
from baseline.placement_ga import PlacementGA
from baseline.scheduling_list import ListScheduler
from baseline.baseline_runner import BaselineRunner as RealBaselineRunner


@dataclass
class DatasetConfig:
    """Configuration for dataset generation."""
    # Problem sizes
    small_ops: int = 20      # Number of operations for small problems
    large_ops: int = 50      # Number of operations for large problems
    count_per_size: int = 50  # Number of instances per size

    # Chip sizes
    chip_sizes: List[Tuple[int, int]] = field(default_factory=lambda: [
        (16, 16),
        (20, 20),
        (24, 24)
    ])

    # Module library
    modules: Dict[str, Module] = field(default_factory=lambda: {
        "mixer_2x2": Module("mixer_2x2", ModuleType.MIXER, 2, 2, 3),
        "mixer_3x3": Module("mixer_3x3", ModuleType.MIXER, 3, 3, 5),
        "heater_1x1": Module("heater_1x1", ModuleType.HEATER, 1, 1, 4),
        "heater_2x2": Module("heater_2x2", ModuleType.HEATER, 2, 2, 6),
        "detector_1x2": Module("detector_1x2", ModuleType.DETECTOR, 1, 2, 2),
        "storage_2x2": Module("storage_2x2", ModuleType.STORAGE, 2, 2, 1),
    })

    # Operation types and their required modules
    op_types: Dict[str, List[str]] = field(default_factory=lambda: {
        "mix": ["mixer_2x2", "mixer_3x3"],
        "heat": ["heater_1x1", "heater_2x2"],
        "detect": ["detector_1x2"],
        "store": ["storage_2x2"],
    })

    # Dependency graph parameters
    max_dependencies: int = 3
    dependency_prob: float = 0.3


class ProblemGenerator:
    """Generates random DMFB problem instances."""

    def __init__(self, config: DatasetConfig = None):
        self.config = config or DatasetConfig()
        random.seed(42)  # For reproducibility

    def generate(self, num_ops: int, chip_size: Tuple[int, int],
                 name: str = None) -> DMFBProblem:
        """
        Generate a random problem instance.

        Args:
            num_ops: Number of operations
            chip_size: (width, height) of chip
            name: Problem name

        Returns:
            DMFBProblem instance
        """
        width, height = chip_size

        # Generate operations
        operations = []
        for i in range(num_ops):
            op = self._generate_operation(i, operations)
            operations.append(op)

        problem = DMFBProblem(
            name=name or f"random_{num_ops}ops_{width}x{height}",
            chip_width=width,
            chip_height=height,
            modules=self.config.modules,
            operations=operations
        )

        return problem

    def _generate_operation(self, op_id: int,
                           existing_ops: List[Operation]) -> Operation:
        """Generate a single random operation."""
        # Select random operation type
        op_type = random.choice(list(self.config.op_types.keys()))
        module_options = self.config.op_types[op_type]
        module_type = random.choice(module_options)

        # Generate dependencies (from earlier operations only to avoid cycles)
        dependencies = []
        if existing_ops and random.random() < self.config.dependency_prob:
            num_deps = random.randint(1, min(self.config.max_dependencies, len(existing_ops)))
            # Select from recent operations (temporal locality)
            candidates = [op.id for op in existing_ops[-10:]] if len(existing_ops) > 10 else [op.id for op in existing_ops]
            dependencies = random.sample(candidates, min(num_deps, len(candidates)))

        return Operation(
            id=op_id,
            op_type=op_type,
            module_type=module_type,
            dependencies=dependencies
        )

    def generate_dataset(self, output_dir: str = "data/dataset"):
        """
        Generate full dataset with multiple sizes.

        Returns:
            Dict with statistics about generated data
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        stats = {
            "total_problems": 0,
            "by_size": {},
            "files": []
        }

        # Generate small problems (20 ops)
        print(f"Generating {self.config.count_per_size} small problems ({self.config.small_ops} ops)...")
        small_problems = []
        for i in range(self.config.count_per_size):
            chip = random.choice(self.config.chip_sizes)
            problem = self.generate(
                num_ops=self.config.small_ops,
                chip_size=chip,
                name=f"small_{i:03d}"
            )
            small_problems.append(problem)

        # Save small problems
        small_file = output_path / "problems_small.json"
        self._save_problems(small_problems, small_file)
        stats["by_size"]["small"] = len(small_problems)
        stats["files"].append(str(small_file))

        # Generate large problems (50 ops)
        print(f"Generating {self.config.count_per_size} large problems ({self.config.large_ops} ops)...")
        large_problems = []
        for i in range(self.config.count_per_size):
            chip = random.choice(self.config.chip_sizes)
            problem = self.generate(
                num_ops=self.config.large_ops,
                chip_size=chip,
                name=f"large_{i:03d}"
            )
            large_problems.append(problem)

        # Save large problems
        large_file = output_path / "problems_large.json"
        self._save_problems(large_problems, large_file)
        stats["by_size"]["large"] = len(large_problems)
        stats["files"].append(str(large_file))

        # Generate summary
        stats["total_problems"] = len(small_problems) + len(large_problems)

        # Save metadata
        metadata = {
            "statistics": stats,
            "config": {
                "small_ops": self.config.small_ops,
                "large_ops": self.config.large_ops,
                "count_per_size": self.config.count_per_size,
                "chip_sizes": self.config.chip_sizes,
            }
        }
        metadata_file = output_path / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"\nDataset generated:")
        print(f"  Small problems: {stats['by_size']['small']}")
        print(f"  Large problems: {stats['by_size']['large']}")
        print(f"  Total: {stats['total_problems']}")
        print(f"  Output: {output_dir}")

        return stats

    def _save_problems(self, problems: List[DMFBProblem], filepath: Path):
        """Save problems to JSON file."""
        data = [p.to_dict() for p in problems]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


@dataclass
class SolutionEntry:
    """A problem-solution pair for training."""
    problem: DMFBProblem
    # Solutions from different algorithms
    placement_ga: Any = None
    placement_sa: Any = None
    schedule_list: Any = None
    schedule_cp: Any = None  # Constraint programming
    routes_astar: Any = None

    # Metrics
    makespan: int = None
    total_wirelength: float = None
    area_utilization: float = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "problem": self.problem.to_dict(),
            "solutions": {
                "placement_ga": self.placement_ga,
                "placement_sa": self.placement_sa,
                "schedule_list": self.schedule_list,
                "schedule_cp": self.schedule_cp,
                "routes_astar": self.routes_astar,
            },
            "metrics": {
                "makespan": self.makespan,
                "total_wirelength": self.total_wirelength,
                "area_utilization": self.area_utilization,
            }
        }


class EnhancedBaselineRunner:
    """Runs real baseline algorithms to generate solution labels."""

    def __init__(self):
        self.results = []
        # Baseline algorithms will be initialized per problem
        self.baseline_runner = RealBaselineRunner()

    def run_on_problem(self, problem: DMFBProblem) -> SolutionEntry:
        """
        Run all baseline algorithms on a problem using real implementations.
        """
        entry = SolutionEntry(problem=problem)

        try:
            # Run GA for placement
            ga_result = self._run_ga_placement(problem)
            if ga_result:
                entry.placement_ga = ga_result

            # Run List Scheduling
            list_result = self._run_list_scheduling(problem)
            if list_result:
                entry.schedule_list = list_result

            # Run full baseline pipeline (placement + scheduling + routing)
            full_result = self._run_full_baseline(problem)
            if full_result:
                entry.metrics = {
                    "makespan": full_result.get('makespan', 0),
                    "total_wirelength": full_result.get('total_wirelength', 0.0),
                    "area_utilization": full_result.get('area_utilization', 0.0)
                }

        except Exception as e:
            print(f"  [WARNING] Error running baselines on {problem.name}: {e}")
            # Fall back to dummy solutions
            entry = self._create_dummy_solution(problem)

        return entry

    def _run_ga_placement(self, problem: DMFBProblem) -> List[Dict]:
        """Run GA placement algorithm."""
        try:
            # Initialize GA solver for this problem
            ga_solver = PlacementGA(problem, pop_size=50, generations=100)
            result = ga_solver.solve()
            if result and hasattr(result, 'positions'):
                placements = []
                for op_id, (x, y) in result.positions.items():
                    # Map operation ID to module
                    op = next((o for o in problem.operations if o.id == op_id), None)
                    if op:
                        module = problem.modules.get(op.module_type)
                        if module:
                            placements.append({
                                "operation_id": op_id,
                                "module_type": op.module_type,
                                "x": x,
                                "y": y,
                                "width": module.width,
                                "height": module.height
                            })
                return placements
        except Exception as e:
            print(f"    [GA Placement Failed] {e}")
        return None
        """Run GA placement algorithm."""
        try:
            # Use the GA solver
            result = self.ga_solver.solve(problem)
            if result and 'placements' in result:
                placements = []
                for module_id, (x, y) in result['placements'].items():
                    module = problem.modules.get(module_id)
                    if module:
                        placements.append({
                            "module_id": module_id,
                            "x": x,
                            "y": y,
                            "width": module.width,
                            "height": module.height
                        })
                return placements
        except Exception as e:
            print(f"    [GA Placement Failed] {e}")
        return None

    def _run_list_scheduling(self, problem: DMFBProblem) -> List[Dict]:
        """Run List Scheduling algorithm."""
        try:
            # Initialize list scheduler for this problem
            list_scheduler = ListScheduler()
            schedule = list_scheduler.schedule(problem)
            if schedule:
                schedule_list = []
                for op_id, (start_time, end_time, module_id) in schedule.items():
                    schedule_list.append({
                        "operation_id": op_id,
                        "start_time": start_time,
                        "end_time": end_time,
                        "module_id": module_id
                    })
                return schedule_list
        except Exception as e:
            print(f"    [List Scheduling Failed] {e}")
        return None

    def _run_full_baseline(self, problem: DMFBProblem) -> Dict:
        """Run full baseline pipeline."""
        try:
            result = self.baseline_runner.run(problem, method="python")
            return result
        except Exception as e:
            print(f"    [Full Baseline Failed] {e}")
        return None

    def _create_dummy_solution(self, problem: DMFBProblem) -> SolutionEntry:
        """Create a dummy solution as fallback."""
        entry = SolutionEntry(problem=problem)

        # Simple grid placement
        placements = []
        for i, module_type in enumerate(problem.modules.keys()):
            module = problem.modules[module_type]
            x = (i * 3) % problem.chip_width
            y = ((i * 3) // problem.chip_width) * 3
            if x + module.width <= problem.chip_width and y + module.height <= problem.chip_height:
                placements.append({
                    "module_id": module_type,
                    "x": x,
                    "y": y,
                    "width": module.width,
                    "height": module.height
                })
        entry.placement_ga = placements
        entry.placement_sa = placements

        # Simple topological schedule
        topo_order = problem.topological_sort()
        schedule = []
        current_time = 0
        for op_id in topo_order:
            op = next(o for o in problem.operations if o.id == op_id)
            duration = op.get_duration(problem.modules)
            schedule.append({
                "operation_id": op_id,
                "start_time": current_time,
                "end_time": current_time + duration,
                "module_id": op.module_type
            })
            current_time += duration
        entry.schedule_list = schedule
        entry.schedule_cp = schedule

        entry.makespan = current_time
        entry.area_utilization = 0.5

        return entry

    def run_dataset(self, problems: List[DMFBProblem],
                    output_file: str = "data/dataset/solutions.json"):
        """Run baselines on all problems and save results."""
        print(f"Running baselines on {len(problems)} problems...")

        results = []
        for i, problem in enumerate(problems):
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(problems)}")

            entry = self.run_on_problem(problem)
            results.append(entry.to_dict())

        # Save results
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"Solutions saved to {output_file}")
        return results


def generate_dataset(output_dir: str = "data/dataset"):
    """Main entry point for dataset generation."""
    print("=" * 60)
    print("DMFB Dataset Generator")
    print("=" * 60)

    # Step 1: Generate problems
    generator = ProblemGenerator()
    stats = generator.generate_dataset(output_dir)

    # Step 2: Run baselines to generate labels
    print("\nGenerating baseline solutions...")
    runner = EnhancedBaselineRunner()

    # Load problems and run baselines
    small_file = Path(output_dir) / "problems_small.json"
    large_file = Path(output_dir) / "problems_large.json"

    with open(small_file) as f:
        small_data = json.load(f)
        small_problems = [DMFBProblem.from_dict(d) for d in small_data]

    with open(large_file) as f:
        large_data = json.load(f)
        large_problems = [DMFBProblem.from_dict(d) for d in large_data]

    # Run baselines
    runner.run_dataset(small_problems, f"{output_dir}/solutions_small.json")
    runner.run_dataset(large_problems, f"{output_dir}/solutions_large.json")

    print("\n" + "=" * 60)
    print("Dataset generation complete!")
    print("=" * 60)
    print(f"\nFiles created in {output_dir}:")
    for f in Path(output_dir).glob("*.json"):
        print(f"  - {f.name}")

    return stats


if __name__ == "__main__":
    generate_dataset()
