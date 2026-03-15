"""
Routing验证器

验证路由方案是否满足以下约束：
1. 无碰撞约束：同一时间同一位置的液滴不能冲突
2. 流体约束：液滴之间必须保持最小间距
3. 路径连续性：液滴移动必须是连续的
4. 终点约束：液滴必须到达目标位置

TODO: 完整实现（Week 2-3）
"""

from typing import Dict, Any, List, Tuple, Set, Optional
from collections import defaultdict

from .base_verifier import BaseVerifier, Violation, ViolationType, VerificationResult


class DropletPath:
    """液滴路径表示"""

    def __init__(self, droplet_id: str, path: List[Tuple[int, int, int]]):
        """
        Args:
            droplet_id: 液滴ID
            path: [(t, x, y), ...] 时空路径
        """
        self.droplet_id = droplet_id
        self.path = sorted(path, key=lambda p: p[0])  # 按时间排序

    def get_position_at(self, time: int) -> Optional[Tuple[int, int]]:
        """获取指定时间的坐标"""
        for t, x, y in self.path:
            if t == time:
                return (x, y)
            if t > time:
                break
        return None

    def get_time_range(self) -> Tuple[int, int]:
        """获取路径的时间范围"""
        if not self.path:
            return (0, 0)
        return (self.path[0][0], self.path[-1][0])


class RoutingVerifier(BaseVerifier):
    """
    路由验证器

    验证路由方案的正确性
    TODO: 完整实现（Week 2-3）
    """

    def __init__(self, min_spacing: int = 1):
        """
        Args:
            min_spacing: 液滴之间的最小间距（电极数）
        """
        super().__init__("routing")
        self.min_spacing = min_spacing

    def verify(self, problem: 'DMFBProblem', solution: Dict[str, Any]) -> VerificationResult:
        """
        验证路由方案

        Args:
            problem: DMFB问题定义
            solution: 路由方案，格式：
                {
                    "routes": [
                        {
                            "droplet_id": "d1",
                            "path": [(0, 1, 1), (1, 2, 1), (2, 3, 1)]  # (t, x, y)
                        },
                        ...
                    ]
                }

        Returns:
            VerificationResult: 验证结果
        """
        violations: List[Violation] = []
        stats = {
            "total_droplets": 0,
            "droplets_checked": 0,
            "collision_checks": 0,
            "fluid_constraint_checks": 0
        }

        # 提取路由信息
        routes = solution.get("routes", [])
        if not routes:
            # 空路由可能是合法的（如果没有液滴需要移动）
            return self._create_result(violations, stats)

        stats["total_droplets"] = len(routes)

        # 解析路径
        droplet_paths: Dict[str, DropletPath] = {}
        for route in routes:
            try:
                droplet_id = route["droplet_id"]
                path = route["path"]
                # 验证路径格式
                validated_path = []
                for point in path:
                    if len(point) >= 3:
                        validated_path.append((int(point[0]), int(point[1]), int(point[2])))

                droplet_paths[droplet_id] = DropletPath(droplet_id, validated_path)
            except (KeyError, ValueError) as e:
                violations.append(Violation(
                    violation_type=ViolationType.INVALID_PATH,
                    message=f"路由路径格式无效: {e}",
                    severity="error",
                    entities=[str(route)]
                ))

        stats["droplets_checked"] = len(droplet_paths)

        # TODO: 实现完整的验证逻辑
        # 1. 检查液滴碰撞（时空冲突）
        collision_violations = self._check_collisions(droplet_paths)
        violations.extend(collision_violations)

        # 2. 检查流体约束（液滴间距）
        fluid_violations = self._check_fluid_constraints(droplet_paths)
        violations.extend(fluid_violations)

        # 3. 检查路径连续性
        continuity_violations = self._check_path_continuity(droplet_paths)
        violations.extend(continuity_violations)

        stats["collision_checks"] = len(droplet_paths) * (len(droplet_paths) - 1) // 2

        return self._create_result(violations, stats)

    def _check_collisions(self, droplet_paths: Dict[str, DropletPath]) -> List[Violation]:
        """
        检查液滴碰撞（时空冲突）

        TODO: 完整实现
        """
        violations = []

        # 构建时空占用图
        # time -> (x, y) -> list of droplet_ids
        spacetime_occupancy: Dict[int, Dict[Tuple[int, int], List[str]]] = defaultdict(lambda: defaultdict(list))

        for droplet_id, path in droplet_paths.items():
            for t, x, y in path.path:
                spacetime_occupancy[t][(x, y)].append(droplet_id)

        # 检查同一时空点是否有多个液滴
        for t, positions in spacetime_occupancy.items():
            for (x, y), droplets in positions.items():
                if len(droplets) > 1:
                    violations.append(Violation(
                        violation_type=ViolationType.DROPLET_COLLISION,
                        message=f"在时间 t={t}, 位置 ({x}, {y}) 发生液滴碰撞: {', '.join(droplets)}",
                        severity="error",
                        entities=droplets,
                        details={
                            "time": t,
                            "position": (x, y),
                            "droplets": droplets
                        },
                        suggested_fix="调整液滴路径，避免同时到达同一位置"
                    ))

        return violations

    def _check_fluid_constraints(self, droplet_paths: Dict[str, DropletPath]) -> List[Violation]:
        """
        检查流体约束（液滴间距）

        TODO: 完整实现（考虑对角线相邻）
        """
        violations = []

        # 简化实现：检查同一时间液滴之间的曼哈顿距离
        # 完整的实现应该考虑流体动力学约束

        return violations

    def _check_path_continuity(self, droplet_paths: Dict[str, DropletPath]) -> List[Violation]:
        """
        检查路径连续性

        TODO: 完整实现
        """
        violations = []

        for droplet_id, path in droplet_paths.items():
            for i in range(1, len(path.path)):
                prev_t, prev_x, prev_y = path.path[i - 1]
                curr_t, curr_x, curr_y = path.path[i]

                # 时间必须连续
                if curr_t != prev_t + 1:
                    violations.append(Violation(
                        violation_type=ViolationType.INVALID_PATH,
                        message=f"液滴 {droplet_id} 的路径在时间上不连续: t={prev_t} 到 t={curr_t}",
                        severity="error",
                        entities=[droplet_id],
                        suggested_fix="确保路径的时间戳连续"
                    ))

                # 移动距离检查（相邻电极或原地等待）
                dx = abs(curr_x - prev_x)
                dy = abs(curr_y - prev_y)
                if dx + dy > 1:
                    violations.append(Violation(
                        violation_type=ViolationType.INVALID_PATH,
                        message=f"液滴 {droplet_id} 在 t={prev_t} 到 t={curr_t} 的移动距离过大: ({dx}, {dy})",
                        severity="error",
                        entities=[droplet_id],
                        details={
                            "from": (prev_t, prev_x, prev_y),
                            "to": (curr_t, curr_x, curr_y)
                        },
                        suggested_fix="液滴每次只能移动到相邻电极或保持不动"
                    ))

        return violations


# 便捷函数
def verify_routing(problem: 'DMFBProblem', routes: List[Dict[str, Any]],
                   min_spacing: int = 1) -> VerificationResult:
    """
    便捷函数：快速验证路由方案

    Args:
        problem: DMFB问题
        routes: 路由列表
        min_spacing: 液滴最小间距

    Returns:
        VerificationResult: 验证结果
    """
    verifier = RoutingVerifier(min_spacing=min_spacing)
    solution = {"routes": routes}
    return verifier.verify(problem, solution)
