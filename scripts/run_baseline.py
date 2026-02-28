#!/usr/bin/env python3
"""
Run baseline algorithms on DMFB problems.

Usage:
    # Run on a single problem
    python scripts/run_baseline.py --problem data/raw/test.json --method python

    # Run on a directory of problems
    python scripts/run_baseline.py --input data/raw/ --output results/ --method python

    # Compare multiple methods
    python scripts/run_baseline.py --problem test.json --compare
"""

import sys
sys.path.insert(0, 'src')

import argparse
import json
import time
from pathlib import Path
from tqdm import tqdm

from baseline.problem import DMFBProblem
from baseline.baseline_runner import BaselineRunner
from utils.visualization import visualize_full_solution


def run_single(problem_file: str, method: str, visualize: bool = False, output_dir: str = None):
    """Run baseline on a single problem."""
    print(f"Loading problem from {problem_file}...")
    problem = DMFBProblem.load(problem_file)
    print(f"Loaded: {problem}")

    runner = BaselineRunner()
    print(f"\nRunning {method} baseline...")

    start = time.time()
    result = runner.run(problem, method=method)
    elapsed = time.time() - start

    print(f"\n{'='*50}")
    print("Results:")
    print(f"  Makespan: {result.get('makespan', 'N/A')}")
    print(f"  CPU time: {result.get('cpu_time', 'N/A'):.3f}s")
    print(f"  Wall time: {elapsed:.3f}s")

    if 'placement_time' in result:
        print(f"  Placement: {result['placement_time']:.3f}s")
        print(f"  Scheduling: {result['scheduling_time']:.3f}s")
        print(f"  Routing: {result['routing_time']:.3f}s")

    print('='*50)

    # Visualize
    if visualize:
        viz_dir = output_dir or f"experiments/figures/{problem.name}"
        visualize_full_solution(problem, result, viz_dir)

    return result


def run_batch(input_dir: str, output_dir: str, method: str):
    """Run baseline on multiple problems."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load all problems
    problem_files = list(input_path.glob("*.json"))
    print(f"Found {len(problem_files)} problems in {input_dir}")

    runner = BaselineRunner()
    results = []

    for pf in tqdm(problem_files, desc=f"Running {method}"):
        try:
            problem = DMFBProblem.load(pf)
            result = runner.run(problem, method=method)
            result['problem_name'] = problem.name
            results.append(result)
        except Exception as e:
            print(f"\nError on {pf.name}: {e}")
            results.append({
                'problem_name': pf.stem,
                'error': str(e),
                'makespan': float('inf'),
                'cpu_time': float('inf')
            })

    # Save results
    summary = {
        'method': method,
        'num_problems': len(results),
        'avg_makespan': sum(r.get('makespan', 0) for r in results if 'makespan' in r) / len(results),
        'avg_cpu_time': sum(r.get('cpu_time', 0) for r in results if 'cpu_time' in r) / len(results),
        'results': results
    }

    summary_file = output_path / f"baseline_{method}_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nSummary saved to {summary_file}")
    print(f"Average makespan: {summary['avg_makespan']:.2f}")
    print(f"Average CPU time: {summary['avg_cpu_time']:.3f}s")


def compare_methods(problem_file: str):
    """Compare multiple baseline methods on a single problem."""
    problem = DMFBProblem.load(problem_file)
    runner = BaselineRunner()

    print(f"Comparing methods on {problem.name}...")
    results = runner.compare_methods(problem)

    print("\n" + "="*70)
    print(f"{'Method':<15} {'Makespan':<12} {'CPU Time':<12} {'Status'}")
    print("="*70)

    for method, result in results.items():
        if 'error' in result:
            print(f"{method:<15} {'ERROR':<12} {'ERROR':<12} {result['error']}")
        else:
            print(f"{method:<15} {result.get('makespan', 'N/A'):<12} "
                  f"{result.get('cpu_time', 0):.3f}s      {'OK'}")

    print("="*70)


def main():
    parser = argparse.ArgumentParser(description='Run DMFB baseline algorithms')
    parser.add_argument('--problem', type=str,
                       help='Single problem file to run')
    parser.add_argument('--input', type=str,
                       help='Directory of problems to run')
    parser.add_argument('--output', type=str, default='experiments/results',
                       help='Output directory for results')
    parser.add_argument('--method', type=str, default='python',
                       choices=['auto', 'python', 'mfsim', 'splash'],
                       help='Baseline method to use')
    parser.add_argument('--visualize', action='store_true',
                       help='Generate visualizations')
    parser.add_argument('--compare', action='store_true',
                       help='Compare all available methods')

    args = parser.parse_args()

    if args.compare and args.problem:
        compare_methods(args.problem)
    elif args.problem:
        run_single(args.problem, args.method, args.visualize, args.output)
    elif args.input:
        run_batch(args.input, args.output, args.method)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
