#!/usr/bin/env python3
"""
Generate DMFB problem dataset using baseline algorithms.

This script:
1. Generates problem instances
2. Runs baseline algorithms
3. Saves problems + solutions as training data

Usage:
    python scripts/generate_dataset.py --output data/training --sizes 20 50 100 --num-per-size 100
"""

import sys
sys.path.insert(0, 'src')

import argparse
import json
from pathlib import Path
from tqdm import tqdm

from dataset.generator import ProblemGenerator, load_problem_dataset
from baseline.baseline_runner import BaselineRunner


def main():
    parser = argparse.ArgumentParser(description='Generate DMFB training dataset')
    parser.add_argument('--output', type=str, default='data/processed',
                       help='Output directory for dataset')
    parser.add_argument('--sizes', type=int, nargs='+', default=[20, 50, 100],
                       help='Problem sizes (number of operations)')
    parser.add_argument('--num-per-size', type=int, default=100,
                       help='Number of problems per size')
    parser.add_argument('--patterns', type=str, nargs='+',
                       default=['linear', 'parallel', 'random'],
                       help='DAG patterns to generate')
    parser.add_argument('--method', type=str, default='python',
                       choices=['auto', 'python', 'mfsim', 'splash'],
                       help='Baseline method to use')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed')
    parser.add_argument('--skip-existing', action='store_true',
                       help='Skip problems that already exist')

    args = parser.parse_args()

    print("=" * 60)
    print("DMFB Dataset Generator")
    print("=" * 60)

    # Initialize components
    generator = ProblemGenerator(seed=args.seed)
    runner = BaselineRunner()

    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\nConfiguration:")
    print(f"  Output directory: {output_path}")
    print(f"  Problem sizes: {args.sizes}")
    print(f"  Problems per size: {args.num_per_size}")
    print(f"  Patterns: {args.patterns}")
    print(f"  Baseline method: {args.method}")
    print(f"  Available methods: {runner.available_methods()}")

    total_generated = 0
    total_failed = 0

    for size in args.sizes:
        for pattern in args.patterns:
            print(f"\n{'='*60}")
            print(f"Generating: size={size}, pattern={pattern}")
            print('='*60)

            for i in tqdm(range(args.num_per_size), desc=f"{pattern}_{size}"):
                problem_name = f"{pattern}_{size}_{i:04d}"
                output_file = output_path / f"{problem_name}.json"

                # Skip if exists
                if args.skip_existing and output_file.exists():
                    continue

                try:
                    # Generate problem
                    problem = generator.generate(
                        num_ops=size,
                        pattern=pattern,
                        name=problem_name
                    )

                    # Run baseline
                    result = runner.run(problem, method=args.method)

                    # Combine and save
                    training_sample = {
                        'problem': problem.to_dict(),
                        'baseline_solution': result,
                        'method': args.method,
                        'statistics': {
                            'makespan': result.get('makespan'),
                            'cpu_time': result.get('cpu_time'),
                            'routing_success': result.get('routing_success_rate', 0)
                        }
                    }

                    with open(output_file, 'w') as f:
                        json.dump(training_sample, f, indent=2)

                    total_generated += 1

                except Exception as e:
                    print(f"\nError on {problem_name}: {e}")
                    total_failed += 1

    print(f"\n{'='*60}")
    print("Dataset generation complete!")
    print(f"  Generated: {total_generated}")
    print(f"  Failed: {total_failed}")
    print(f"  Output: {output_path}")
    print('='*60)


if __name__ == '__main__':
    main()
