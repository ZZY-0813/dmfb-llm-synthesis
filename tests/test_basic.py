"""
Basic tests to verify the framework is working correctly.
"""

import sys
sys.path.insert(0, 'src')

import pytest
from src.baseline.problem import DMFBProblem, Module, Operation, ModuleType
from src.baseline.placement_ga import PlacementGA
from src.baseline.scheduling_list import ListScheduler
from src.baseline.routing_astar import AStarRouter
from src.dataset.generator import ProblemGenerator


def test_problem_creation():
    """Test basic problem creation."""
    modules = {
        'mixer': Module('mixer', ModuleType.MIXER, 3, 3, 5),
        'heater': Module('heater', ModuleType.HEATER, 2, 2, 10),
    }

    operations = [
        Operation(1, 'mix', 'mixer', [], 5),
        Operation(2, 'heat', 'heater', [1], 10),
    ]

    problem = DMFBProblem('test', 64, 64, modules, operations)

    assert problem.name == 'test'
    assert problem.chip_width == 64
    assert len(problem.operations) == 2


def test_placement_ga():
    """Test genetic algorithm placement."""
    generator = ProblemGenerator(seed=42)
    problem = generator.generate(10, pattern='linear')

    ga = PlacementGA(problem, pop_size=20, generations=50, seed=42)
    best = ga.solve(verbose=False)

    assert best.fitness is not None
    assert len(best.positions) == 10

    # Check all operations have positions
    for op in problem.operations:
        assert op.id in best.positions


def test_list_scheduling():
    """Test list scheduling."""
    generator = ProblemGenerator(seed=42)
    problem = generator.generate(10, pattern='linear')

    scheduler = ListScheduler(problem)
    result = scheduler.solve(priority_strategy='asap')

    assert 'schedule' in result
    assert 'makespan' in result
    assert len(result['schedule']) == 10

    # Verify dependencies are respected
    for op in problem.operations:
        start_time, _ = result['schedule'][op.id]
        for dep_id in op.dependencies:
            _, dep_end = result['schedule'][dep_id]
            assert start_time >= dep_end, f"Dependency violation: {op.id} starts before {dep_id} ends"


def test_astar_routing():
    """Test A* routing."""
    from src.baseline.problem import Droplet

    # Simple 10x10 grid
    modules = {'test': Module('test', ModuleType.MIXER, 1, 1, 1)}
    operations = [Operation(1, 'test', 'test')]
    problem = DMFBProblem('routing_test', 10, 10, modules, operations)

    router = AStarRouter(problem)

    # Create a simple droplet
    droplet = Droplet(1, (0, 0), (5, 5), 0, 20)

    # Route
    path = router.route_single(droplet)

    assert path is not None
    assert len(path) > 0
    assert path[0] == (0, 0, 0)  # Start position
    assert path[-1][:2] == (5, 5)  # End position


def test_problem_generator():
    """Test problem generation."""
    generator = ProblemGenerator(seed=42)

    # Test different patterns
    for pattern in ['linear', 'parallel', 'random']:
        problem = generator.generate(20, pattern=pattern)
        assert len(problem.operations) == 20
        assert problem.name.startswith(pattern)

        # Verify DAG is valid
        topo_order = problem.topological_sort()
        assert len(topo_order) == 20


def test_problem_serialization():
    """Test saving and loading problems."""
    import tempfile
    import os

    generator = ProblemGenerator(seed=42)
    problem = generator.generate(10, pattern='linear', name='serialization_test')

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'test.json')

        # Save
        problem.save(filepath)
        assert os.path.exists(filepath)

        # Load
        loaded = DMFBProblem.load(filepath)
        assert loaded.name == problem.name
        assert len(loaded.operations) == len(problem.operations)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
