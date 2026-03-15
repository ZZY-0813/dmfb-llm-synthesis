"""
Placement验证器测试

测试各种边界情况和重叠检测
"""

import sys
sys.path.insert(0, 'src')

# 创建一个简单的mock问题类，避免复杂的依赖
class MockProblem:
    """测试用的简单问题类"""
    def __init__(self, width=10, height=10):
        self.chip_width = width
        self.chip_height = height


from agents.verifier import PlacementVerifier, verify_placement, ViolationType


def create_test_problem():
    """创建测试问题"""
    return MockProblem(width=10, height=10)


def test_valid_placement():
    """测试合法布局"""
    print("\n=== 测试合法布局 ===")

    problem = create_test_problem()
    placements = [
        {"module_id": "mixer_1", "x": 2, "y": 2, "width": 2, "height": 2},
        {"module_id": "heater_1", "x": 5, "y": 5, "width": 1, "height": 1}
    ]

    result = verify_placement(problem, placements)

    print(f"验证通过: {result.is_valid}")
    print(f"违规数量: {len(result.violations)}")

    assert result.is_valid, "合法布局应该通过验证"
    print("OK: 测试通过")


def test_overlap():
    """测试模块重叠"""
    print("\n=== 测试模块重叠 ===")

    problem = create_test_problem()
    placements = [
        {"module_id": "mixer_1", "x": 2, "y": 2, "width": 3, "height": 3},
        {"module_id": "mixer_2", "x": 3, "y": 3, "width": 3, "height": 3}  # 重叠
    ]

    result = verify_placement(problem, placements)

    print(f"验证通过: {result.is_valid}")
    print(f"违规数量: {len(result.violations)}")

    for v in result.violations:
        print(f"  - {v}")

    assert not result.is_valid, "重叠布局应该验证失败"
    assert result.has_error(ViolationType.MODULE_OVERLAP), "应该检测到重叠错误"
    print("OK: 测试通过")


def test_out_of_bounds():
    """测试越界"""
    print("\n=== 测试越界 ===")

    problem = create_test_problem()
    placements = [
        {"module_id": "mixer_1", "x": 8, "y": 2, "width": 3, "height": 3}  # x+width=11 > 10
    ]

    result = verify_placement(problem, placements)

    print(f"验证通过: {result.is_valid}")
    print(f"违规数量: {len(result.violations)}")

    for v in result.violations:
        print(f"  - {v}")

    assert not result.is_valid, "越界布局应该验证失败"
    assert result.has_error(ViolationType.MODULE_OUT_OF_BOUNDS), "应该检测到越界错误"
    print("OK: 测试通过")


def test_negative_position():
    """测试负坐标"""
    print("\n=== 测试负坐标 ===")

    problem = create_test_problem()
    placements = [
        {"module_id": "mixer_1", "x": -1, "y": 2, "width": 2, "height": 2}
    ]

    result = verify_placement(problem, placements)

    print(f"验证通过: {result.is_valid}")

    assert not result.is_valid, "负坐标应该验证失败"
    print("OK: 测试通过")


def test_empty_placement():
    """测试空布局"""
    print("\n=== 测试空布局 ===")

    problem = create_test_problem()
    placements = []

    result = verify_placement(problem, placements)

    print(f"验证通过: {result.is_valid}")

    assert not result.is_valid, "空布局应该验证失败"
    print("OK: 测试通过")


def test_llm_report():
    """测试LLM报告生成"""
    print("\n=== 测试LLM报告 ===")

    problem = create_test_problem()
    placements = [
        {"module_id": "mixer_1", "x": 2, "y": 2, "width": 3, "height": 3},
        {"module_id": "mixer_2", "x": 3, "y": 3, "width": 3, "height": 3}  # 重叠
    ]

    result = verify_placement(problem, placements)
    report = result.to_llm_report()

    print("LLM报告:")
    print(report)

    assert "重叠" in report or "overlap" in report.lower(), "报告应该提到重叠"
    print("OK: 测试通过")


def test_multiple_violations():
    """测试多个违规"""
    print("\n=== 测试多个违规 ===")

    problem = create_test_problem()
    placements = [
        {"module_id": "mixer_1", "x": -2, "y": -2, "width": 3, "height": 3},  # 负坐标
        {"module_id": "mixer_2", "x": 0, "y": 0, "width": 3, "height": 3},   # 与mixer_1重叠且越界
        {"module_id": "heater_1", "x": 15, "y": 15, "width": 2, "height": 2}  # 严重越界
    ]

    result = verify_placement(problem, placements)

    print(f"验证通过: {result.is_valid}")
    print(f"违规数量: {len(result.violations)}")

    for v in result.violations:
        print(f"  - {v.violation_type.value}: {v.message[:50]}...")

    assert len(result.violations) >= 2, "应该检测到多个违规"
    print("OK: 测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("Placement验证器测试")
    print("=" * 50)

    try:
        test_valid_placement()
        test_overlap()
        test_out_of_bounds()
        test_negative_position()
        test_empty_placement()
        test_llm_report()
        test_multiple_violations()

        print("\n" + "=" * 50)
        print("所有测试通过")
        print("=" * 50)
        return True

    except AssertionError as e:
        print(f"\n测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
