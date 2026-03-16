# DMFB 合成数据集

本数据集用于训练 LLM Agent 进行数字微流控生物芯片 (DMFB) 的全流程合成。

## 数据集概览

- **生成时间**: 2026-03-16
- **问题规模**: 100 个合成问题 (50 小 + 50 大)
- **芯片尺寸**: 16x16, 20x20, 24x24

## 文件说明

| 文件 | 大小 | 内容 |
|------|------|------|
| `problems_small.json` | 274 KB | 20 操作的小规模问题 (50个) |
| `problems_large.json` | 595 KB | 50 操作的大规模问题 (50个) |
| `solutions_small.json` | 947 KB | 小规模问题的基线解决方案 |
| `solutions_large.json` | 2.2 MB | 大规模问题的基线解决方案 |
| `metadata.json` | 0.5 KB | 数据集统计信息 |

## 问题结构

每个问题包含以下信息：

```json
{
  "name": "small_000",
  "chip_width": 24,
  "chip_height": 24,
  "modules": {
    "mixer_2x2": {"name": "mixer_2x2", "type": "mixer", "width": 2, "height": 2, "exec_time": 3},
    "detector_1x2": {"name": "detector_1x2", "type": "detector", "width": 1, "height": 2, "exec_time": 2},
    ...
  },
  "operations": [
    {"id": 0, "op_type": "mix", "module_type": "mixer_2x2", "dependencies": []},
    {"id": 1, "op_type": "detect", "module_type": "detector_1x2", "dependencies": [0]},
    ...
  ]
}
```

## 解决方案结构

每个解决方案包含：

### Placement (布局)
- 算法: GA (遗传算法) + SA (模拟退火)
- 格式:
```json
{
  "operation_id": 0,
  "module_type": "mixer_2x2",
  "x": 0,
  "y": 0,
  "width": 2,
  "height": 2
}
```

### Scheduling (调度)
- 算法: List Scheduling (列表调度)
- 格式:
```json
{
  "operation_id": 0,
  "start_time": 0,
  "end_time": 3,
  "module_id": "mixer_2x2"
}
```

### Metrics (指标)
- **makespan**: 总完成时间
- **area_utilization**: 芯片面积利用率

## 基线算法

### 1. Placement (布局优化)
- **Fast Greedy + Local Search**: O(n²) 复杂度
- 优化目标: 最小化线长 (Manhattan distance)
- 约束: 无重叠, 芯片边界内

### 2. Scheduling (调度优化)
- **List Scheduling**: O(n log n) 复杂度
- 策略: 拓扑排序 + 启发式优先级
- 约束: 依赖关系, 模块可用性

### 3. 数据验证
- ✅ 所有 placement 无重叠
- ✅ 所有 schedule 满足依赖约束
- ✅ 100% 数据有效性

## 使用示例

```python
import json

# 加载问题
with open('problems_small.json') as f:
    problems = json.load(f)

# 加载对应解决方案
with open('solutions_small.json') as f:
    solutions = json.load(f)

# 使用第一个问题和解决方案
problem = problems[0]
solution = solutions[0]

print(f"问题: {problem['name']}")
print(f"操作数: {len(problem['operations'])}")
print(f"Makespan: {solution['metrics']['makespan']}")
```

## 下一步扩展

1. **添加 Routing**: 使用 A* 算法生成液滴路径
2. **更多算法变体**: CP (约束规划), MILP 求解
3. **真实问题**: 导入 CS220 的 17 个基准测试用例
4. **数据增强**: 对每个问题生成多组不同质量的解

## 生成脚本

```bash
# 快速生成 (推荐)
python scripts/generate_dataset_fast.py --size 50

# 自定义参数
python scripts/generate_dataset_fast.py --size 100 --small-ops 30 --large-ops 80
```

## 验证结果

```
小规模问题 (20 ops):
  - 有效布局: 50/50
  - 有效调度: 50/50

大规模问题 (50 ops):
  - 有效布局: 50/50
  - 有效调度: 50/50
```

---

**用途**: 用于训练 LLM Agent 的 few-shot prompting 和 RAG 检索增强生成
