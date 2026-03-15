"""
Schedule验证器

验证调度方案是否满足以下约束：
1. 依赖约束：操作必须在所有前驱完成后才能开始
2. 资源约束：同一模块同一时间只能执行一个操作
3. 时序约束：操作持续时间必须符合模块要求
"""

from typing import Dict, Any, List, Tuple, Set
from collections import defaultdict

from .base_verifier import BaseVerifier, Violation, ViolationType, VerificationResult


class ScheduleVerifier(BaseVerifier):
    """
    调度验证器

    验证调度方案的正确性
    """

    def __init__(self):
        super().__init__("scheduling")

    def verify(self, problem: 'DMFBProblem', solution: Dict[str, Any]) -> VerificationResult:
        """
        验证调度方案

        Args:
            problem: DMFB问题定义
            solution: 调度方案，格式：
                {
                    "schedule": [
                        {"operation_id": 0, "start_time": 0, "end_time": 3, "module_id": "mixer_1"},
                        ...
                    ]
                }

        Returns:
            VerificationResult: 验证结果
        """
        violations: List[Violation] = []
        stats = {
            "total_operations": 0,
            "operations_checked": 0,
            "dependency_checks": 0,
            "resource_checks": 0
        }

        # 提取调度信息
        schedule = solution.get("schedule", [])
        if not schedule:
            violations.append(Violation(
                violation_type=ViolationType.DEPENDENCY_VIOLATION,
                message="调度方案为空，没有安排任何操作",
                severity="error",
                entities=[],
                suggested_fix="请为每个操作安排开始时间和模块"
            ))
            return self._create_result(violations, stats)

        stats["total_operations"] = len(schedule)

        # 构建操作映射
        op_schedule = {}  # op_id -> schedule_entry
        for entry in schedule:
            try:
                op_id = entry["operation_id"]
                op_schedule[op_id] = {
                    "start": int(entry["start_time"]),
                    "end": int(entry["end_time"]),
                    "module_id": entry.get("module_id", "unknown"),
                    "entry": entry
                }
            except (KeyError, ValueError) as e:
                violations.append(Violation(
                    violation_type=ViolationType.TIMING_VIOLATION,
                    message=f"调度条目格式无效: {e}",
                    severity="error",
                    entities=[str(entry)]
                ))

        stats["operations_checked"] = len(op_schedule)

        # 1. 检查依赖约束
        dependency_violations = self._check_dependencies(problem, op_schedule)
        violations.extend(dependency_violations)
        stats["dependency_checks"] = len(problem.operations)

        # 2. 检查资源约束
        resource_violations = self._check_resource_conflicts(op_schedule)
        violations.extend(resource_violations)
        stats["resource_checks"] = len(op_schedule)

        # 3. 检查时序约束
        timing_violations = self._check_timing(problem, op_schedule)
        violations.extend(timing_violations)

        return self._create_result(violations, stats)

    def _check_dependencies(self, problem: 'DMFBProblem', op_schedule: Dict[int, Dict]) -> List[Violation]:
        """检查依赖约束：前驱操作必须在当前操作开始前完成"""
        violations = []

        # 构建操作ID到对象的映射
        op_map = {op.id: op for op in problem.operations}

        for op_id, sched in op_schedule.items():
            if op_id not in op_map:
                violations.append(Violation(
                    violation_type=ViolationType.DEPENDENCY_VIOLATION,
                    message=f"操作 {op_id} 不在问题定义中",
                    severity="error",
                    entities=[str(op_id)],
                    suggested_fix=f"请检查操作ID是否正确"
                ))
                continue

            op = op_map[op_id]
            current_start = sched["start"]

            # 检查所有前驱
            for pred_id in op.dependencies:
                if pred_id not in op_schedule:
                    violations.append(Violation(
                        violation_type=ViolationType.DEPENDENCY_VIOLATION,
                        message=f"前驱操作 {pred_id} 没有被调度",
                        severity="error",
                        entities=[str(op_id), str(pred_id)],
                        suggested_fix=f"请先调度前驱操作 {pred_id}"
                    ))
                    continue

                pred_sched = op_schedule[pred_id]
                pred_end = pred_sched["end"]

                # 关键检查：前驱必须在当前操作开始前完成
                if pred_end > current_start:
                    violations.append(Violation(
                        violation_type=ViolationType.DEPENDENCY_VIOLATION,
                        message=f"操作 {op_id} (开始于t={current_start}) 在前驱 {pred_id} (结束于t={pred_end}) 完成前就开始了",
                        severity="error",
                        entities=[str(op_id), str(pred_id)],
                        details={
                            "operation_id": op_id,
                            "operation_start": current_start,
                            "predecessor_id": pred_id,
                            "predecessor_end": pred_end,
                            "gap": current_start - pred_end
                        },
                        suggested_fix=f"将操作 {op_id} 的开始时间推迟到 t={pred_end} 或更晚"
                    ))

        return violations

    def _check_resource_conflicts(self, op_schedule: Dict[int, Dict]) -> List[Violation]:
        """检查资源冲突：同一模块同一时间只能执行一个操作"""
        violations = []

        # 按模块分组
        module_usage: Dict[str, List[Tuple[int, int, int]]] = defaultdict(list)
        # module_id -> [(start, end, op_id), ...]

        for op_id, sched in op_schedule.items():
            module_id = sched["module_id"]
            start = sched["start"]
            end = sched["end"]
            module_usage[module_id].append((start, end, op_id))

        # 检查每个模块的使用冲突
        for module_id, usage_list in module_usage.items():
            # 按开始时间排序
            usage_list.sort(key=lambda x: x[0])

            n = len(usage_list)
            for i in range(n):
                for j in range(i + 1, n):
                    start1, end1, op1 = usage_list[i]
                    start2, end2, op2 = usage_list[j]

                    # 检查时间区间是否重叠
                    # 重叠条件：不是 (end1 <= start2 或 end2 <= start1)
                    if not (end1 <= start2 or end2 <= start1):
                        # 计算重叠时间段
                        overlap_start = max(start1, start2)
                        overlap_end = min(end1, end2)

                        violations.append(Violation(
                            violation_type=ViolationType.RESOURCE_CONFLICT,
                            message=f"模块 '{module_id}' 在时间 [{overlap_start}, {overlap_end}] 被操作 {op1} 和 {op2} 同时使用",
                            severity="error",
                            entities=[module_id, str(op1), str(op2)],
                            details={
                                "module_id": module_id,
                                "operation1": {"id": op1, "start": start1, "end": end1},
                                "operation2": {"id": op2, "start": start2, "end": end2},
                                "overlap": {"start": overlap_start, "end": overlap_end}
                            },
                            suggested_fix=f"将操作 {op2} 推迟到 t={end1} 或更晚，或为操作 {op2} 分配不同的模块"
                        ))

        return violations

    def _check_timing(self, problem: 'DMFBProblem', op_schedule: Dict[int, Dict]) -> List[Violation]:
        """检查时序约束：持续时间是否合理"""
        violations = []

        # 获取模块库
        modules = problem.modules if hasattr(problem, 'modules') else {}

        op_map = {op.id: op for op in problem.operations}

        for op_id, sched in op_schedule.items():
            start = sched["start"]
            end = sched["end"]
            duration = end - start

            # 检查负时间或零持续时间
            if duration <= 0:
                violations.append(Violation(
                    violation_type=ViolationType.TIMING_VIOLATION,
                    message=f"操作 {op_id} 的持续时间无效: {duration} (开始={start}, 结束={end})",
                    severity="error",
                    entities=[str(op_id)],
                    suggested_fix="确保结束时间严格大于开始时间"
                ))
                continue

            # 检查负开始时间
            if start < 0:
                violations.append(Violation(
                    violation_type=ViolationType.TIMING_VIOLATION,
                    message=f"操作 {op_id} 的开始时间为负: t={start}",
                    severity="error",
                    entities=[str(op_id)],
                    suggested_fix="确保所有操作的开始时间 >= 0"
                ))

            # 检查是否满足模块最小执行时间（如果有模块信息）
            if op_id in op_map:
                op = op_map[op_id]
                expected_duration = None

                if hasattr(op, 'duration') and op.duration is not None:
                    expected_duration = op.duration
                elif hasattr(op, 'module_type') and op.module_type in modules:
                    expected_duration = modules[op.module_type].exec_time

                if expected_duration is not None and duration < expected_duration:
                    violations.append(Violation(
                        violation_type=ViolationType.TIMING_VIOLATION,
                        message=f"操作 {op_id} 的执行时间 ({duration}) 短于模块要求的最小时间 ({expected_duration})",
                        severity="warning",  # 警告级别，可能可以容忍
                        entities=[str(op_id)],
                        details={
                            "operation_id": op_id,
                            "actual_duration": duration,
                            "required_duration": expected_duration
                        },
                        suggested_fix=f"将操作 {op_id} 的结束时间推迟到 t={start + expected_duration} 或更晚"
                    ))

        return violations


# 便捷函数
def verify_schedule(problem: 'DMFBProblem', schedule: List[Dict[str, Any]]) -> VerificationResult:
    """
    便捷函数：快速验证调度方案

    Args:
        problem: DMFB问题
        schedule: 调度列表

    Returns:
        VerificationResult: 验证结果
    """
    verifier = ScheduleVerifier()
    solution = {"schedule": schedule}
    return verifier.verify(problem, solution)
