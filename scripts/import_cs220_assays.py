"""
Import CS220 benchmark assays into our framework.

Usage:
    python scripts/import_cs220_assays.py \
        --cs220-dir C:/claude/CS220-dmfb-synthesis-skeleton \
        --output data/cs220_assays
"""

import sys
from pathlib import Path

# Add project root to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

import argparse
import json

from src.baseline.adapters.cs220_adapter import CS220Importer


def main():
    parser = argparse.ArgumentParser(description='Import CS220 assays')
    parser.add_argument('--cs220-dir', type=str,
                       default='C:/claude/CS220-dmfb-synthesis-skeleton',
                       help='Path to CS220 directory')
    parser.add_argument('--output', type=str,
                       default='data/cs220_assays',
                       help='Output directory for imported assays')
    args = parser.parse_args()

    cs220_dir = Path(args.cs220_dir)
    assays_dir = cs220_dir / 'Assays' / 'CFGs'

    if not assays_dir.exists():
        print(f"Error: CS220 assays directory not found: {assays_dir}")
        return 1

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Importing CS220 Benchmark Assays")
    print("=" * 60)

    problems = CS220Importer.import_all_cs220_assays(assays_dir)

    print(f"\nImported {len(problems)} assays")

    # Save each problem
    for problem in problems:
        output_file = output_dir / f"{problem.name}.json"
        problem.save(str(output_file))
        print(f"  Saved: {output_file}")

    # Create summary
    summary = {
        'total_assays': len(problems),
        'assays': [
            {
                'name': p.name,
                'operations': len(p.operations),
                'chip_size': f"{p.chip_width}x{p.chip_height}",
                'critical_path': p.get_critical_path_length()
            }
            for p in problems
        ]
    }

    summary_file = output_dir / 'summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nSummary saved to: {summary_file}")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
