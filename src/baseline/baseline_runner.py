"""
Unified interface for running baseline algorithms.

Automatically selects the best available adapter and provides
consistent API across all baseline methods.
"""

from typing import Dict, List, Optional, Union, Tuple
from pathlib import Path
import json
import time

from .problem import DMFBProblem
from .adapters import PythonFallbackAdapter, AdapterError


class BaselineRunner:
    """
    Unified runner for DMFB baseline algorithms.

    Automatically detects and uses available external tools,
    falling back to pure Python implementations if needed.

    Example:
        >>> runner = BaselineRunner()
        >>> result = runner.run(problem, method="auto")
        >>> print(f"Makespan: {result['makespan']}")
        >>>
        >>> # Run batch evaluation
        >>> results = runner.run_batch(problems, method="python")
    """

    # Available adapters (populated at init)
    ADAPTERS = {
        'python': None,  # Always available
        'mfsim': None,   # Optional
        'splash': None,  # Optional
    }

    def __init__(self, prefer_external: bool = True):
        """
        Initialize runner and detect available tools.

        Args:
            prefer_external: If True, prefer external tools over Python fallback
        """
        self.prefer_external = prefer_external
        self._init_adapters()

    def _init_adapters(self):
        """Detect and initialize available adapters."""
        # Python fallback is always available
        self.ADAPTERS['python'] = PythonFallbackAdapter()

        # Try to initialize optional adapters
        try:
            from .adapters import MFSimAdapter
            self.ADAPTERS['mfsim'] = MFSimAdapter()
            print("✓ MFSim adapter available")
        except (ImportError, AdapterError) as e:
            print(f"[SKIP] MFSim not available: {e}")

        try:
            from .adapters import SplashAdapter
            self.ADAPTERS['splash'] = SplashAdapter()
            print("✓ Splash adapter available")
        except (ImportError, AdapterError) as e:
            print(f"[SKIP] Splash not available: {e}")

    def run(self, problem: DMFBProblem,
            method: str = "auto",
            **kwargs) -> Dict:
        """
        Run baseline synthesis.

        Args:
            problem: DMFB problem instance
            method: "auto", "python", "mfsim", or "splash"
            **kwargs: Algorithm-specific parameters

        Returns:
            Synthesis result dictionary

        Raises:
            ValueError: If requested method is not available
        """
        if method == "auto":
            adapter = self._select_best_adapter()
        elif method in self.ADAPTERS:
            adapter = self.ADAPTERS[method]
            if adapter is None:
                raise ValueError(f"Adapter '{method}' is not available")
        else:
            raise ValueError(f"Unknown method: {method}. "
                           f"Available: {self.available_methods()}")

        return adapter.solve_full(problem, **kwargs)

    def run_placement_only(self, problem: DMFBProblem,
                          method: str = "auto",
                          **kwargs) -> Dict[int, Tuple[int, int]]:
        """Run only placement stage."""
        adapter = self._get_adapter(method)
        return adapter.solve_placement(problem, **kwargs)

    def run_scheduling_only(self, problem: DMFBProblem,
                           placement: Optional[Dict] = None,
                           method: str = "auto",
                           **kwargs) -> Dict[int, Tuple[int, int]]:
        """Run only scheduling stage."""
        adapter = self._get_adapter(method)
        return adapter.solve_scheduling(problem, placement, **kwargs)

    def run_routing_only(self, problem: DMFBProblem,
                        placement: Dict,
                        schedule: Dict,
                        method: str = "auto",
                        **kwargs) -> Dict:
        """Run only routing stage."""
        adapter = self._get_adapter(method)
        return adapter.solve_routing(problem, placement, schedule, **kwargs)

    def _select_best_adapter(self):
        """Select the best available adapter based on preference."""
        if self.prefer_external:
            # Prefer external tools
            for name in ['mfsim', 'splash']:
                if self.ADAPTERS[name] is not None:
                    return self.ADAPTERS[name]

        # Fall back to Python
        return self.ADAPTERS['python']

    def _get_adapter(self, method: str):
        """Get adapter by method name."""
        if method == "auto":
            return self._select_best_adapter()

        adapter = self.ADAPTERS.get(method)
        if adapter is None:
            raise ValueError(f"Adapter '{method}' not available")
        return adapter

    def available_methods(self) -> List[str]:
        """Return list of available method names."""
        return [name for name, adapter in self.ADAPTERS.items()
                if adapter is not None]

    def run_batch(self, problems: List[DMFBProblem],
                  method: str = "auto",
                  verbose: bool = True,
                  **kwargs) -> List[Dict]:
        """
        Run baseline on multiple problems.

        Args:
            problems: List of DMFB problems
            method: Baseline method to use
            verbose: Print progress
            **kwargs: Passed to run()

        Returns:
            List of results (one per problem)
        """
        from tqdm import tqdm

        results = []
        iterator = tqdm(problems, desc=f"Running {method}") if verbose else problems

        for i, problem in enumerate(iterator):
            try:
                result = self.run(problem, method, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"\nError on problem {i}: {e}")
                results.append({
                    'error': str(e),
                    'makespan': float('inf'),
                    'cpu_time': float('inf')
                })

        return results

    def compare_methods(self, problem: DMFBProblem,
                       methods: Optional[List[str]] = None,
                       **kwargs) -> Dict[str, Dict]:
        """
        Compare multiple baseline methods on the same problem.

        Args:
            problem: DMFB problem instance
            methods: List of methods to compare (default: all available)
            **kwargs: Passed to each method

        Returns:
            Dictionary mapping method name to result
        """
        if methods is None:
            methods = self.available_methods()

        results = {}
        for method in methods:
            print(f"\nRunning {method}...")
            start = time.time()
            try:
                result = self.run(problem, method, **kwargs)
                result['wall_time'] = time.time() - start
                results[method] = result

                print(f"  Makespan: {result.get('makespan', 'N/A')}")
                print(f"  CPU time: {result.get('cpu_time', 'N/A'):.3f}s")
            except Exception as e:
                print(f"  Error: {e}")
                results[method] = {'error': str(e)}

        return results

    def generate_training_data(self, problems: List[DMFBProblem],
                              output_dir: str,
                              method: str = "python",
                              save_intermediate: bool = True):
        """
        Generate training data by running baseline on problems.

        Args:
            problems: List of problems
            output_dir: Directory to save results
            method: Baseline method to use
            save_intermediate: Save results after each problem
        """
        from pathlib import Path
        import json

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for i, problem in enumerate(problems):
            print(f"\nProcessing problem {i+1}/{len(problems)}: {problem.name}")

            result = self.run(problem, method)

            # Combine problem and solution
            training_sample = {
                'problem': problem.to_dict(),
                'baseline_solution': result,
                'method': method
            }

            # Save
            output_file = output_path / f"{problem.name}_{method}.json"
            with open(output_file, 'w') as f:
                json.dump(training_sample, f, indent=2)

            print(f"  Saved to {output_file}")
            print(f"  Makespan: {result.get('makespan', 'N/A')}")
