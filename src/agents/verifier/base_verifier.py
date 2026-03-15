"""
验证器基类模块

为Placement、Scheduling、Routing验证器提供统一接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ViolationType(Enum):
    """违规类型枚举"""
    # Placement相关
    MODULE_OVERLAP = "module_overlap"          # 模块重叠
    MODULE_OUT_OF_BOUNDS = "module_out_of_bounds"  # 模块越界
    MODULE_INVALID_POSITION = "module_invalid_position"  # 无效位置

    # Scheduling相关
    DEPENDENCY_VIOLATION = "dependency_violation"  # 依赖违反
    RESOURCE_CONFLICT = "resource_conflict"      # 资源冲突
    TIMING_VIOLATION = "timing_violation"        # 时序违反

    # Routing相关
    DROPLET_COLLISION = "droplet_collision"      # 液滴碰撞
    FLUID_CONSTRAINT = "fluid_constraint"        # 流体约束违反
    INVALID_PATH = "invalid_path"                # 无效路径


@dataclass
class Violation:
    """
    违规记录

    用于描述验证中发现的具体问题
    """
    violation_type: ViolationType
    message: str                    # 人类可读的错误描述
    severity: str                   # "error", "warning"
    entities: List[str] = field(default_factory=list)  # 涉及的模块/操作/液滴ID
    details: Dict[str, Any] = field(default_factory=dict)  # 详细信息
    suggested_fix: Optional[str] = None  # 建议的修复方式

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": self.violation_type.value,
            "message": self.message,
            "severity": self.severity,
            "entities": self.entities,
            "details": self.details,
            "suggested_fix": self.suggested_fix
        }

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.violation_type.value}: {self.message}"


@dataclass
class VerificationResult:
    """
    验证结果

    包含是否通过、违规列表、统计信息等
    """
    is_valid: bool
    violations: List[Violation] = field(default_factory=list)
    stage: str = ""  # "placement", "scheduling", "routing"

    # 统计信息
    stats: Dict[str, Any] = field(default_factory=dict)

    def get_errors(self) -> List[Violation]:
        """获取所有错误级别的违规"""
        return [v for v in self.violations if v.severity == "error"]

    def get_warnings(self) -> List[Violation]:
        """获取所有警告级别的违规"""
        return [v for v in self.violations if v.severity == "warning"]

    def has_error(self, error_type: ViolationType) -> bool:
        """检查是否有特定类型的错误"""
        return any(v.violation_type == error_type for v in self.get_errors())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于序列化"""
        return {
            "is_valid": self.is_valid,
            "stage": self.stage,
            "violations": [v.to_dict() for v in self.violations],
            "stats": self.stats,
            "summary": {
                "total_violations": len(self.violations),
                "errors": len(self.get_errors()),
                "warnings": len(self.get_warnings())
            }
        }

    def to_llm_report(self) -> str:
        """
        生成适合LLM理解的报告

        将验证结果转换为自然语言描述，便于LLM理解并修复
        """
        if self.is_valid:
            return f"[PASS] {self.stage}验证通过，未发现违规。"

        lines = [f"[FAIL] {self.stage}验证失败，发现 {len(self.violations)} 个问题：\n"]

        for i, v in enumerate(self.violations, 1):
            lines.append(f"{i}. [{v.severity.upper()}] {v.message}")
            if v.entities:
                lines.append(f"   涉及: {', '.join(v.entities)}")
            if v.suggested_fix:
                lines.append(f"   建议修复: {v.suggested_fix}")
            lines.append("")

        return "\n".join(lines)


class BaseVerifier(ABC):
    """
    验证器基类

    所有具体验证器（Placement、Scheduling、Routing）都应继承此类
    """

    def __init__(self, name: str):
        self.name = name
        self.enabled_warnings: List[ViolationType] = []  # 启用的警告类型

    @abstractmethod
    def verify(self, problem: 'Problem', solution: Dict[str, Any]) -> VerificationResult:
        """
        执行验证

        Args:
            problem: 问题定义
            solution: 解决方案（布局/调度/路由）

        Returns:
            VerificationResult: 验证结果
        """
        pass

    def enable_warning(self, warning_type: ViolationType):
        """启用特定类型的警告"""
        if warning_type not in self.enabled_warnings:
            self.enabled_warnings.append(warning_type)

    def _create_result(self, violations: List[Violation], stats: Optional[Dict] = None) -> VerificationResult:
        """创建验证结果"""
        errors = [v for v in violations if v.severity == "error"]
        return VerificationResult(
            is_valid=len(errors) == 0,
            violations=violations,
            stage=self.name,
            stats=stats or {}
        )
