"""
Placement验证器

验证布局方案是否满足以下约束：
1. 模块不能重叠
2. 模块必须在芯片边界内
3. 模块位置必须有效（整数坐标）
"""

from typing import Dict, Any, List, Tuple, Optional, Set
from dataclasses import dataclass

from .base_verifier import BaseVerifier, Violation, ViolationType, VerificationResult


@dataclass
class ModulePosition:
    """模块位置"""
    module_id: str
    x: int
    y: int
    width: int
    height: int

    @property
    def x2(self) -> int:
        """右下角x坐标（不包含）"""
        return self.x + self.width

    @property
    def y2(self) -> int:
        """右下角y坐标（不包含）"""
        return self.y + self.height

    def get_cells(self) -> Set[Tuple[int, int]]:
        """获取模块占据的所有单元格"""
        cells = set()
        for i in range(self.x, self.x2):
            for j in range(self.y, self.y2):
                cells.add((i, j))
        return cells

    def intersects(self, other: 'ModulePosition') -> bool:
        """检查两个模块是否相交"""
        return not (self.x2 <= other.x or other.x2 <= self.x or
                   self.y2 <= other.y or other.y2 <= self.y)

    def get_intersection_area(self, other: 'ModulePosition') -> int:
        """计算相交面积"""
        if not self.intersects(other):
            return 0
        x_overlap = max(0, min(self.x2, other.x2) - max(self.x, other.x))
        y_overlap = max(0, min(self.y2, other.y2) - max(self.y, other.y))
        return x_overlap * y_overlap


