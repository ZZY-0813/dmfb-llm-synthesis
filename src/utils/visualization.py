"""
Visualization utilities for DMFB synthesis results.

Provides functions to visualize:
- Placement (module positions on chip)
- Schedule (Gantt chart)
- Routing (droplet paths)
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle, FancyBboxPatch, Arrow
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from ..baseline.problem import DMFBProblem


def visualize_placement(problem: DMFBProblem,
                       placement: Dict[int, Tuple[int, int]],
                       title: str = "DMFB Placement",
                       figsize: Tuple[int, int] = (10, 10),
                       show_dependencies: bool = True,
                       save_path: Optional[str] = None):
    """
    Visualize module placement on the DMFB chip.

    Args:
        problem: DMFB problem instance
        placement: Dictionary mapping operation ID to (x, y) position
        title: Plot title
        figsize: Figure size
        show_dependencies: Draw lines between dependent modules
        save_path: If provided, save figure to this path
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Draw grid
    ax.set_xlim(0, problem.chip_width)
    ax.set_ylim(0, problem.chip_height)
    ax.set_aspect('equal')

    # Grid lines
    for i in range(problem.chip_width + 1):
        ax.axvline(i, color='lightgray', linewidth=0.5)
    for i in range(problem.chip_height + 1):
        ax.axhline(i, color='lightgray', linewidth=0.5)

    # Color map for module types
    colors = {
        'mixer': '#FF6B6B',
        'heater': '#4ECDC4',
        'detector': '#45B7D1',
        'storage': '#96CEB4',
        'dispenser': '#FFEAA7',
        'waste': '#DDA0DD'
    }

    op_map = {op.id: op for op in problem.operations}

    # Draw modules
    for op_id, (x, y) in placement.items():
        op = op_map.get(op_id)
        if not op:
            continue

        module = problem.modules[op.module_type]
        color = colors.get(module.type.value, 'gray')

        # Draw module rectangle
        rect = FancyBboxPatch(
            (x, y), module.width, module.height,
            boxstyle="round,pad=0.02",
            facecolor=color,
            edgecolor='black',
            linewidth=2,
            alpha=0.7
        )
        ax.add_patch(rect)

        # Add operation ID label
        cx = x + module.width / 2
        cy = y + module.height / 2
        ax.text(cx, cy, str(op_id), ha='center', va='center',
               fontsize=10, fontweight='bold')

    # Draw dependency edges
    if show_dependencies:
        for op in problem.operations:
            if op.id not in placement:
                continue

            x1, y1 = placement[op.id]
            module1 = problem.modules[op.module_type]
            cx1 = x1 + module1.width / 2
            cy1 = y1 + module1.height / 2

            for dep_id in op.dependencies:
                if dep_id not in placement:
                    continue

                x2, y2 = placement[dep_id]
                module2 = problem.modules[op_map[dep_id].module_type]
                cx2 = x2 + module2.width / 2
                cy2 = y2 + module2.height / 2

                # Draw arrow from dependency to dependent
                ax.annotate('', xy=(cx1, cy1), xytext=(cx2, cy2),
                           arrowprops=dict(arrowstyle='->', color='red',
                                         alpha=0.3, lw=1))

    ax.set_xlabel('X (electrodes)')
    ax.set_ylabel('Y (electrodes)')
    ax.set_title(title)

    # Legend
    legend_elements = [patches.Patch(facecolor=color, edgecolor='black', label=mtype)
                      for mtype, color in colors.items()
                      if mtype in [m.type.value for m in problem.modules.values()]]
    ax.legend(handles=legend_elements, loc='upper right')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved to {save_path}")

    return fig, ax


def visualize_schedule(problem: DMFBProblem,
                      schedule: Dict[int, Tuple[int, int]],
                      title: str = "DMFB Schedule",
                      figsize: Tuple[int, int] = (12, 8),
                      group_by_module: bool = True,
                      save_path: Optional[str] = None):
    """
    Visualize operation schedule as a Gantt chart.

    Args:
        problem: DMFB problem instance
        schedule: Dictionary mapping operation ID to (start, end) time
        title: Plot title
        figsize: Figure size
        group_by_module: Group operations by module type
        save_path: If provided, save figure to this path
    """
    fig, ax = plt.subplots(figsize=figsize)

    op_map = {op.id: op for op in problem.operations}

    # Sort operations
    if group_by_module:
        # Group by module type
        module_groups = {}
        for op_id in schedule:
            op = op_map[op_id]
            mtype = op.module_type
            if mtype not in module_groups:
                module_groups[mtype] = []
            module_groups[mtype].append(op_id)

        sorted_ops = []
        y_labels = []
        y_pos = 0
        for mtype, ops in sorted(module_groups.items()):
            sorted_ops.extend(ops)
            y_labels.append(f"{mtype} ({len(ops)} ops)")
            y_pos += len(ops) + 0.5
    else:
        sorted_ops = sorted(schedule.keys())
        y_labels = [f"Op {op_id}" for op_id in sorted_ops]

    # Color by module type
    colors = plt.cm.Set3(np.linspace(0, 1, len(problem.modules)))
    module_color = {mtype: colors[i] for i, mtype in enumerate(problem.modules)}

    # Draw bars
    for i, op_id in enumerate(sorted_ops):
        start, end = schedule[op_id]
        duration = end - start
        op = op_map[op_id]
        color = module_color.get(op.module_type, 'gray')

        ax.barh(i, duration, left=start, height=0.6,
               color=color, edgecolor='black', alpha=0.8)

        # Add operation ID
        ax.text(start + duration/2, i, str(op_id),
               ha='center', va='center', fontsize=8)

    ax.set_yticks(range(len(sorted_ops)))
    ax.set_yticklabels([f"Op {op_id}" for op_id in sorted_ops])
    ax.set_xlabel('Time (ticks)')
    ax.set_ylabel('Operation')
    ax.set_title(title)

    # Add makespan line
    makespan = max(end for start, end in schedule.values())
    ax.axvline(makespan, color='red', linestyle='--', linewidth=2, label=f'Makespan={makespan}')
    ax.legend()

    ax.grid(axis='x', alpha=0.3)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')

    return fig, ax


