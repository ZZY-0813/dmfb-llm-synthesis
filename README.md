# DMFB + LLM Synthesis Framework

A comprehensive framework for **Digital Microfluidic Biochip (DMFB) Full-Stage Synthesis** using Large Language Models and Multi-Agent Systems.

This project implements:
- **Placement**: Genetic Algorithm (GA) for module positioning
- **Scheduling**: List scheduling with multiple priority strategies (ASAP, ALAP, Mobility-based)
- **Routing**: A* search with fluidic constraints
- **Multi-Agent Framework**: Extensible architecture for LLM-based synthesis (in development)

## 📁 Project Structure

```
dmfb-llm-synthesis/
├── src/
│   ├── baseline/               # Baseline algorithms
│   │   ├── problem.py          # Core data structures (DMFBProblem, Module, Operation)
│   │   ├── placement_ga.py     # Genetic Algorithm for placement
│   │   ├── scheduling_list.py  # List scheduling algorithms
│   │   ├── routing_astar.py    # A* routing with fluidic constraints
│   │   ├── baseline_runner.py  # Unified interface for all baselines
│   │   └── adapters/           # Adapters for external tools
│   │       ├── base_adapter.py
│   │       ├── python_fallback.py  # Pure Python implementation
│   │       ├── mfsim_adapter.py    # MFSim wrapper (optional)
│   │       └── splash_adapter.py   # Splash-2 wrapper (optional)
│   ├── dataset/
│   │   └── generator.py        # Problem instance generator
│   └── utils/
│       ├── visualization.py    # Matplotlib-based visualization
│       ├── config.py           # YAML/JSON config management
│       └── logger.py           # Logging utilities
├── scripts/
│   ├── generate_dataset.py     # Generate training data
│   └── run_baseline.py         # Run baseline algorithms
├── configs/
│   └── default.yaml            # Default configuration
├── data/                       # Generated datasets (gitignored)
├── experiments/                # Experiment results (gitignored)
└── external/                   # External tools (optional)
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd dmfb-llm-synthesis

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Generate a Test Problem

```python
from src.dataset.generator import ProblemGenerator
from src.baseline.problem import DMFBProblem

# Create generator
gen = ProblemGenerator(seed=42)

# Generate a single problem
problem = gen.generate(
    num_ops=20,
    pattern='random',  # 'linear', 'parallel', 'fork_join', 'pcr'
    name='test_problem'
)

print(problem)
# Output: DMFBProblem(test_problem: 20 ops, 64x64 grid, CPL=45)

# Save for later use
problem.save('data/test_problem.json')
```

### 3. Run Baseline Algorithms

```python
from src.baseline.baseline_runner import BaselineRunner
from src.baseline.problem import DMFBProblem

# Load problem
problem = DMFBProblem.load('data/test_problem.json')

# Run baseline
runner = BaselineRunner()
result = runner.run(problem, method='python')

print(f"Makespan: {result['makespan']}")
print(f"CPU time: {result['cpu_time']:.3f}s")
```

### 4. Command Line Usage

```bash
# Generate dataset
python scripts/generate_dataset.py \
    --output data/training \
    --sizes 20 50 100 \
    --num-per-size 100 \
    --patterns linear parallel random

# Run baseline on single problem
python scripts/run_baseline.py \
    --problem data/test_problem.json \
    --method python \
    --visualize

# Compare multiple methods
python scripts/run_baseline.py \
    --problem data/test_problem.json \
    --compare
```

## 📊 Baseline Algorithms

### Placement: Genetic Algorithm

```python
from src.baseline.placement_ga import PlacementGA

ga = PlacementGA(
    problem,
    pop_size=100,
    generations=500,
    crossover_rate=0.8,
    mutation_rate=0.2
)

best = ga.solve(verbose=True)
print(f"Best wirelength: {-best.fitness}")
```

### Scheduling: List Scheduling

```python
from src.baseline.scheduling_list import ListScheduler

scheduler = ListScheduler(problem)

# Multiple priority strategies available:
# - 'asap': As Soon As Possible
# - 'alap': As Late As Possible
# - 'mobility': ALAP - ASAP (critical path first)
# - 'critical_path': Longest path to sink

result = scheduler.solve(priority_strategy='mobility')
print(f"Makespan: {result['makespan']}")
```

### Routing: A* Search

```python
from src.baseline.routing_astar import AStarRouter

router = AStarRouter(problem)

# Add static obstacles (placed modules)
for op_id, (x, y) in placement.items():
    module = problem.modules[problem.operations[op_id-1].module_type]
    router.add_obstacle(x, y, module.width, module.height)

# Route multiple droplets with conflict avoidance
routes = router.route_multiple(droplets, strategy='prioritized')
```

## 🎨 Visualization

```python
from src.utils.visualization import visualize_placement, visualize_schedule

# Visualize placement
visualize_placement(
    problem,
    placement,
    title="My Placement",
    save_path="figures/placement.png"
)

# Visualize schedule as Gantt chart
visualize_schedule(
    problem,
    schedule,
    title="My Schedule",
    save_path="figures/schedule.png"
)

# Generate all visualizations
from src.utils.visualization import visualize_full_solution

visualize_full_solution(problem, solution, output_dir="experiments/figures/")
```

## 🔧 Configuration

Create a custom configuration file:

```yaml
# my_config.yaml
baseline:
  placement:
    pop_size: 200
    generations: 1000

  scheduling:
    priority_strategy: critical_path

experiment:
  num_runs: 10
  save_visualizations: true
```

Load and use:

```python
from src.utils.config import load_config

config = load_config('configs/my_config.yaml')
```

## 📚 Problem Instance Formats

### JSON Format

```json
{
  "name": "test_problem",
  "chip_width": 64,
  "chip_height": 64,
  "modules": {
    "mixer_3x3": {
      "name": "mixer_3x3",
      "type": "mixer",
      "width": 3,
      "height": 3,
      "exec_time": 5
    }
  },
  "operations": [
    {
      "id": 1,
      "op_type": "mix",
      "module_type": "mixer_3x3",
      "dependencies": [],
      "duration": null
    }
  ]
}
```

### Supported DAG Patterns

- **linear**: Chain: 1 → 2 → 3 → ...
- **parallel**: Multiple independent chains
- **fork_join**: Fork into parallel branches then join
- **pcr**: PCR cycles (mix → heat → detect)
- **random**: Random DAG with controlled edge probability

## 🔌 External Tools (Optional)

The framework supports adapters for external DMFB tools:

### MFSim (UCR)

```python
from src.baseline.adapters import MFSimAdapter

adapter = MFSimAdapter('/path/to/mfsim')
result = adapter.solve_full(problem)
```

### Splash-2

```python
from src.baseline.adapters import SplashAdapter

adapter = SplashAdapter('/path/to/splash2')
result = adapter.solve_full(problem)
```

If external tools are not available, the framework automatically falls back to pure Python implementations.

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_placement.py -v
```

## 📝 Citation

If you use this framework in your research, please cite:

```bibtex
@software{dmfb_llm_synthesis,
  title={DMFB + LLM Synthesis Framework},
  author={Your Name},
  year={2024},
  url={https://github.com/your-repo}
}
```

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Contact

For questions or support, please open an issue on GitHub.

---

**Status**: This is an active research project. The baseline algorithms are fully functional. The LLM-based multi-agent synthesis framework is under development.
# Auto-push test
