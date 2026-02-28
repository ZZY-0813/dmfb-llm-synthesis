"""
Benchmark our framework against CS220 assays.

Usage:
    python scripts/benchmark_cs220.py --assays-dir data/cs220_assays
"""

import sys
from pathlib import Path

script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

import argparse
import json
import time

from src.baseline.problem import DMFBProblem
from src.baseline.baseline_runner import BaselineRunner


def benchmark_assay(problem_file: Path, runner: BaselineRunner):
    """Benchmark a single assay."""
    problem = DMFBProblem.load(str(problem_file))

    start_time = time.time()
    result = runner.run(problem, method='python')
    elapsed = time.time() - start_time

    return {
        'name': problem.name,
        'operations': len(problem.operations),
        'critical_path': problem.get_critical_path_length(),
        'makespan': result.get('makespan', 0),
        'cpu_time': elapsed,
        'success': result.get('success', False)
    }


def main():
    parser = argparse.ArgumentParser(description='Benchmark CS220 assays')
    parser.add_argument('--assays-dir', type=str,
                       default='data/cs220_assays',
                       help='Directory containing imported CS220 assays')
    args = parser.parse_args()

    assays_dir = Path(args.assays_dir)
    if not assays_dir.exists():
        print(f"Error: Assays directory not found: {assays_dir}")
        return 1

    print("=" * 80)
    print("Benchmarking CS220 Assays with Our Framework")
    print("=" * 80)

    runner = BaselineRunner()
    results = []

    for assay_file in sorted(assays_dir.glob('*.json')):
        if assay_file.name == 'summary.json':
            continue

        try:
            result = benchmark_assay(assay_file, runner)
            results.append(result)
            status = "OK" if result['success'] else "FAIL"
            print(f"[{status}] {result['name']}: "
                  f"ops={result['operations']}, "
                  f"CPL={result['critical_path']}, "
                  f"makespan={result['makespan']}, "
                  f"time={result['cpu_time']:.2f}s")
        except Exception as e:
            print(f"[ERROR] {assay_file.stem}: {e}")

    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)

    # Create summary table
    print(f"\n{'Assay':<25} {'Ops':>6} {'CPL':>6} {'Makespan':>10} {'Time (s)':>10}")
    print("-" * 80)
    for r in results:
        print(f"{r['name']:<25} {r['operations']:>6} {r['critical_path']:>6} "
              f"{r['makespan']:>10} {r['cpu_time']:>10.2f}")

    # Overall statistics
    total_ops = sum(r['operations'] for r in results)
    avg_makespan_ratio = sum(r['makespan'] / max(r['critical_path'], 1)
                            for r in results) / len(results)
    total_time = sum(r['cpu_time'] for r in results)

    print(f"\nTotal assays: {len(results)}")
    print(f"Total operations: {total_ops}")
    print(f"Avg makespan/CPL ratio: {avg_makespan_ratio:.2f}")
    print(f"Total CPU time: {total_time:.2f}s")

    return 0


if __name__ == '__main__':
    sys.exit(main())