def visualize_routing(problem: DMFBProblem,
                     placement: Dict[int, Tuple[int, int]],
                     routing: Dict[int, List[Tuple[int, int, int]]],
                     title: str = "DMFB Routing",
                     figsize: Tuple[int, int] = (12, 12),
                     time_step: Optional[int] = None,
                     save_path: Optional[str] = None):
    """
    Visualize droplet routing paths.

    Args:
        problem: DMFB problem instance
        placement: Module positions
        routing: Dictionary mapping droplet ID to path
        title: Plot title
        figsize: Figure size
        time_step: If provided, show snapshot at this time step
        save_path: If provided, save figure to this path
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Draw chip boundary
    ax.set_xlim(0, problem.chip_width)
    ax.set_ylim(0, problem.chip_height)
    ax.set_aspect('equal')

    # Draw grid
    for i in range(problem.chip_width + 1):
        ax.axvline(i, color='lightgray', linewidth=0.5)
    for i in range(problem.chip_height + 1):
        ax.axhline(i, color='lightgray', linewidth=0.5)

    # Draw modules (as obstacles)
    op_map = {op.id: op for op in problem.operations}
    for op_id, (x, y) in placement.items():
        op = op_map.get(op_id)
        if op:
            module = problem.modules[op.module_type]
            rect = Rectangle((x, y), module.width, module.height,
                           facecolor='gray', edgecolor='black', alpha=0.3)
            ax.add_patch(rect)

    # Draw routing paths
    colors = plt.cm.rainbow(np.linspace(0, 1, len(routing)))

    for i, (droplet_id, path) in enumerate(routing.items()):
        if not path:
            continue

        color = colors[i % len(colors)]

        if time_step is not None:
            # Show droplet positions at specific time
            positions = [(x, y) for x, y, t in path if t == time_step]
            for pos in positions:
                circle = plt.Circle(pos, 0.3, color=color, alpha=0.8)
                ax.add_patch(circle)
        else:
            # Show full path
            xs = [p[0] for p in path]
            ys = [p[1] for p in path]
            ax.plot(xs, ys, '-o', color=color, alpha=0.6, markersize=3,
                   label=f'Droplet {droplet_id}')

            # Mark start and end
            if path:
                ax.plot(path[0][0], path[0][1], 'go', markersize=10)  # Start
                ax.plot(path[-1][0], path[-1][1], 'r*', markersize=15)  # End

    ax.set_xlabel('X (electrodes)')
    ax.set_ylabel('Y (electrodes)')
    ax.set_title(title if time_step is None else f"{title} (t={time_step})")

    if len(routing) <= 10:  # Only show legend if not too many
        ax.legend(loc='upper right')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')

    return fig, ax


def visualize_full_solution(problem: DMFBProblem,
                           solution: Dict,
                           output_dir: str):
    """
    Generate all visualizations for a complete solution.

    Args:
        problem: DMFB problem instance
        solution: Dictionary with 'placement', 'schedule', 'routing'
        output_dir: Directory to save figures
    """
    from pathlib import Path
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    base_name = problem.name

    # Placement
    if 'placement' in solution:
        visualize_placement(
            problem, solution['placement'],
            title=f"{base_name} - Placement",
            save_path=output_path / f"{base_name}_placement.png"
        )
        plt.close()

    # Schedule
    if 'schedule' in solution:
        visualize_schedule(
            problem, solution['schedule'],
            title=f"{base_name} - Schedule",
            save_path=output_path / f"{base_name}_schedule.png"
        )
        plt.close()

    # Routing
    if 'routing' in solution and 'placement' in solution:
        visualize_routing(
            problem, solution['placement'], solution['routing'],
            title=f"{base_name} - Routing",
            save_path=output_path / f"{base_name}_routing.png"
        )
        plt.close()

    print(f"Visualizations saved to {output_dir}")
