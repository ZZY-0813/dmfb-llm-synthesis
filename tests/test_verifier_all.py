"""
所有验证器的综合测试
"""

import sys
sys.path.insert(0, 'src')

from agents.verifier import (
    PlacementVerifier, ScheduleVerifier, RoutingVerifier,
    UnifiedVerifier, verify_placement, verify_schedule, verify_routing,
    ViolationType
)


class MockProblem:
    """测试用的简单问题类"""
    def __init__(self, width=10, height=10):
        self.chip_width = width
        self.chip_height = height
        self.operations = []
        self.modules = {}


class MockOperation:
    """模拟操作"""
    def __init__(self, op_id, dependencies=None, duration=3):
        self.id = op_id
        self.dependencies = dependencies or []
        self.duration = duration


def test_placement_verifier():
    """测试Placement验证器"""
    print("\n=== Placement验证器测试 ===")

    problem = MockProblem(10, 10)
    placements = [
        {"module_id": "mixer_1", "x": 2, "y": 2, "width": 2, "height": 2},
        {"module_id": "heater_1", "x": 5, "y": 5, "width": 1, "height": 1}
    ]

    result = verify_placement(problem, placements)
    assert result.is_valid, "合法布局应该通过"
    print("[OK] 合法布局测试通过")

    # 测试重叠
    placements_overlap = [
        {"module_id": "m1", "x": 2, "y": 2, "width": 3, "height": 3},
        {"module_id": "m2", "x": 3, "y": 3, "width": 3, "height": 3}
    ]
    result = verify_placement(problem, placements_overlap)
    assert not result.is_valid, "重叠布局应该失败"
    assert result.has_error(ViolationType.MODULE_OVERLAP)
    print("[OK] 重叠检测测试通过")

    # 测试越界
    placements_oob = [
        {"module_id": "m1", "x": 8, "y": 2, "width": 3, "height": 3}
    ]
    result = verify_placement(problem, placements_oob)
    assert not result.is_valid, "越界布局应该失败"
    assert result.has_error(ViolationType.MODULE_OUT_OF_BOUNDS)
    print("[OK] 越界检测测试通过")


def test_schedule_verifier():
    """测试Schedule验证器"""
    print("\n=== Schedule验证器测试 ===")

    # 创建有依赖关系的问题
    problem = MockProblem()
    problem.operations = [
        MockOperation(0, dependencies=[], duration=3),
        MockOperation(1, dependencies=[0], duration=2),
        MockOperation(2, dependencies=[0], duration=2)
    ]

    # 合法调度
    schedule = [
        {"operation_id": 0, "start_time": 0, "end_time": 3, "module_id": "mixer_1"},
        {"operation_id": 1, "start_time": 3, "end_time": 5, "module_id": "heater_1"},
        {"operation_id": 2, "start_time": 3, "end_time": 5, "module_id": "heater_2"}
    ]

    result = verify_schedule(problem, schedule)
    assert result.is_valid, "合法调度应该通过"
    print("[OK] 合法调度测试通过")

    # 依赖违反
    schedule_bad_dep = [
        {"operation_id": 0, "start_time": 0, "end_time": 3, "module_id": "mixer_1"},
        {"operation_id": 1, "start_time": 1, "end_time": 3, "module_id": "heater_1"}  # 依赖0，但1<3
    ]

    result = verify_schedule(problem, schedule_bad_dep)
    assert not result.is_valid, "依赖违反应该失败"
    assert result.has_error(ViolationType.DEPENDENCY_VIOLATION)
    print("[OK] 依赖违反检测测试通过")

    # 资源冲突
    schedule_conflict = [
        {"operation_id": 0, "start_time": 0, "end_time": 3, "module_id": "mixer_1"},
        {"operation_id": 1, "start_time": 1, "end_time": 4, "module_id": "mixer_1"}  # 同时使用mixer_1
    ]

    result = verify_schedule(problem, schedule_conflict)
    assert not result.is_valid, "资源冲突应该失败"
    assert result.has_error(ViolationType.RESOURCE_CONFLICT)
    print("[OK] 资源冲突检测测试通过")

    # 负持续时间
    schedule_negative = [
        {"operation_id": 0, "start_time": 5, "end_time": 3, "module_id": "mixer_1"}
    ]

    result = verify_schedule(problem, schedule_negative)
    assert not result.is_valid, "负持续时间应该失败"
    print("[OK] 负持续时间检测测试通过")


def test_routing_verifier():
    """测试Routing验证器"""
    print("\n=== Routing验证器测试 ===")

    problem = MockProblem()

    # 合法路径
    routes = [
        {"droplet_id": "d1", "path": [(0, 1, 1), (1, 2, 1), (2, 3, 1)]},
        {"droplet_id": "d2", "path": [(0, 5, 5), (1, 5, 6), (2, 5, 7)]}
    ]

    result = verify_routing(problem, routes)
    assert result.is_valid, "合法路径应该通过"
    print("[OK] 合法路径测试通过")

    # 碰撞检测
    routes_collision = [
        {"droplet_id": "d1", "path": [(0, 1, 1), (1, 2, 1), (2, 3, 1)]},
        {"droplet_id": "d2", "path": [(0, 3, 3), (1, 2, 1), (2, 1, 1)]}  # t=1时都在(2,1)
    ]

    result = verify_routing(problem, routes_collision)
    assert not result.is_valid, "路径碰撞应该失败"
    assert result.has_error(ViolationType.DROPLET_COLLISION)
    print("[OK] 路径碰撞检测测试通过")

    # 不连续时间
    routes_discontinuous = [
        {"droplet_id": "d1", "path": [(0, 1, 1), (2, 2, 1)]}  # 缺少t=1
    ]

    result = verify_routing(problem, routes_discontinuous)
    assert not result.is_valid, "不连续时间应该失败"
    assert result.has_error(ViolationType.INVALID_PATH)
    print("[OK] 时间连续性检测测试通过")


def test_unified_verifier():
    """测试统一验证器"""
    print("\n=== 统一验证器测试 ===")

    problem = MockProblem()
    problem.operations = [
        MockOperation(0, dependencies=[]),
        MockOperation(1, dependencies=[0])
    ]

    solution = {
        "placements": [
            {"module_id": "mixer_1", "x": 2, "y": 2, "width": 2, "height": 2}
        ],
        "schedule": [
            {"operation_id": 0, "start_time": 0, "end_time": 3, "module_id": "mixer_1"},
            {"operation_id": 1, "start_time": 3, "end_time": 6, "module_id": "mixer_1"}
        ],
        "routes": [
            {"droplet_id": "d1", "path": [(0, 1, 1), (1, 2, 1), (2, 3, 1)]}
        ]
    }

    unified = UnifiedVerifier()
    results = unified.verify_full(problem, solution)

    print(f"验证结果: {list(results.keys())}")
    for stage, result in results.items():
        print(f"  {stage}: {'通过' if result.is_valid else '失败'}")

    assert unified.is_valid(results), "合法方案应该全部通过"
    print("[OK] 统一验证器测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("验证器综合测试")
    print("=" * 60)

    try:
        test_placement_verifier()
        test_schedule_verifier()
        test_routing_verifier()
        test_unified_verifier()

        print("\n" + "=" * 60)
        print("所有测试通过！")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n[FAIL] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