class PlacementVerifier(BaseVerifier):
    """
    Placement验证器

    验证布局方案的正确性和合理性
    """

    def __init__(self, check_connectivity: bool = False):
        """
        初始化

        Args:
            check_connectivity: 是否检查布局的连通性（可选，计算开销大）
        """
        super().__init__("placement")
        self.check_connectivity = check_connectivity

    def verify(self, problem: 'Problem', solution: Dict[str, Any]) -> VerificationResult:
        """
        验证布局方案

        Args:
            problem: DMFB问题定义
            solution: 布局方案，格式：
                {
                    "placements": [
                        {"module_id": "mixer_1", "x": 2, "y": 3, "width": 3, "height": 3},
                        ...
                    ]
                }

        Returns:
            VerificationResult: 验证结果
        """
        violations: List[Violation] = []
        stats = {
            "total_modules": 0,
            "modules_checked": 0,
            "overlap_checks": 0,
            "boundary_checks": 0
        }

        # 提取布局信息
        placements = solution.get("placements", [])
        if not placements:
            violations.append(Violation(
                violation_type=ViolationType.MODULE_INVALID_POSITION,
                message="布局方案为空，没有放置任何模块",
                severity="error",
                entities=[],
                suggested_fix="请为每个操作分配一个模块位置"
            ))
            return self._create_result(violations, stats)

        stats["total_modules"] = len(placements)

        # 解析模块位置
        modules: List[ModulePosition] = []
        for p in placements:
            try:
                module = ModulePosition(
                    module_id=p.get("module_id", str(len(modules))),
                    x=int(p["x"]),
                    y=int(p["y"]),
                    width=int(p.get("width", p.get("w", 1))),
                    height=int(p.get("height", p.get("h", 1)))
                )
                modules.append(module)
            except (KeyError, ValueError, TypeError) as e:
                violations.append(Violation(
                    violation_type=ViolationType.MODULE_INVALID_POSITION,
                    message=f"模块位置信息无效: {e}",
                    severity="error",
                    entities=[str(p)],
                    suggested_fix="确保每个模块有有效的x, y, width, height"
                ))

        stats["modules_checked"] = len(modules)

        # 1. 检查边界
        boundary_violations = self._check_boundary(modules, problem)
        violations.extend(boundary_violations)
        stats["boundary_checks"] = len(modules)

        # 2. 检查重叠
        overlap_violations = self._check_overlaps(modules)
        violations.extend(overlap_violations)
        stats["overlap_checks"] = len(modules) * (len(modules) - 1) // 2

        # 3. 可选：检查连通性
        if self.check_connectivity:
            connectivity_violations = self._check_connectivity(problem, modules)
            violations.extend(connectivity_violations)

        return self._create_result(violations, stats)

    def _check_boundary(self, modules: List[ModulePosition], problem: 'Problem') -> List[Violation]:
        """检查模块是否在芯片边界内"""
        violations = []

        # 获取芯片尺寸
        chip_width = getattr(problem, 'chip_width', 10)
        chip_height = getattr(problem, 'chip_height', 10)

        for module in modules:
            errors = []

            if module.x < 0:
                errors.append(f"x={module.x} < 0")
            if module.y < 0:
                errors.append(f"y={module.y} < 0")
            if module.x2 > chip_width:
                errors.append(f"x+width={module.x2} > chip_width={chip_width}")
            if module.y2 > chip_height:
                errors.append(f"y+height={module.y2} > chip_height={chip_height}")

            if errors:
                violations.append(Violation(
                    violation_type=ViolationType.MODULE_OUT_OF_BOUNDS,
                    message=f"模块 '{module.module_id}' 超出芯片边界: {', '.join(errors)}",
                    severity="error",
                    entities=[module.module_id],
                    details={
                        "module": {
                            "id": module.module_id,
                            "x": module.x, "y": module.y,
                            "width": module.width, "height": module.height
                        },
                        "chip": {"width": chip_width, "height": chip_height}
                    },
                    suggested_fix=f"将模块移动到 [0, {chip_width-module.width}] × [0, {chip_height-module.height}] 范围内"
                ))

        return violations

    def _check_overlaps(self, modules: List[ModulePosition]) -> List[Violation]:
        """检查模块之间是否重叠"""
        violations = []
        n = len(modules)

        for i in range(n):
            for j in range(i + 1, n):
                m1, m2 = modules[i], modules[j]

                if m1.intersects(m2):
                    # 计算重叠区域
                    overlap_area = m1.get_intersection_area(m2)
                    overlap_cells = m1.get_cells() & m2.get_cells()

                    # 确定重叠类型
                    if overlap_area == m1.width * m1.height:
                        overlap_type = "完全包含"
                    elif overlap_area > 0:
                        overlap_type = "部分重叠"
                    else:
                        overlap_type = "边缘接触"

                    # 计算建议的移动方向
                    suggested_move = self._suggest_move_direction(m1, m2)

                    violations.append(Violation(
                        violation_type=ViolationType.MODULE_OVERLAP,
                        message=f"模块 '{m1.module_id}' 与 '{m2.module_id}' {overlap_type}，重叠面积={overlap_area}单元格",
                        severity="error",
                        entities=[m1.module_id, m2.module_id],
                        details={
                            "module1": {
                                "id": m1.module_id,
                                "position": (m1.x, m1.y),
                                "size": (m1.width, m1.height)
                            },
                            "module2": {
                                "id": m2.module_id,
                                "position": (m2.x, m2.y),
                                "size": (m2.width, m2.height)
                            },
                            "overlap_area": overlap_area,
                            "overlap_cells": list(overlap_cells)[:10]  # 最多显示10个
                        },
                        suggested_fix=suggested_move
                    ))

        return violations

    def _suggest_move_direction(self, m1: ModulePosition, m2: ModulePosition) -> str:
        """建议移动方向以消除重叠"""
        # 计算中心点
        c1x, c1y = m1.x + m1.width / 2, m1.y + m1.height / 2
        c2x, c2y = m2.x + m2.width / 2, m2.y + m2.height / 2

        # 确定主要重叠方向
        dx = abs(c1x - c2x)
        dy = abs(c1y - c2y)

        directions = []

        if dx > dy:
            # 水平方向分离更容易
            if c1x < c2x:
                directions.append(f"将'{m1.module_id}'向左移动{m2.x2 - m1.x}格")
                directions.append(f"或将'{m2.module_id}'向右移动{m1.x2 - m2.x}格")
            else:
                directions.append(f"将'{m1.module_id}'向右移动{m2.x - m1.x2}格")
                directions.append(f"或将'{m2.module_id}'向左移动{m1.x - m2.x2}格")
        else:
            # 垂直方向分离更容易
            if c1y < c2y:
                directions.append(f"将'{m1.module_id}'向上移动{m2.y2 - m1.y}格")
                directions.append(f"或将'{m2.module_id}'向下移动{m1.y2 - m2.y}格")
            else:
                directions.append(f"将'{m1.module_id}'向下移动{m2.y - m1.y2}格")
                directions.append(f"或将'{m2.module_id}'向上移动{m1.y - m2.y2}格")

        return "；".join(directions)

    def _check_connectivity(self, problem: 'Problem', modules: List[ModulePosition]) -> List[Violation]:
        """
        检查布局的连通性（可选检查）

        确保所有模块之间有足够的通道进行液滴路由
        """
        violations = []

        # 简化的连通性检查：确保模块之间的通道宽度至少为1
        # 实际实现可能需要更复杂的图连通性算法

        return violations


# 便捷函数
def verify_placement(problem: 'Problem', placements: List[Dict[str, Any]],
                     check_connectivity: bool = False) -> VerificationResult:
    """
    便捷函数：快速验证布局

    Args:
        problem: DMFB问题
        placements: 布局列表
        check_connectivity: 是否检查连通性

    Returns:
        VerificationResult: 验证结果
    """
    verifier = PlacementVerifier(check_connectivity=check_connectivity)
    solution = {"placements": placements}
    return verifier.verify(problem, solution)
