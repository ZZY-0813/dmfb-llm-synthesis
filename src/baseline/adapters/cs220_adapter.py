"""
CS220-dmfb-synthesis-skeleton Adapter.

This adapter integrates the CS220 C++ synthesis framework.
Input format: .cfg (control flow graph) + .dag files
Output format: placement, schedule, routing files
"""

import os
import re
import json
import subprocess
from pathlib import Path
from typing import Dict, Tuple, List, Optional, Any
from dataclasses import dataclass, asdict

try:
    from .base_adapter import BaseAdapter, AdapterError
    from ..problem import DMFBProblem, Module, Operation, Droplet, ModuleType
except ImportError:
    # Allow direct import for testing
    from base_adapter import BaseAdapter, AdapterError
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from problem import DMFBProblem, Module, Operation, Droplet, ModuleType


@dataclass
class CS220Config:
    """Configuration for CS220 adapter."""
    tool_path: Path = Path("C:/claude/CS220-dmfb-synthesis-skeleton")
    executable: str = "CS220Synth.exe"  # Windows
    build_dir: str = "build"
    temp_dir: Path = Path("temp/cs220")


class CS220Adapter(BaseAdapter):
    """
    Adapter for CS220 DMFB synthesis skeleton.

    This tool provides:
    - List scheduling (asap/alap/mobility based)
    - Left-edge binder placement
    - Roy maze router

    Usage:
        adapter = CS220Adapter()
        result = adapter.solve_full(problem)
    """

    def __init__(self, tool_path: str = "C:/claude/CS220-dmfb-synthesis-skeleton"):
        super().__init__(tool_path)
        self.config = CS220Config(tool_path=Path(tool_path))
        self._executable_path = self.tool_path / self.config.executable

    def _validate_installation(self):
        """Check if CS220 is compiled and available."""
        if not self.tool_path or not self.tool_path.exists():
            raise AdapterError(f"CS220 not found at {self.tool_path}")

        # Check if executable exists, if not try to find it
        if not self._executable_path.exists():
            # Try without .exe (Linux/Mac)
            alt_path = self.tool_path / "CS220Synth"
            if alt_path.exists():
                self._executable_path = alt_path
            else:
                raise AdapterError(
                    f"CS220 executable not found. Please build it first:\n"
                    f"  cd {self.tool_path}\n"
                    f"  mkdir build && cd build\n"
                    f"  cmake ..\n"
                    f"  make"
                )

    def solve_placement(self, problem: DMFBProblem, **kwargs) -> Dict[int, Tuple[int, int]]:
        """
        Solve placement using CS220.
        Note: CS220 solves all stages together, so this runs full synthesis.
        """
        result = self.solve_full(problem, **kwargs)
        return result['placement']

    def solve_scheduling(self, problem: DMFBProblem,
                        placement: Optional[Dict] = None,
                        **kwargs) -> Dict[int, Tuple[int, int]]:
        """
        Solve scheduling using CS220.
        Note: CS220 solves all stages together, so this runs full synthesis.
        """
        result = self.solve_full(problem, **kwargs)
        return result['schedule']

    def solve_routing(self, problem: DMFBProblem,
                     placement: Dict,
                     schedule: Dict,
                     **kwargs) -> Dict[int, List[Tuple[int, int, int]]]:
        """
        Solve routing using CS220.
        Note: CS220 solves all stages together, so this runs full synthesis.
        """
        result = self.solve_full(problem, **kwargs)
        return result['routing']

    def solve_full(self, problem: DMFBProblem,
                   work_dir: Optional[Path] = None,
                   scheduler_type: str = "list",
                   placer_type: str = "left_edge",
                   router_type: str = "roy_maze",
                   **kwargs) -> Dict[str, Any]:
        """
        Run full synthesis using CS220.

        Args:
            problem: DMFB problem instance
            work_dir: Working directory for intermediate files
            scheduler_type: "list" or "cs220" (your implementation)
            placer_type: "left_edge" or "cs220"
            router_type: "roy_maze" or "cs220"

        Returns:
            Dictionary with placement, schedule, routing, makespan, etc.
        """
        self._validate_installation()

        # Create working directory
        if work_dir is None:
            work_dir = self.config.temp_dir
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        # Export problem to CS220 format
        assay_dir = work_dir / "Assays" / "CFGs" / problem.name
        assay_dir.mkdir(parents=True, exist_ok=True)

        cfg_file = assay_dir / f"{problem.name}.cfg"
        arch_file = assay_dir / "ArchFile" / "arch.txt"

        # Write input files
        self._export_to_cs220_format(problem, cfg_file, arch_file)

        # Run CS220
        cmd = [
            str(self._executable_path),
            str(cfg_file),
            scheduler_type,
            placer_type,
            router_type
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                raise AdapterError(f"CS220 failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise AdapterError("CS220 timed out after 5 minutes")
        except FileNotFoundError:
            raise AdapterError(f"CS220 executable not found: {self._executable_path}")

        # Parse output files
        output_dir = work_dir / "Output"
        return self._parse_cs220_output(problem, output_dir)

    def _export_to_cs220_format(self, problem: DMFBProblem,
                                cfg_file: Path, arch_file: Path):
        """Export DMFBProblem to CS220's .cfg and .dag format."""

        # For simple DAG without control flow, create a single DAG
        dag_name = f"DAG_{problem.name}"

        # Write CFG file (simplified - single DAG without control flow)
        with open(cfg_file, 'w') as f:
            f.write(f"NAME({problem.name}.cfg)\n\n")
            f.write(f"DAG({dag_name})\n\n")
            f.write("NUMCGS(0)\n")  # No conditional groups

        # Write DAG file
        dag_file = cfg_file.parent / f"{problem.name}_{dag_name}.dag"
        self._write_dag_file(problem, dag_file, dag_name)

        # Write architecture file
        arch_file.parent.mkdir(parents=True, exist_ok=True)
        self._write_arch_file(problem, arch_file)

    def _write_dag_file(self, problem: DMFBProblem, dag_file: Path, dag_name: str):
        """Write operations as a DAG file."""
        with open(dag_file, 'w') as f:
            f.write(f"DagName ({dag_name})\n")

            # Create a map of operation IDs for edge creation
            op_map = {op.id: op for op in problem.operations}

            # Write nodes (operations)
            for op in problem.operations:
                node_type = self._map_op_type_to_cs220(op.op_type)
                module = problem.modules.get(op.module_type)

                if node_type == "DISPENSE":
                    # DISPENSE (id, type, fluid_name, volume, name)
                    f.write(f"NODE ({op.id}, DISPENSE, Sample, 10, Sample)\n")
                elif node_type in ["MIX", "HEAT", "DETECT"]:
                    # MIX/HEAT/DETECT (id, type, duration, name)
                    duration = op.duration or (module.exec_time if module else 5)
                    f.write(f"NODE ({op.id}, {node_type}, {duration}, {node_type})\n")
                elif node_type == "OUTPUT":
                    # OUTPUT (id, type, fluid_name, name)
                    f.write(f"NODE ({op.id}, OUTPUT, null, Output)\n")
                else:
                    # Default
                    duration = op.duration or (module.exec_time if module else 5)
                    f.write(f"NODE ({op.id}, {node_type}, {duration}, {node_type})\n")

                # Write edges (dependencies)
                for dep_id in op.dependencies:
                    f.write(f"EDGE ({dep_id}, {op.id})\n")

                f.write("\n")

    def _map_op_type_to_cs220(self, op_type: str) -> str:
        """Map our operation types to CS220 types."""
        mapping = {
            'mix': 'MIX',
            'mixer': 'MIX',
            'heat': 'HEAT',
            'heater': 'HEAT',
            'detect': 'DETECT',
            'detector': 'DETECT',
            'dispense': 'DISPENSE',
            'output': 'OUTPUT',
            'storage': 'STORAGE',
        }
        return mapping.get(op_type.lower(), 'MIX')

    def _write_arch_file(self, problem: DMFBProblem, arch_file: Path):
        """Write architecture specification."""
        with open(arch_file, 'w') as f:
            f.write(f"ARCHNAME (Arch_{problem.chip_width}_{problem.chip_height})\n")
            f.write(f"DIM ({problem.chip_width}, {problem.chip_height})\n\n")

            # Write module locations (if placement is available)
            # For now, use default locations based on module types
            self._write_default_modules(f, problem)

            # Write I/O ports
            f.write("Input (north, 1, 0, Sample)\n")
            f.write("Output (south, 1, 0, Output)\n\n")

            f.write("FREQ (100)\n")
            f.write("TIMESTEP (1)\n")

    def _write_default_modules(self, f, problem: DMFBProblem):
        """Write default module locations."""
        # Place modules at fixed positions
        x, y = 2, 2

        for module_name, module in problem.modules.items():
            if module.type == ModuleType.HEATER:
                f.write(f"EXTERNAL (HEAT, {x}, {y}, {x + module.width}, {y + module.height})\n")
            elif module.type == ModuleType.DETECTOR:
                f.write(f"EXTERNAL (DETECT, {x}, {y}, {x + module.width}, {y + module.height})\n")

            x += module.width + 2
            if x > problem.chip_width - 5:
                x = 2
                y += 5

    def _parse_cs220_output(self, problem: DMFBProblem,
                           output_dir: Path) -> Dict[str, Any]:
        """Parse CS220 output files."""
        result = {
            'placement': {},
            'schedule': {},
            'routing': {},
            'makespan': 0,
            'cpu_time': 0,
            'method': 'cs220',
            'success': False
        }

        # Parse placement file
        placed_file = output_dir / f"{problem.name}_placed.txt"
        if placed_file.exists():
            result['placement'] = self._parse_placement(placed_file)

        # Parse schedule file
        scheduled_file = output_dir / f"{problem.name}_scheduled.txt"
        if scheduled_file.exists():
            result['schedule'], result['makespan'] = self._parse_schedule(scheduled_file)

        # Parse route file
        routed_file = output_dir / f"{problem.name}_routed.txt"
        if routed_file.exists():
            result['routing'] = self._parse_routing(routed_file)

        result['success'] = bool(result['schedule'])
        return result

    def _parse_placement(self, placed_file: Path) -> Dict[int, Tuple[int, int]]:
        """Parse placement output file."""
        placement = {}
        # CS220 placement format needs to be determined from actual output
        # This is a placeholder
        return placement

    def _parse_schedule(self, scheduled_file: Path) -> Tuple[Dict[int, Tuple[int, int]], int]:
        """Parse schedule output file."""
        schedule = {}
        makespan = 0
        # CS220 schedule format needs to be determined from actual output
        # This is a placeholder
        return schedule, makespan

    def _parse_routing(self, routed_file: Path) -> Dict[int, List[Tuple[int, int, int]]]:
        """Parse routing output file."""
        routing = {}
        # CS220 routing format needs to be determined from actual output
        # This is a placeholder
        return routing


class CS220Importer:
    """
    Import CS220 assays into our DMFBProblem format.

    This allows us to use CS220's benchmark assays for testing.
    """

    @staticmethod
    def load_cs220_assay(cfg_path: Path, arch_path: Optional[Path] = None) -> DMFBProblem:
        """
        Load a CS220 assay (CFG + DAGs) as a DMFBProblem.

        Args:
            cfg_path: Path to .cfg file
            arch_path: Optional path to architecture file

        Returns:
            DMFBProblem instance
        """
        cfg_path = Path(cfg_path)
        assay_name = cfg_path.stem

        # Parse CFG file
        dag_files = CS220Importer._parse_cfg(cfg_path)

        # Parse all DAG files
        operations = []
        modules = {}

        for dag_file in dag_files:
            dag_ops, dag_modules = CS220Importer._parse_dag(dag_file)
            operations.extend(dag_ops)
            modules.update(dag_modules)

        # Parse architecture if provided
        chip_width, chip_height = 64, 64  # Default
        if arch_path and arch_path.exists():
            chip_width, chip_height = CS220Importer._parse_arch(arch_path)

        # Create problem
        problem = DMFBProblem(
            name=assay_name,
            chip_width=chip_width,
            chip_height=chip_height,
            modules=modules,
            operations=operations,
            droplets=[]  # Will be inferred
        )

        return problem

    @staticmethod
    def _parse_cfg(cfg_path: Path) -> List[Path]:
        """Parse CFG file and return list of DAG file paths."""
        dag_files = []
        cfg_dir = cfg_path.parent

        with open(cfg_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('DAG('):
                    # Extract DAG name
                    match = re.search(r'DAG\((\w+)\)', line)
                    if match:
                        dag_name = match.group(1)
                        dag_file = cfg_dir / f"{cfg_path.stem}_{dag_name}.dag"
                        if dag_file.exists():
                            dag_files.append(dag_file)

        return dag_files

    @staticmethod
    def _parse_dag(dag_path: Path) -> Tuple[List[Operation], Dict[str, Module]]:
        """Parse a DAG file and return operations and modules."""
        operations = []
        modules = {}

        # Define module types mapping (name, type, width, height, exec_time)
        type_to_module = {
            'MIX': ('mixer_3x3', Module('mixer_3x3', ModuleType.MIXER, 3, 3, 5)),
            'HEAT': ('heater_2x2', Module('heater_2x2', ModuleType.HEATER, 2, 2, 10)),
            'DETECT': ('detector_1x1', Module('detector_1x1', ModuleType.DETECTOR, 1, 1, 2)),
            'DISPENSE': ('dispenser', Module('dispenser', ModuleType.DISPENSER, 1, 1, 1)),
            'OUTPUT': ('waste', Module('waste', ModuleType.WASTE, 1, 1, 1)),
        }

        with open(dag_path, 'r') as f:
            content = f.read()

        # Parse nodes
        node_pattern = r'NODE\s*\(\s*(\d+)\s*,\s*(\w+)\s*(?:,\s*([^)]+))?\)'
        for match in re.finditer(node_pattern, content):
            node_id = int(match.group(1))
            node_type = match.group(2)
            params = match.group(3) if match.group(3) else ""

            # Get module info
            module_key, module = type_to_module.get(node_type, type_to_module['MIX'])
            modules[module_key] = module

            # Parse duration from params
            duration = None
            if params:
                param_parts = [p.strip() for p in params.split(',')]
                # Try to find duration (usually a number)
                for part in param_parts:
                    try:
                        duration = int(part)
                        break
                    except ValueError:
                        continue

            # Create operation
            op = Operation(
                id=node_id,
                op_type=node_type.lower(),
                module_type=module_key,
                dependencies=[],  # Will be set later
                duration=duration
            )
            operations.append(op)

        # Parse edges (dependencies)
        edge_pattern = r'EDGE\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)'
        op_map = {op.id: op for op in operations}

        for match in re.finditer(edge_pattern, content):
            from_id = int(match.group(1))
            to_id = int(match.group(2))

            if to_id in op_map:
                op_map[to_id].dependencies.append(from_id)

        return operations, modules

    @staticmethod
    def _parse_arch(arch_path: Path) -> Tuple[int, int]:
        """Parse architecture file and return chip dimensions."""
        with open(arch_path, 'r') as f:
            for line in f:
                if line.startswith('DIM'):
                    match = re.search(r'DIM\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)', line)
                    if match:
                        return int(match.group(1)), int(match.group(2))
        return 64, 64

    @staticmethod
    def import_all_cs220_assays(cs220_assays_dir: Path) -> List[DMFBProblem]:
        """
        Import all CS220 assays from a directory.

        Args:
            cs220_assays_dir: Path to CS220/Assays/CFGs directory

        Returns:
            List of DMFBProblem instances
        """
        problems = []
        cs220_assays_dir = Path(cs220_assays_dir)

        for assay_dir in cs220_assays_dir.iterdir():
            if not assay_dir.is_dir():
                continue

            cfg_files = list(assay_dir.glob("*.cfg"))
            if not cfg_files:
                continue

            cfg_file = cfg_files[0]
            arch_file = assay_dir / "ArchFile" / "arch.txt"

            try:
                problem = CS220Importer.load_cs220_assay(cfg_file, arch_file)
                problems.append(problem)
                print(f"[OK] Imported {problem.name}: {len(problem.operations)} ops")
            except Exception as e:
                print(f"[SKIP] Failed to import {assay_dir.name}: {e}")

        return problems
