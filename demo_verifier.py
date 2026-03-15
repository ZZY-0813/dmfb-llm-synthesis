"""
Verifier Demo - Show current code capabilities
"""
import sys
sys.path.insert(0, 'src')

from agents.verifier import (
    PlacementVerifier, ScheduleVerifier, RoutingVerifier,
    UnifiedVerifier, ViolationType
)

class MockProblem:
    def __init__(self, width=10, height=10):
        self.chip_width = width
        self.chip_height = height
        self.operations = []
        self.modules = {}

class MockOperation:
    def __init__(self, op_id, dependencies=None, duration=3):
        self.id = op_id
        self.dependencies = dependencies or []
        self.duration = duration

def demo_placement():
    """Demo: Placement Verifier"""
    print("\n" + "="*60)
    print("PLACEMENT VERIFIER DEMO")
    print("="*60)

    problem = MockProblem(10, 10)
    verifier = PlacementVerifier()

    # Case 1: Valid placement
    print("\n[Case 1] Valid Placement:")
    placements = [
        {"module_id": "mixer_1", "x": 2, "y": 2, "width": 2, "height": 2},
        {"module_id": "heater_1", "x": 5, "y": 5, "width": 1, "height": 1}
    ]
    result = verifier.verify(problem, {"placements": placements})
    print(f"  Result: {'PASS' if result.is_valid else 'FAIL'}")
    print(f"  Violations: {len(result.violations)}")

    # Case 2: Overlapping modules
    print("\n[Case 2] Overlapping Modules:")
    placements = [
        {"module_id": "mixer_1", "x": 2, "y": 2, "width": 3, "height": 3},
        {"module_id": "mixer_2", "x": 3, "y": 3, "width": 3, "height": 3}
    ]
    result = verifier.verify(problem, {"placements": placements})
    print(f"  Result: {'PASS' if result.is_valid else 'FAIL'}")
    print(f"  Violations: {len(result.violations)}")
    for v in result.violations:
        print(f"    - {v.violation_type.value}: {v.message[:60]}...")
        if v.suggested_fix:
            print(f"      Suggestion: {v.suggested_fix[:60]}...")

def demo_schedule():
    """Demo: Schedule Verifier"""
    print("\n" + "="*60)
    print("SCHEDULE VERIFIER DEMO")
    print("="*60)

    problem = MockProblem()
    problem.operations = [
        MockOperation(0, dependencies=[], duration=3),
        MockOperation(1, dependencies=[0], duration=2),
    ]
    verifier = ScheduleVerifier()

    # Case 1: Valid schedule
    print("\n[Case 1] Valid Schedule (respects dependencies):")
    schedule = [
        {"operation_id": 0, "start_time": 0, "end_time": 3, "module_id": "mixer_1"},
        {"operation_id": 1, "start_time": 3, "end_time": 5, "module_id": "heater_1"}
    ]
    result = verifier.verify(problem, {"schedule": schedule})
    print(f"  Result: {'PASS' if result.is_valid else 'FAIL'}")
    print(f"  Op0: t=0->3 on mixer_1")
    print(f"  Op1: t=3->5 on heater_1 (depends on Op0)")

    # Case 2: Dependency violation
    print("\n[Case 2] Dependency Violation:")
    schedule = [
        {"operation_id": 0, "start_time": 0, "end_time": 3, "module_id": "mixer_1"},
        {"operation_id": 1, "start_time": 1, "end_time": 3, "module_id": "heater_1"}
    ]
    result = verifier.verify(problem, {"schedule": schedule})
    print(f"  Result: {'PASS' if result.is_valid else 'FAIL'}")
    print(f"  Op0: t=0->3 on mixer_1")
    print(f"  Op1: t=1->3 on heater_1 (starts before Op0 finishes!)")
    for v in result.violations:
        print(f"    - {v.violation_type.value}")
        print(f"      Suggestion: {v.suggested_fix}")

