"""
MFSimStatic Adapter.

This adapter integrates the UCR MFSimStatic DMFB synthesis tool.
MFSimStatic is a comprehensive C++ framework with multiple algorithms for:
- Scheduling: LS, PS, GAS, GAPS, RGAS, FDLS, FPPCS, FPPCPS, RTELS, ILPS
- Placement: KLLP, GLEB, GPB, FPPCLEB
- Routing: RMR, BR, FPR, FPMR, CR, FPPCSR, FPPCPR, LR, CDMAR
- Pin Mapping: IAPM, FPPCPM, EFPPCPOPM, EFPPCROPM, CPM, PPM, RAPM, SWPM
- Wire Routing: NOWR, PMIWR, PFWR, YWR, EFPPCWR

Input format: .txt (assay description)
Output format: Multiple interface files

Usage:
    MFSimStatic ef [scheduler] [placer] [router] [wash] [resourceAlloc]
                   [pinMap] [wireRoute] [compaction] [procEngine] [execType]
                   inputAssayFile inputArchFile maxDropsPerStorageMod
                   numCellsBetweenMods numHorizTracks numVertTracks
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Tuple, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

try:
    from .base_adapter import BaseAdapter, AdapterError
    from ..problem import DMFBProblem, Module, Operation, Droplet, ModuleType
except ImportError:
    from base_adapter import BaseAdapter, AdapterError
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from problem import DMFBProblem, Module, Operation, Droplet, ModuleType


class MFSimScheduler(str, Enum):
    """MFSim scheduler types."""
    LS = "LS"           # List Scheduling
    PS = "PS"           # Path Scheduling
    GAS = "GAS"         # Genetic Algorithm Scheduling
    GAPS = "GAPS"       # Genetic Algorithm Path Scheduling
    RGAS = "RGAS"       # Rickett's Genetic Algorithm Scheduling
    FDLS = "FDLS"       # Force Directed List Scheduling
    FPPCS = "FPPCS"     # FPPC Scheduling
    FPPCPS = "FPPCPS"   # FPPC Path Scheduling
    RTELS = "RTELS"     # Real-Time Evaluation List Scheduling
    ILPS = "ILPS"       # ILP Scheduling


class MFSimPlacer(str, Enum):
    """MFSim placer types."""
    KLLP = "KLLP"       # KAMER Linked-List Placement
    GLEB = "GLEB"       # Grissom's Left Edge Binder
    GPB = "GPB"         # Grissom's Path Binder
    FPPCLEB = "FPPCLEB" # FPPC Left Edge Binder


class MFSimRouter(str, Enum):
    """MFSim router types."""
    RMR = "RMR"         # Roy Maze Router
    BR = "BR"           # BioRouter
    FPR = "FPR"         # Fixed-Place Router
    FPMR = "FPMR"       # Fixed-Place Map Router
    CR = "CR"           # Cho's Router
    FPPCSR = "FPPCSR"   # FPPC Sequential Router
    FPPCPR = "FPPCPR"   # FPPC Parallel Router
    LR = "LR"           # Lee's Router
    CDMAR = "CDMAR"     # CDMA Router


class MFSimPinMapper(str, Enum):
    """MFSim pin mapper types."""
    IAPM = "IAPM"           # Individually Addressable
    FPPCPM = "FPPCPM"       # FPPC Original
    EFPPCPOPM = "EFPPCPOPM" # Enhanced FPPC Pin-Optimized
    EFPPCROPM = "EFPPCROPM" # Enhanced FPPC Route-Optimized
    CPM = "CPM"             # Clique Partitioning
    PPM = "PPM"             # Power Aware
    RAPM = "RAPM"           # Reliability Aware
    SWPM = "SWPM"           # Switching Aware


@dataclass
class MFSimConfig:
    """Configuration for MFSim adapter."""
    tool_path: Path = Path("C:/claude/MFSimStatic/MFSimStatic")
    executable: str = "MFSimStatic.exe"
    temp_dir: Path = Path("temp/mfsim")

    # Default algorithm choices
    scheduler: MFSimScheduler = MFSimScheduler.LS
    placer: MFSimPlacer = MFSimPlacer.GLEB
    router: MFSimRouter = MFSimRouter.RMR
    pin_mapper: MFSimPinMapper = MFSimPinMapper.IAPM

    # Default parameters
    perform_wash: bool = False
    resource_alloc: str = "FPRA0"  # Fixed Place Resource Allocator
    wire_route: str = "NOWR"        # No Wire Routing
    compaction: str = "NC"          # No Compaction
    proc_engine: str = "FREEPE"     # Free Processing Engine
    exec_type: str = "SE"           # Simulation Execution

    # Resource parameters
    max_drops_per_storage: int = 1
    num_cells_between_mods: int = 0
    num_horiz_tracks: int = 3
    num_vert_tracks: int = 3


class MFSimAdapter(BaseAdapter):
    """
    Adapter for UCR MFSimStatic DMFB synthesis tool.

    MFSimStatic is a comprehensive synthesis framework with many algorithms.
    This adapter supports calling it via command line.

    Example:
        adapter = MFSimAdapter()
        result = adapter.solve_full(problem)
    """

    def __init__(self, tool_path: str = "C:/claude/MFSimStatic/MFSimStatic"):
        self.config = MFSimConfig(tool_path=Path(tool_path))
        self._executable_path = self.config.tool_path / self.config.executable
        super().__init__(tool_path)

    def _validate_installation(self):
        """Check if MFSimStatic is compiled and available."""
        if not self.tool_path or not self.tool_path.exists():
            raise AdapterError(f"MFSimStatic not found at {self.tool_path}")

        # Check for executable
        if not self._executable_path.exists():
            alt_path = self.tool_path / "MFSimStatic"
            if alt_path.exists():
                self._executable_path = alt_path
            else:
                raise AdapterError(
                    f"MFSimStatic executable not found. Please compile it first:\n"
                    f"  cd {self.tool_path}\n"
                    f"  mkdir build && cd build\n"
                    f"  cmake ..\n"
                    f"  make"
                )

    def solve_placement(self, problem: DMFBProblem, **kwargs) -> Dict[int, Tuple[int, int]]:
        """Solve placement using MFSim."""
        result = self.solve_full(problem, **kwargs)
        return result.get('placement', {})

    def solve_scheduling(self, problem: DMFBProblem,
                        placement: Optional[Dict] = None,
                        **kwargs) -> Dict[int, Tuple[int, int]]:
        """Solve scheduling using MFSim."""
        result = self.solve_full(problem, **kwargs)
        return result.get('schedule', {})

    def solve_routing(self, problem: DMFBProblem,
                     placement: Dict,
                     schedule: Dict,
                     **kwargs) -> Dict[int, List[Tuple[int, int, int]]]:
        """Solve routing using MFSim."""
        result = self.solve_full(problem, **kwargs)
        return result.get('routing', {})

    def solve_full(self, problem: DMFBProblem,
                   work_dir: Optional[Path] = None,
                   scheduler: Optional[str] = None,
                   placer: Optional[str] = None,
                   router: Optional[str] = None,
                   **kwargs) -> Dict[str, Any]:
        """
        Run full synthesis using MFSimStatic.

        Args:
            problem: DMFB problem instance
            work_dir: Working directory for intermediate files
            scheduler: Scheduler type (LS, PS, GAS, etc.)
            placer: Placer type (GLEB, KLLP, GPB, etc.)
            router: Router type (RMR, BR, etc.)

        Returns:
            Dictionary with placement, schedule, routing, makespan, etc.
        """
        self._validate_installation()

        # Create working directory
        if work_dir is None:
            work_dir = self.config.temp_dir / problem.name
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        # Export problem to MFSim format
        assay_file = work_dir / f"{problem.name}.txt"
        arch_file = work_dir / "arch.txt"
        self._export_to_mfsim_format(problem, assay_file, arch_file)

        # Set algorithm choices
        sched = scheduler or self.config.scheduler.value
        place = placer or self.config.placer.value
        route = router or self.config.router.value

        # Build command for full flow
        cmd = [
            str(self._executable_path),
            "ef",  # Entire Flow
            sched,  # Scheduler
            place,  # Placer
            route,  # Router
            "TRUE" if self.config.perform_wash else "FALSE",  # Wash
            self.config.resource_alloc,
            self.config.pin_mapper.value,
            self.config.wire_route,
            self.config.compaction,
            self.config.proc_engine,
            self.config.exec_type,
            str(assay_file),  # Input assay
            str(arch_file),   # Input architecture
            str(self.config.max_drops_per_storage),
            str(self.config.num_cells_between_mods),
            str(self.config.num_horiz_tracks),
            str(self.config.num_vert_tracks)
        ]

        # Execute MFSimStatic
        try:
            result = subprocess.run(
                cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                raise AdapterError(f"MFSimStatic failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise AdapterError("MFSimStatic timed out after 5 minutes")
        except FileNotFoundError:
            raise AdapterError(f"MFSimStatic executable not found: {self._executable_path}")

        # Parse output files
        output_dir = work_dir / "Output"
        return self._parse_mfsim_output(problem, output_dir, work_dir)

    def _export_to_mfsim_format(self, problem: DMFBProblem,
                                assay_file: Path, arch_file: Path):
        """Export DMFBProblem to MFSim's input format."""
        # Write assay file (DAG description)
        self._write_assay_file(problem, assay_file)

        # Write architecture file
        self._write_arch_file(problem, arch_file)

    def _write_assay_file(self, problem: DMFBProblem, assay_file: Path):
        """Write assay description file (0_DAG_to_SCHED format)."""
        with open(assay_file, 'w') as f:
            f.write(f"DagName ({problem.name})\n")

            # Create module type to operation type mapping
            module_op_map = {}
            for op in problem.operations:
                module = problem.modules.get(op.module_type)
                if module:
                    module_op_map[op.module_type] = self._map_module_to_mfsim_op(module.type)

            # Write nodes
            for op in problem.operations:
                node_type = module_op_map.get(op.module_type, "MIX")
                duration = op.duration or 5

                if node_type == "DISPENSE":
                    f.write(f"Node ({op.id}, DISPENSE, Sample, 10, Op{op.id})\n")
                elif node_type == "MIX":
                    f.write(f"Node ({op.id}, MIX, 2, {duration}, Op{op.id})\n")
                elif node_type == "DILUTE":
                    f.write(f"Node ({op.id}, DILUTE, 2, {duration}, Op{op.id})\n")
                elif node_type == "SPLIT":
                    f.write(f"Node ({op.id}, SPLIT, 2, {duration}, Op{op.id})\n")
                elif node_type == "HEAT":
                    f.write(f"Node ({op.id}, HEAT, {duration}, Op{op.id})\n")
                elif node_type == "DETECT":
                    f.write(f"Node ({op.id}, DETECT, 1, {duration}, Op{op.id})\n")
                elif node_type == "OUTPUT":
                    f.write(f"Node ({op.id}, OUTPUT, Output, Op{op.id})\n")
                else:
                    f.write(f"Node ({op.id}, MIX, 2, {duration}, Op{op.id})\n")

                # Write edges (dependencies)
                for dep_id in op.dependencies:
                    f.write(f"Edge ({dep_id}, {op.id})\n")

                f.write("\n")

    def _map_module_to_mfsim_op(self, module_type: ModuleType) -> str:
        """Map ModuleType to MFSim operation type."""
        mapping = {
            ModuleType.MIXER: "MIX",
            ModuleType.HEATER: "HEAT",
            ModuleType.DETECTOR: "DETECT",
            ModuleType.STORAGE: "STORAGE",
            ModuleType.DISPENSER: "DISPENSE",
            ModuleType.WASTE: "OUTPUT",
        }
        return mapping.get(module_type, "MIX")

    def _write_arch_file(self, problem: DMFBProblem, arch_file: Path):
        """Write architecture file."""
        with open(arch_file, 'w') as f:
            f.write(f"Dim ({problem.chip_width}, {problem.chip_height})\n")

            # Write external modules (HEAT, DETECT)
            y_pos = 2
            for module_name, module in problem.modules.items():
                if module.type == ModuleType.HEATER:
                    f.write(f"External (HEAT, 2, {y_pos}, {2+module.width}, {y_pos+module.height})\n")
                    y_pos += module.height + 2
                elif module.type == ModuleType.DETECTOR:
                    f.write(f"External (DETECT, 2, {y_pos}, {2+module.width}, {y_pos+module.height})\n")
                    y_pos += module.height + 2

            f.write("\n")

            # Write I/O ports
            f.write("Input (North, 2, 2, Sample)\n")
            f.write("Output (South, 2, 2, Output)\n\n")

            f.write("Freq (100)\n")
            f.write("Timestep (1)\n")

    def _parse_mfsim_output(self, problem: DMFBProblem,
                           output_dir: Path, work_dir: Path) -> Dict[str, Any]:
        """Parse MFSimStatic output files."""
        result = {
            'placement': {},
            'schedule': {},
            'routing': {},
            'makespan': 0,
            'cpu_time': 0,
            'method': 'mfsim',
            'success': False
        }

        # Parse schedule file (1_SCHED_to_PLACE.txt)
        sched_file = output_dir / "1_SCHED_to_PLACE.txt"
        if sched_file.exists():
            result['schedule'], result['makespan'] = self._parse_schedule_file(sched_file)

        # Parse placement file (2_PLACE_to_ROUTE.txt)
        place_file = output_dir / "2_PLACE_to_ROUTE.txt"
        if place_file.exists():
            result['placement'] = self._parse_placement_file(place_file)

        # Parse route file (3_ROUTE_to_SIM.txt)
        route_file = output_dir / "3_ROUTE_to_SIM.txt"
        if route_file.exists():
            result['routing'] = self._parse_routing_file(route_file)

        result['success'] = bool(result['schedule'])
        return result

    def _parse_schedule_file(self, sched_file: Path) -> Tuple[Dict[int, Tuple[int, int]], int]:
        """Parse schedule output file (1_SCHED_to_PLACE format)."""
        schedule = {}
        makespan = 0

        with open(sched_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('Node ('):
                    # Parse: Node (id, type, ..., startTS, endTS)
                    match = re.search(r'Node\s*\(\s*(\d+)\s*,\s*\w+\s*,[^,]+,[^,]+,[^,]+,\s*(\d+)\s*,\s*(\d+)', line)
                    if match:
                        node_id = int(match.group(1))
                        start_ts = int(match.group(2))
                        end_ts = int(match.group(3))
                        schedule[node_id] = (start_ts, end_ts)
                        makespan = max(makespan, end_ts)

        return schedule, makespan

    def _parse_placement_file(self, place_file: Path) -> Dict[int, Tuple[int, int]]:
        """Parse placement output file (2_PLACE_to_ROUTE format)."""
        placement = {}
        # Placement info is in Reconfig lines with module positions
        # For now, return empty - can be enhanced later
        return placement

    def _parse_routing_file(self, route_file: Path) -> Dict[int, List[Tuple[int, int, int]]]:
        """Parse routing output file (3_ROUTE_to_SIM format)."""
        routing = {}
        # Routing parsing is complex - can be enhanced later
        return routing


class MFSimImporter:
    """Import MFSim assays into our DMFBProblem format."""

    @staticmethod
    def load_mfsim_assay(assay_path: Path, arch_path: Optional[Path] = None) -> DMFBProblem:
        """
        Load a MFSim assay file as a DMFBProblem.

        Args:
            assay_path: Path to assay .txt file
            arch_path: Optional path to architecture file

        Returns:
            DMFBProblem instance
        """
        assay_path = Path(assay_path)
        assay_name = assay_path.stem

        # Parse assay file
        operations, dag_name = MFSimImporter._parse_assay_file(assay_path)

        # Parse architecture if provided
        chip_width, chip_height = 64, 64
        modules = MFSimImporter._get_default_modules()

        if arch_path and arch_path.exists():
            chip_width, chip_height, arch_modules = MFSimImporter._parse_arch_file(arch_path)
            modules.update(arch_modules)

        # Create problem
        problem = DMFBProblem(
            name=assay_name,
            chip_width=chip_width,
            chip_height=chip_height,
            modules=modules,
            operations=operations,
            droplets=[]
        )

        return problem

    @staticmethod
    def _parse_assay_file(assay_path: Path) -> Tuple[List[Operation], str]:
        """Parse MFSim assay file."""
        operations = []
        dag_name = ""

        with open(assay_path, 'r') as f:
            content = f.read()

        # Parse DagName
        name_match = re.search(r'DagName\s*\(\s*(\w+)\s*\)', content)
        if name_match:
            dag_name = name_match.group(1)

        # Map MFSim operation types to our module types
        type_mapping = {
            'MIX': ('mixer_3x3', 5),
            'DILUTE': ('mixer_3x3', 5),
            'SPLIT': ('mixer_3x3', 5),
            'HEAT': ('heater_2x2', 10),
            'DETECT': ('detector_1x1', 2),
            'DISPENSE': ('dispenser', 1),
            'OUTPUT': ('waste', 1),
            'STORAGE': ('storage_2x2', 1),
        }

        # Parse nodes
        node_pattern = r'Node\s*\(\s*(\d+)\s*,\s*(\w+)\s*(?:,\s*([^)]+))?\)'
        for match in re.finditer(node_pattern, content):
            node_id = int(match.group(1))
            node_type = match.group(2)
            params = match.group(3) if match.group(3) else ""

            # Get module info
            module_key, default_duration = type_mapping.get(node_type, ('mixer_3x3', 5))

            # Parse duration from params
            duration = default_duration
            if params:
                param_parts = [p.strip() for p in params.split(',')]
                # Try to find duration (usually a number in params)
                for part in param_parts:
                    try:
                        val = int(part)
                        if val > 0 and val < 1000:  # Reasonable duration
                            duration = val
                            break
                    except ValueError:
                        continue

            # Create operation
            op = Operation(
                id=node_id,
                op_type=node_type.lower(),
                module_type=module_key,
                dependencies=[],
                duration=duration
            )
            operations.append(op)

        # Parse edges
        edge_pattern = r'Edge\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)'
        op_map = {op.id: op for op in operations}

        for match in re.finditer(edge_pattern, content):
            from_id = int(match.group(1))
            to_id = int(match.group(2))

            if to_id in op_map:
                op_map[to_id].dependencies.append(from_id)

        return operations, dag_name

    @staticmethod
    def _parse_arch_file(arch_path: Path) -> Tuple[int, int, Dict[str, Module]]:
        """Parse MFSim architecture file."""
        chip_width, chip_height = 64, 64
        modules = {}

        with open(arch_path, 'r') as f:
            content = f.read()

        # Parse Dim
        dim_match = re.search(r'Dim\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)', content)
        if dim_match:
            chip_width = int(dim_match.group(1))
            chip_height = int(dim_match.group(2))

        return chip_width, chip_height, modules

    @staticmethod
    def _get_default_modules() -> Dict[str, Module]:
        """Get default module library."""
        return {
            'mixer_3x3': Module('mixer_3x3', ModuleType.MIXER, 3, 3, 5),
            'heater_2x2': Module('heater_2x2', ModuleType.HEATER, 2, 2, 10),
            'detector_1x1': Module('detector_1x1', ModuleType.DETECTOR, 1, 1, 2),
            'storage_2x2': Module('storage_2x2', ModuleType.STORAGE, 2, 2, 1),
            'dispenser': Module('dispenser', ModuleType.DISPENSER, 1, 1, 1),
            'waste': Module('waste', ModuleType.WASTE, 1, 1, 1),
        }


def compare_with_mfsim(problem: DMFBProblem,
                       mfsim_adapter: Optional[MFSimAdapter] = None) -> Dict[str, Any]:
    """
    Compare Python fallback results with MFSimStatic results.

    Args:
        problem: DMFB problem to solve
        mfsim_adapter: Optional MFSim adapter instance

    Returns:
        Comparison dictionary with both results
    """
    from ..baseline_runner import BaselineRunner

    # Run Python fallback
    runner = BaselineRunner()
    python_result = runner.run(problem, method='python')

    # Run MFSim if available
    mfsim_result = None
    if mfsim_adapter is None:
        try:
            mfsim_adapter = MFSimAdapter()
        except AdapterError:
            pass

    if mfsim_adapter:
        try:
            mfsim_result = mfsim_adapter.solve_full(problem)
        except AdapterError as e:
            print(f"MFSim not available: {e}")

    # Create comparison
    comparison = {
        'problem': problem.name,
        'operations': len(problem.operations),
        'critical_path': problem.get_critical_path_length(),
        'python': {
            'makespan': python_result.get('makespan'),
            'cpu_time': python_result.get('cpu_time'),
            'success': python_result.get('success', True)
        },
        'mfsim': {
            'makespan': mfsim_result.get('makespan') if mfsim_result else None,
            'cpu_time': mfsim_result.get('cpu_time') if mfsim_result else None,
            'success': mfsim_result.get('success', False) if mfsim_result else False
        } if mfsim_result else None
    }

    # Calculate improvement if both succeeded
    if mfsim_result and mfsim_result.get('success') and python_result.get('success'):
        python_ms = python_result.get('makespan', 0)
        mfsim_ms = mfsim_result.get('makespan', 0)
        if python_ms > 0:
            improvement = (python_ms - mfsim_ms) / python_ms * 100
            comparison['improvement'] = f"{improvement:+.1f}%"

    return comparison
