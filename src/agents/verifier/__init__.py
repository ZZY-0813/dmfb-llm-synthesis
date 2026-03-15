"""
DMFB验证器模块

提供布局、调度、路由的验证功能
"""

from typing import Dict, Any

from .base_verifier import (
    BaseVerifier,
    Violation,
    ViolationType,
    VerificationResult
)

from .placement_verifier import (
    PlacementVerifier,
    ModulePosition,
    verify_placement
)

# 占位符：后续实现
# from .schedule_verifier import ScheduleVerifier, verify_schedule
# from .routing_verifier import RoutingVerifier, verify_routing

__all__ = [
    # 基类
    'BaseVerifier',
    'Violation',
    'ViolationType',
    'VerificationResult',

    # Placement验证器
    'PlacementVerifier',
    'ModulePosition',
    'verify_placement',

    # TODO: Scheduling验证器 (Week 1-2)
    # 'ScheduleVerifier',
    # 'verify_schedule',

    # TODO: Routing验证器 (Week 2)
    # 'RoutingVerifier',
    # 'verify_routing',
]


def get_verifier(stage: str) -> BaseVerifier:
    """
    获取指定阶段的验证器

    Args:
        stage: "placement", "scheduling", "routing"

    Returns:
        BaseVerifier: 对应阶段的验证器
    """
    stage = stage.lower()

    if stage == "placement":
        return PlacementVerifier()
    # elif stage == "scheduling":
    #     return ScheduleVerifier()
    # elif stage == "routing":
    #     return RoutingVerifier()
    else:
        raise ValueError(f"Unknown verification stage: {stage}. "
                        f"Available: placement")  # , scheduling, routing")


class UnifiedVerifier:
    """
    统一验证器

    顺序执行所有阶段的验证
    """

    def __init__(self):
        self.placement_verifier = PlacementVerifier()
        # self.schedule_verifier = ScheduleVerifier()  # TODO
        # self.routing_verifier = RoutingVerifier()    # TODO

    def verify_full(self, problem: 'Problem', solution: Dict[str, Any]) -> Dict[str, VerificationResult]:
        """
        执行全流程验证

        Args:
            problem: DMFB问题
            solution: 完整解决方案，包含placements, schedule, routes

        Returns:
            Dict[str, VerificationResult]: 各阶段的验证结果
        """
        results = {}

        # 1. 验证布局
        if "placements" in solution:
            results["placement"] = self.placement_verifier.verify(
                problem,
                {"placements": solution["placements"]}
            )

        # 2. 验证调度 (TODO)
        # if "schedule" in solution:
        #     results["scheduling"] = self.schedule_verifier.verify(...)

        # 3. 验证路由 (TODO)
        # if "routes" in solution:
        #     results["routing"] = self.routing_verifier.verify(...)

        return results

    def is_valid(self, results: Dict[str, VerificationResult]) -> bool:
        """检查所有阶段是否都通过"""
        return all(r.is_valid for r in results.values())