def demo_routing():
    """Demo: Routing Verifier"""
    print("\n" + "="*60)
    print("ROUTING VERIFIER DEMO")
    print("="*60)

    problem = MockProblem(10, 10)
    verifier = RoutingVerifier()

    # Case 1: Valid routes
    print("\n[Case 1] Valid Routes (no collision):")
    routes = [
        {"droplet_id": "d1", "path": [(0, 1, 1), (1, 2, 1), (2, 3, 1)]},
        {"droplet_id": "d2", "path": [(0, 5, 5), (1, 5, 6), (2, 5, 7)]}
    ]
    result = verifier.verify(problem, {"routes": routes})
    print(f"  Result: {'PASS' if result.is_valid else 'FAIL'}")
    print(f"  d1: (1,1) -> (2,1) -> (3,1)")
    print(f"  d2: (5,5) -> (5,6) -> (5,7)")

    # Case 2: Collision
    print("\n[Case 2] Droplet Collision:")
    routes = [
        {"droplet_id": "d1", "path": [(0, 1, 1), (1, 2, 1), (2, 3, 1)]},
        {"droplet_id": "d2", "path": [(0, 3, 3), (1, 2, 1), (2, 1, 1)]}  # Both at (2,1) at t=1
    ]
    result = verifier.verify(problem, {"routes": routes})
    print(f"  Result: {'PASS' if result.is_valid else 'FAIL'}")
    print(f"  d1: (1,1) -> (2,1) -> (3,1)")
    print(f"  d2: (3,3) -> (2,1) -> (1,1)")
    print(f"  Collision at t=1, position (2,1)!")
    for v in result.violations:
        print(f"    - {v.violation_type.value}")

def demo_unified():
    """Demo: Unified Verifier"""
    print("\n" + "="*60)
    print("UNIFIED VERIFIER DEMO")
    print("="*60)

    problem = MockProblem()
    problem.operations = [
        MockOperation(0, dependencies=[]),
        MockOperation(1, dependencies=[0])
    ]

    solution = {
        "placements": [
            {"module_id": "mixer_1", "x": 2, "y": 2, "width": 2, "height": 2}
        ],
        "schedule": [
            {"operation_id": 0, "start_time": 0, "end_time": 3, "module_id": "mixer_1"},
            {"operation_id": 1, "start_time": 3, "end_time": 6, "module_id": "mixer_1"}
        ],
        "routes": [
            {"droplet_id": "d1", "path": [(0, 1, 1), (1, 2, 1), (2, 3, 1)]}
        ]
    }

    unified = UnifiedVerifier()
    results = unified.verify_full(problem, solution)

    print("\nFull solution verification:")
    for stage, result in results.items():
        status = "PASS" if result.is_valid else "FAIL"
        print(f"  [{status}] {stage}: {len(result.violations)} violations")

    print(f"\nOverall: {'ALL PASS' if unified.is_valid(results) else 'FAILED'}")

def demo_llm_report():
    """Demo: LLM-friendly error report"""
    print("\n" + "="*60)
    print("LLM REPORT DEMO")
    print("="*60)

    problem = MockProblem(10, 10)
    verifier = PlacementVerifier()

    # Create an invalid placement
    placements = [
        {"module_id": "mixer_1", "x": 2, "y": 2, "width": 3, "height": 3},
        {"module_id": "mixer_2", "x": 3, "y": 3, "width": 3, "height": 3}
    ]
    result = verifier.verify(problem, {"placements": placements})

    print("\nReport for LLM (natural language):")
    print("-"*60)
    report = result.to_llm_report()
    print(report)
    print("-"*60)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("DMFB VERIFIER SYSTEM - CAPABILITY DEMONSTRATION")
    print("="*60)
    print("\nCurrent Status: Week 1 Complete - All Verifiers Implemented")

    demo_placement()
    demo_schedule()
    demo_routing()
    demo_unified()
    demo_llm_report()

    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60)
    print("\nSummary:")
    print("  - 3 Placement checks: overlap, out-of-bounds, negative position")
    print("  - 3 Schedule checks: dependency, resource conflict, timing")
    print("  - 3 Routing checks: collision, continuity, (fluid constraint framework)")
    print("  - Unified verification across all stages")
    print("  - LLM-friendly error reports with fix suggestions")
