"""
Quick demo of the DMFB + LLM Synthesis Framework.

This script demonstrates the basic functionality without running
full optimization (which takes time).
"""

import sys
sys.path.insert(0, 'src')

print("="*60)
print("DMFB + LLM Synthesis Framework - Demo")
print("="*60)

# 1. Import and basic test
print("\n1. Testing imports...")
from src.baseline.problem import DMFBProblem, Module, Operation, ModuleType
from src.baseline.placement_ga import PlacementGA
from src.baseline.scheduling_list import ListScheduler
from src.baseline.routing_astar import AStarRouter
from src.dataset.generator import ProblemGenerator
print("   [OK] All imports successful")

# 2. Problem generation
print("\n2. Generating test problem...")
gen = ProblemGenerator(seed=42)
problem = gen.generate(
    num_ops=5,  # Small problem for quick demo
    pattern='linear',
    name='demo_problem'
)
print(f"   [OK] Generated: {problem}")
print(f"   - Operations: {len(problem.operations)}")
print(f"   - Chip size: {problem.chip_width}x{problem.chip_height}")
print(f"   - Critical path: {problem.get_critical_path_length()}")

# 3. Test list scheduling (fast)
print("\n3. Testing list scheduling (fast)...")
scheduler = ListScheduler(problem)
schedule_result = scheduler.solve(priority_strategy='asap')
print(f"   [OK] Makespan: {schedule_result['makespan']}")
print(f"   - Schedule: {schedule_result['schedule']}")

# 4. Test placement (reduced iterations for demo)
print("\n4. Testing GA placement (quick demo, 50 gens)...")
print("   (Full runs use 500 generations)")
ga = PlacementGA(problem, pop_size=20, generations=50, seed=42)
best = ga.solve(verbose=False)
print(f"   [OK] Best wirelength: {-best.fitness:.2f}")
print(f"   - Positions: {best.positions}")

# 5. Show problem structure
print("\n5. Problem structure:")
print("   Operations:")
for op in problem.operations:
    deps = f" (depends on: {op.dependencies})" if op.dependencies else ""
    print(f"   - Op {op.id}: {op.op_type} using {op.module_type}{deps}")

print("\n" + "="*60)
print("Demo complete! Framework is working correctly.")
print("="*60)
print("\nNext steps:")
print("1. Generate full dataset: python scripts/generate_dataset.py")
print("2. Run baselines: python scripts/run_baseline.py --help")
print("3. Read PROJECT_SUMMARY.md for details")
print("="*60)
