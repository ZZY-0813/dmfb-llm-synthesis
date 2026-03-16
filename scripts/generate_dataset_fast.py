"""
Fast Dataset Generator for DMFB

Generates problems with lightweight baseline solutions.
Uses simplified algorithms for speed instead of full GA.

Usage:
    python scripts/generate_dataset_fast.py --size 50 --output data/dataset
"""

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, 'src')

from baseline.problem import DMFBProblem
from data.dataset_generator import ProblemGenerator, DatasetConfig, SolutionEntry


class FastBaselineRunner:
    """Fast baseline runner using simplified algorithms."""

    def run_on_problem(self, problem: DMFBProblem) -> SolutionEntry:
        """Generate solution using fast algorithms."""
        entry = SolutionEntry(problem=problem)

        # Fast placement (greedy + local search)
        entry.placement_ga = self._fast_placement(problem)
        entry.placement_sa = entry.placement_ga

        # Fast scheduling (list scheduling with heuristic)
        entry.schedule_list = self._fast_schedule(problem)
        entry.schedule_cp = entry.schedule_list

        # Calculate metrics
        entry.makespan = self._calculate_makespan(entry.schedule_list)
        entry.area_utilization = self._calculate_area_util(entry.placement_ga, problem)

        return entry

    def _fast_placement(self, problem: DMFBProblem) -> list:
        """Greedy placement with minimal wirelength heuristic."""
        placements = []
        occupied = set()

        # Sort operations by dependency depth (deeper first)
        depths = self._calc_dependency_depths(problem)
        sorted_ops = sorted(problem.operations, key=lambda o: depths.get(o.id, 0), reverse=True)

        for op in sorted_ops:
            module = problem.modules.get(op.module_type)
            if not module:
                continue

            # Find position near dependencies
            best_pos = None
            best_cost = float('inf')

            # If has dependencies, try to place near them
            target_x, target_y = 0, 0
            if op.dependencies:
                # Calculate centroid of dependency positions
                dep_positions = []
                for dep_id in op.dependencies:
                    dep_placement = next((p for p in placements if p['operation_id'] == dep_id), None)
                    if dep_placement:
                        dep_positions.append((dep_placement['x'], dep_placement['y']))

                if dep_positions:
                    target_x = sum(p[0] for p in dep_positions) // len(dep_positions)
                    target_y = sum(p[1] for p in dep_positions) // len(dep_positions)

            # Search nearby positions
            for dx in range(0, max(problem.chip_width, problem.chip_height), 2):
                for dy in range(0, max(problem.chip_width, problem.chip_height), 2):
                    # Try 4 quadrants
                    for sx, sy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
                        x = target_x + dx * sx
                        y = target_y + dy * sy

                        if x < 0 or y < 0:
                            continue
                        if x + module.width > problem.chip_width:
                            continue
                        if y + module.height > problem.chip_height:
                            continue

                        # Check overlap
                        overlap = False
                        for px in range(x, x + module.width):
                            for py in range(y, y + module.height):
                                if (px, py) in occupied:
                                    overlap = True
                                    break
                            if overlap:
                                break

                        if not overlap:
                            # Calculate cost (Manhattan distance to dependencies)
                            cost = abs(x - target_x) + abs(y - target_y)
                            if cost < best_cost:
                                best_cost = cost
                                best_pos = (x, y)

                        if best_pos == (target_x, target_y):
                            break
                    if best_pos == (target_x, target_y):
                        break
                if best_pos == (target_x, target_y):
                    break

            if best_pos:
                x, y = best_pos
                placements.append({
                    'operation_id': op.id,
                    'module_type': op.module_type,
                    'x': x,
                    'y': y,
                    'width': module.width,
                    'height': module.height
                })
                # Mark occupied
                for px in range(x, x + module.width):
                    for py in range(y, y + module.height):
                        occupied.add((px, py))

        return placements

    def _calc_dependency_depths(self, problem: DMFBProblem) -> dict:
        """Calculate dependency depth for each operation."""
        depths = {}

        def get_depth(op_id):
            if op_id in depths:
                return depths[op_id]
            op = next((o for o in problem.operations if o.id == op_id), None)
            if not op or not op.dependencies:
                depths[op_id] = 0
                return 0
            max_dep_depth = max(get_depth(d) for d in op.dependencies)
            depths[op_id] = max_dep_depth + 1
            return depths[op_id]

        for op in problem.operations:
            get_depth(op.id)

        return depths

    def _fast_schedule(self, problem: DMFBProblem) -> list:
        """Fast list scheduling using topological order."""
        # Get topological order
        in_degree = {op.id: 0 for op in problem.operations}
        for op in problem.operations:
            for dep in op.dependencies:
                in_degree[op.id] += 1

        # Initialize with operations that have no dependencies
        ready = [op.id for op in problem.operations if in_degree[op.id] == 0]
        schedule = []
        current_time = 0
        completed = set()

        module_availability = {}  # module_id -> time when free

        while ready:
            # Sort ready queue by priority (heuristic: more dependents first)
            ready.sort(key=lambda oid: sum(1 for o in problem.operations if oid in o.dependencies), reverse=True)

            scheduled_this_round = []
            for op_id in ready:
                op = next(o for o in problem.operations if o.id == op_id)
                module = problem.modules.get(op.module_type)

                # Check if module is available
                module_ready = module_availability.get(op.module_type, 0)
                start_time = max(current_time, module_ready)

                # Check all dependencies are completed
                deps_satisfied = all(d in completed for d in op.dependencies)
                if not deps_satisfied:
                    continue

                # Check dependency timing
                max_dep_end = 0
                for dep_id in op.dependencies:
                    dep_sched = next((s for s in schedule if s['operation_id'] == dep_id), None)
                    if dep_sched:
                        max_dep_end = max(max_dep_end, dep_sched['end_time'])

                start_time = max(start_time, max_dep_end)
                duration = module.exec_time if module else 1

                schedule.append({
                    'operation_id': op_id,
                    'start_time': start_time,
                    'end_time': start_time + duration,
                    'module_id': op.module_type
                })

                module_availability[op.module_type] = start_time + duration
                scheduled_this_round.append(op_id)
                completed.add(op_id)

            # Update ready queue
            for op_id in scheduled_this_round:
                ready.remove(op_id)

            # Add newly ready operations
            for op in problem.operations:
                if op.id not in completed and op.id not in ready:
                    if all(d in completed for d in op.dependencies):
                        ready.append(op.id)

            if not scheduled_this_round and ready:
                # Advance time if we couldn't schedule anything
                current_time = min(module_availability.values()) if module_availability else current_time + 1

        return schedule

    def _calculate_makespan(self, schedule: list) -> int:
        """Calculate makespan from schedule."""
        if not schedule:
            return 0
        return max(s['end_time'] for s in schedule)

    def _calculate_area_util(self, placements: list, problem: DMFBProblem) -> float:
        """Calculate area utilization."""
        if not placements:
            return 0.0

        total_module_area = sum(p['width'] * p['height'] for p in placements)
        chip_area = problem.chip_width * problem.chip_height

        return total_module_area / chip_area if chip_area > 0 else 0.0

    def run_dataset(self, problems, output_file):
        """Run on all problems."""
        print(f"Running fast baselines on {len(problems)} problems...")

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


