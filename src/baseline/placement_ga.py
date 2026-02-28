"""
Genetic Algorithm for DMFB Placement.

Optimizes module positions to minimize wirelength (sum of Manhattan distances
between dependent operations) while avoiding overlaps.
"""

import random
import copy
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
import numpy as np

from .problem import DMFBProblem, Operation, Module


@dataclass
class PlacementIndividual:
    """
    A single placement solution (individual in GA population).

    Attributes:
        positions: Dictionary mapping operation ID to (x, y) position
        fitness: Cached fitness value (None if not evaluated)
    """
    positions: Dict[int, Tuple[int, int]]
    fitness: Optional[float] = None

    def copy(self) -> "PlacementIndividual":
        """Create a deep copy."""
        return PlacementIndividual(
            positions=copy.deepcopy(self.positions),
            fitness=self.fitness
        )


class PlacementGA:
    """
    Genetic Algorithm for DMFB placement optimization.

    Optimizes for:
    1. Minimizing total wirelength (Manhattan distance between dependent ops)
    2. Avoiding module overlaps (hard constraint via penalty)
    3. Keeping modules within chip boundaries (hard constraint via penalty)

    Example:
        >>> problem = DMFBProblem(...)  # Load or create problem
        >>> ga = PlacementGA(problem, pop_size=100, generations=500)
        >>> best = ga.solve()
        >>> print(f"Best positions: {best.positions}")
        >>> print(f"Wirelength: {-best.fitness}")
    """

    def __init__(self, problem: DMFBProblem,
                 pop_size: int = 100,
                 generations: int = 500,
                 crossover_rate: float = 0.8,
                 mutation_rate: float = 0.2,
                 elitism: int = 2,
                 tournament_size: int = 3,
                 penalty_overlap: float = 1000.0,
                 penalty_boundary: float = 500.0,
                 seed: Optional[int] = None):
        """
        Initialize GA solver.

        Args:
            problem: DMFB problem instance
            pop_size: Population size
            generations: Number of generations to run
            crossover_rate: Probability of crossover
            mutation_rate: Probability of mutation per gene
            elitism: Number of best individuals to preserve
            tournament_size: Tournament selection size
            penalty_overlap: Penalty for each overlapping module pair
            penalty_boundary: Penalty for each unit outside boundary
            seed: Random seed for reproducibility
        """
        self.problem = problem
        self.pop_size = pop_size
        self.generations = generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.elitism = elitism
        self.tournament_size = tournament_size
        self.penalty_overlap = penalty_overlap
        self.penalty_boundary = penalty_boundary

        # Create operation ID to operation mapping for quick lookup
        self.op_map = {op.id: op for op in problem.operations}

        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        # Statistics tracking
        self.history = {
            'best_fitness': [],
            'avg_fitness': [],
            'worst_fitness': []
        }

    def solve(self, verbose: bool = True) -> PlacementIndividual:
        """
        Run the genetic algorithm.

        Args:
            verbose: Print progress information

        Returns:
            Best placement individual found
        """
        # Initialize population
        population = self._init_population()

        # Evaluate initial population
        for ind in population:
            if ind.fitness is None:
                ind.fitness = self._evaluate(ind)

        # Evolution loop
        for gen in range(self.generations):
            # Sort by fitness
            population.sort(key=lambda x: x.fitness, reverse=True)

            # Track statistics
            fitnesses = [ind.fitness for ind in population]
            self.history['best_fitness'].append(max(fitnesses))
            self.history['avg_fitness'].append(sum(fitnesses) / len(fitnesses))
            self.history['worst_fitness'].append(min(fitnesses))

            if verbose and gen % 50 == 0:
                print(f"Gen {gen:4d}: Best={max(fitnesses):10.2f}, "
                      f"Avg={sum(fitnesses)/len(fitnesses):10.2f}, "
                      f"Wirelength={self._calculate_wirelength(population[0]):.2f}")

            # Create new generation
            new_population = []

            # Elitism: Keep best individuals
            new_population.extend([ind.copy() for ind in population[:self.elitism]])

            # Generate offspring
            while len(new_population) < self.pop_size:
                # Selection
                parent1 = self._tournament_select(population)
                parent2 = self._tournament_select(population)

                # Crossover
                if random.random() < self.crossover_rate:
                    offspring1, offspring2 = self._crossover(parent1, parent2)
                else:
                    offspring1, offspring2 = parent1.copy(), parent2.copy()

                # Mutation
                self._mutate(offspring1)
                self._mutate(offspring2)

                # Evaluate
                offspring1.fitness = self._evaluate(offspring1)
                offspring2.fitness = self._evaluate(offspring2)

                new_population.extend([offspring1, offspring2])

            # Trim to population size
            population = new_population[:self.pop_size]

        # Return best solution
        population.sort(key=lambda x: x.fitness, reverse=True)
        return population[0]

    def _init_population(self) -> List[PlacementIndividual]:
        """Create initial random population."""
        population = []

        for _ in range(self.pop_size):
            positions = {}
            for op in self.problem.operations:
                module = self.problem.modules[op.module_type]
                # Random position within bounds
                max_x = self.problem.chip_width - module.width
                max_y = self.problem.chip_height - module.height

                if max_x >= 0 and max_y >= 0:
                    x = random.randint(0, max_x)
                    y = random.randint(0, max_y)
                else:
                    # Module larger than chip (shouldn't happen)
                    x, y = 0, 0

                positions[op.id] = (x, y)

            population.append(PlacementIndividual(positions=positions))

        return population

    def _evaluate(self, individual: PlacementIndividual) -> float:
        """
        Evaluate fitness of an individual.

        Fitness = -wirelength - penalties
        Higher is better.
        """
        wirelength = self._calculate_wirelength(individual)
        overlap_penalty = self._calculate_overlap_penalty(individual)
        boundary_penalty = self._calculate_boundary_penalty(individual)

        return -(wirelength + overlap_penalty + boundary_penalty)

    def _calculate_wirelength(self, individual: PlacementIndividual) -> float:
        """Calculate total Manhattan wirelength between dependent operations."""
        total = 0.0

        for op in self.problem.operations:
            x1, y1 = individual.positions[op.id]

            for dep_id in op.dependencies:
                x2, y2 = individual.positions[dep_id]

                # Center-to-center distance
                module1 = self.problem.modules[op.module_type]
                module2 = self.problem.modules[self.op_map[dep_id].module_type]

                cx1 = x1 + module1.width / 2
                cy1 = y1 + module1.height / 2
                cx2 = x2 + module2.width / 2
                cy2 = y2 + module2.height / 2

                manhattan = abs(cx1 - cx2) + abs(cy1 - cy2)
                total += manhattan

        return total

    def _calculate_overlap_penalty(self, individual: PlacementIndividual) -> float:
        """Calculate penalty for overlapping modules."""
        penalty = 0.0
        positions = list(individual.positions.items())

        for i, (id1, (x1, y1)) in enumerate(positions):
            module1 = self.problem.modules[self.op_map[id1].module_type]

            for id2, (x2, y2) in positions[i+1:]:
                module2 = self.problem.modules[self.op_map[id2].module_type]

                # Check overlap
                if self._rects_overlap(
                    x1, y1, module1.width, module1.height,
                    x2, y2, module2.width, module2.height
                ):
                    # Calculate overlap area
                    overlap_area = self._overlap_area(
                        x1, y1, module1.width, module1.height,
                        x2, y2, module2.width, module2.height
                    )
                    penalty += self.penalty_overlap * overlap_area

        return penalty

    def _calculate_boundary_penalty(self, individual: PlacementIndividual) -> float:
        """Calculate penalty for modules outside chip boundary."""
        penalty = 0.0

        for op_id, (x, y) in individual.positions.items():
            op = self.op_map[op_id]
            module = self.problem.modules[op.module_type]

            # Check right/bottom boundaries (top-left is 0,0)
            right = x + module.width
            bottom = y + module.height

            if right > self.problem.chip_width:
                penalty += self.penalty_boundary * (right - self.problem.chip_width)
            if bottom > self.problem.chip_height:
                penalty += self.penalty_boundary * (bottom - self.problem.chip_height)
            if x < 0:
                penalty += self.penalty_boundary * abs(x)
            if y < 0:
                penalty += self.penalty_boundary * abs(y)

        return penalty

    @staticmethod
    def _rects_overlap(x1, y1, w1, h1, x2, y2, w2, h2) -> bool:
        """Check if two rectangles overlap."""
        return not (x1 + w1 <= x2 or x2 + w2 <= x1 or
                   y1 + h1 <= y2 or y2 + h2 <= y1)

    @staticmethod
    def _overlap_area(x1, y1, w1, h1, x2, y2, w2, h2) -> float:
        """Calculate overlap area of two rectangles."""
        left = max(x1, x2)
        right = min(x1 + w1, x2 + w2)
        top = max(y1, y2)
        bottom = min(y1 + h1, y2 + h2)

        if right <= left or bottom <= top:
            return 0.0

        return (right - left) * (bottom - top)

    def _tournament_select(self, population: List[PlacementIndividual]) -> PlacementIndividual:
        """Tournament selection."""
        tournament = random.sample(population, min(self.tournament_size, len(population)))
        return max(tournament, key=lambda x: x.fitness)

    def _crossover(self, parent1: PlacementIndividual,
                  parent2: PlacementIndividual) -> Tuple[PlacementIndividual, PlacementIndividual]:
        """
        Uniform crossover: randomly select positions from either parent.
        """
        child1_positions = {}
        child2_positions = {}

        for op_id in parent1.positions:
            if random.random() < 0.5:
                child1_positions[op_id] = parent1.positions[op_id]
                child2_positions[op_id] = parent2.positions[op_id]
            else:
                child1_positions[op_id] = parent2.positions[op_id]
                child2_positions[op_id] = parent1.positions[op_id]

        return (PlacementIndividual(positions=child1_positions),
                PlacementIndividual(positions=child2_positions))

    def _mutate(self, individual: PlacementIndividual) -> None:
        """
        Gaussian mutation: add random noise to positions.
        """
        for op_id in individual.positions:
            if random.random() < self.mutation_rate:
                x, y = individual.positions[op_id]
                module = self.problem.modules[self.op_map[op_id].module_type]

                # Gaussian mutation
                sigma = max(self.problem.chip_width, self.problem.chip_height) * 0.1
                new_x = int(x + random.gauss(0, sigma))
                new_y = int(y + random.gauss(0, sigma))

                # Keep within bounds
                max_x = self.problem.chip_width - module.width
                max_y = self.problem.chip_height - module.height

                individual.positions[op_id] = (
                    max(0, min(new_x, max_x)),
                    max(0, min(new_y, max_y))
                )

        # Invalidate fitness
        individual.fitness = None

    def get_statistics(self) -> Dict:
        """Return evolution statistics."""
        return self.history.copy()