def main():
    parser = argparse.ArgumentParser(description='Generate DMFB dataset with baseline solutions')
    parser.add_argument('--size', type=int, default=50, help='Number of problems per size (default: 50)')
    parser.add_argument('--output', type=str, default='data/dataset', help='Output directory')
    parser.add_argument('--small-ops', type=int, default=20, help='Operations in small problems')
    parser.add_argument('--large-ops', type=int, default=50, help='Operations in large problems')
    args = parser.parse_args()

    print("=" * 60)
    print("DMFB Dataset Generator (Fast Version)")
    print("=" * 60)

    # Generate problems
    config = DatasetConfig(
        small_ops=args.small_ops,
        large_ops=args.large_ops,
        count_per_size=args.size
    )
    generator = ProblemGenerator(config)
    stats = generator.generate_dataset(args.output)

    # Run fast baselines
    print("\nGenerating baseline solutions (fast mode)...")
    runner = FastBaselineRunner()

    small_file = Path(args.output) / "problems_small.json"
    large_file = Path(args.output) / "problems_large.json"

    with open(small_file) as f:
        small_data = json.load(f)
        small_problems = [DMFBProblem.from_dict(d) for d in small_data]

    with open(large_file) as f:
        large_data = json.load(f)
        large_problems = [DMFBProblem.from_dict(d) for d in large_data]

    runner.run_dataset(small_problems, f"{args.output}/solutions_small.json")
    runner.run_dataset(large_problems, f"{args.output}/solutions_large.json")

    print("\n" + "=" * 60)
    print("Dataset generation complete!")
    print("=" * 60)
    print(f"\nFiles created in {args.output}:")
    for f in Path(args.output).glob("*.json"):
        size = f.stat().st_size / 1024  # KB
        print(f"  - {f.name} ({size:.1f} KB)")

    return stats


if __name__ == "__main__":
    main()
