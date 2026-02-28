# DMFB + LLM 项目进度追踪

> 自动生成的进度报告 | 最后更新: 2026-02-28

---

## 📊 总体进度概览

| 阶段 | 状态 | 进度 | 关键里程碑 |
|-----|------|------|-----------|
| **Phase 1** | 进行中 | ~35% | Baseline完善与数据准备 (Week 1-4) |
| **Phase 2** | 未开始 | 0% | Agent框架开发 (Week 5-12) |
| **Phase 3** | 未开始 | 0% | LLM集成与训练 (Week 13-24) |
| **Phase 4** | 未开始 | 0% | 论文撰写与答辩 (Week 25-40) |

---

## ✅ 已实现功能

### 1. 核心Baseline框架 (100% 完成)

| 组件 | 文件 | 代码行数 | 状态 |
|-----|------|---------|------|
| 数据结构 | `src/baseline/problem.py` | ~600 | ✅ 完整 |
| 布局算法 (GA) | `src/baseline/placement_ga.py` | ~350 | ✅ 完整 |
| 调度算法 (List) | `src/baseline/scheduling_list.py` | ~250 | ✅ 完整 |
| 路由算法 (A*) | `src/baseline/routing_astar.py` | ~400 | ✅ 完整 |
| 统一运行接口 | `src/baseline/baseline_runner.py` | ~200 | ✅ 完整 |
| 适配器基类 | `src/baseline/adapters/base_adapter.py` | ~140 | ✅ 完整 |
| Python Fallback | `src/baseline/adapters/python_fallback.py` | ~180 | ✅ 完整 |

**功能详情：**
- [x] DMFB问题定义与JSON序列化
- [x] 模块库管理 (mixer/heater/detector/storage)
- [x] 操作依赖图 (DAG) 与拓扑排序
- [x] 关键路径长度计算
- [x] 遗传算法布局 (锦标赛选择、均匀交叉、高斯变异)
- [x] 列表调度 (ASAP/ALAP/Mobility/Critical Path)
- [x] A*路由 (3D时空搜索、流体约束)
- [x] 统一BaselineRunner接口

---

### 2. 外部工具集成 (85% 完成)

| 工具 | 适配器文件 | 状态 | 备注 |
|-----|-----------|------|------|
| **CS220** | `cs220_adapter.py` (~500行) | ✅ 完成 | 17个测试用例已导入 |
| **MFSimStatic** | `mfsim_adapter.py` (~570行) | ✅ 完成 | 支持23+种算法 |
| **Splash-2** | `splash_adapter.py` | ⏳ 占位 | 待获取工具 |

**CS220集成详情：**
- [x] CS220Importer - CFG/DAG/Arch格式解析
- [x] CS220Adapter - 调用C++可执行文件
- [x] 17个基准测试用例导入 (PCR, ELISA系列等)
- [x] PCR验证通过 (makespan=35, CPL=35, 100%最优)

**MFSimStatic集成详情：**
- [x] MFSimImporter - Assay/Arch格式解析
- [x] MFSimAdapter - 完整适配器
- [x] 支持10种调度器 (LS, PS, GAS, GAPS, RGAS, FDLS, FPPCS, FPPCPS, RTELS, ILPS)
- [x] 支持4种布局器 (KLLP, GLEB, GPB, FPPCLEB)
- [x] 支持9种路由器 (RMR, BR, FPR, FPMR, CR, FPPCSR, FPPCPR, LR, CDMAR)
- [x] compare_with_mfsim对比工具
- [x] 4/4单元测试通过

---

### 3. 问题生成器 (100% 完成)

**文件**: `src/dataset/generator.py` (~350行)

- [x] 5种DAG模式: linear, parallel, fork_join, pcr, random
- [x] 模块库定义: mixer_3x3, mixer_4x4, heater_2x2, detector_1x1, storage_2x2
- [x] 单问题生成
- [x] 批量数据集生成
- [x] 自动芯片尺寸选择
- [x] 随机种子控制 (可重复)

---

### 4. 可视化工具 (90% 完成)

**文件**: `src/utils/visualization.py` (~300行)

- [x] 布局可视化 (网格、模块、依赖箭头)
- [x] 调度Gantt图
- [x] 路由路径可视化
- [x] 完整解决方案可视化
- [ ] 动画支持 (时间推进显示) ⏳
- [ ] 3D可视化 (x, y, time) ⏳

---

### 5. 命令行脚本 (100% 完成)

| 脚本 | 文件 | 功能 |
|-----|------|------|
| 数据集生成 | `scripts/generate_dataset.py` | 批量生成问题 + 运行baseline |
| Baseline运行 | `scripts/run_baseline.py` | 单问题/批量运行 + 对比 |
| CS220导入 | `scripts/import_cs220_assays.py` | 导入17个基准测试 |
| CS220基准 | `scripts/benchmark_cs220.py` | 运行CS220测试集 |
| MFSim测试 | `scripts/test_mfsim_adapter.py` | 验证MFSim适配器 |
| 快速演示 | `demo.py` | 功能演示 |

---

### 6. 配置与工具 (100% 完成)

- [x] `configs/default.yaml` - 默认配置
- [x] `src/utils/config.py` - 配置管理
- [x] `src/utils/logger.py` - 日志工具
- [x] `requirements.txt` - 依赖列表
- [x] `.gitignore` - Git忽略配置
- [x] GitHub仓库推送完成

---

## 🚧 待实现功能（已根据建议优化）

> 💡 **策略调整**: 采用"API优先+快速验证"策略，先使用GPT-4/Claude API验证想法，再决定是否微调

### Phase 1: Baseline完善与验证器核心 (Week 1-3) 【压缩】

#### Week 1: 验证器核心（高优先级）
- [ ] **实现Placement验证器** `src/agents/verifier/placement_verifier.py`
  - 检查模块重叠、越界
  - 返回详细的冲突报告（具体哪个模块、什么冲突）
- [ ] **实现Schedule验证器** `src/agents/verifier/schedule_verifier.py`
  - 检查依赖满足、资源冲突
  - 识别关键路径违规
- [ ] **实现Routing验证器** `src/agents/verifier/routing_verifier.py`
  - 检查液滴碰撞、流体约束
  - 时空冲突检测（高效实现，使用空间索引）
- [ ] **统一Verifier接口** `src/agents/verifier/__init__.py`
  - 集成三个验证器
  - 生成结构化错误报告（便于LLM理解）

#### Week 2: 数据生成与多baseline标签
- [ ] 生成小规模测试集：20 ops × 50个，50 ops × 50个
- [ ] **使用多种baseline生成多样性标签**:
  - GA布局 + List调度（当前）
  - **新增**: SA模拟退火布局 + List调度
  - **新增**: OR-Tools ILP调度（如果可行）
- [ ] 数据分析：对比不同baseline的makespan差异
- [ ] **混合真实数据**: CS220的17个用例已就绪

#### Week 3: 3D可视化优先
- [ ] **实现3D可视化** `src/utils/visualization_3d.py`（高优先级）
  - 使用matplotlib的mplot3d
  - 展示x, y, time三维空间中的液滴轨迹
  - 用于理解路由冲突
- [ ] 改进placement可视化（模块名称、依赖箭头）
- [ ] 动画支持（低优先级，可后期）

#### Week 4 Phase 1总结
- [ ] 添加完整docstring
- [ ] 运行代码格式化 (black)
- [ ] 添加类型注解
- [ ] 编写单元测试 (pytest, 覆盖率>80%)
- [ ] API文档编写

---

### Phase 2: Agent框架开发 (Week 4-8) 【简化压缩】

> 💡 **架构简化**: Master Agent负责任务分解和结果汇总，子Agent之间不直接通信
> 💡 **API优先**: 使用GPT-4/Claude API + few-shot提示，跳过微调阶段

#### Week 4: API基础架构
- [ ] **实现LLM客户端** `src/agents/llm_client.py`
  - 支持OpenAI GPT-4 API
  - 支持Claude API
  - 统一接口，可切换模型
- [ ] **实现Prompt模板系统** `src/agents/prompts/base.py`
  - 可复用的prompt构建器
  - 支持few-shot示例注入
  - 支持Chain-of-Thought

#### Week 5: Placement Agent（核心创新点）【聚焦】
- [ ] **设计Placement Prompt** `src/agents/placement/prompts.py`
  - 问题描述格式（DAG + 芯片尺寸 + 模块库）
  - Chain-of-Thought提示（"首先分析关键路径..."）
  - Few-shot示例（从baseline结果中选择优质示例）
- [ ] **实现Placement Agent** `src/agents/placement/agent.py`
  - 调用LLM生成布局方案
  - 使用验证器检查可行性
  - **单轮生成 + 后处理修复**: 用启发式算法（局部搜索）修复重叠
  - 如仍不可行，反馈错误给LLM重新生成（最多3次）
- [ ] **评估Placement效果**
  - 与GA对比makespan和线长
  - 记录成功率、LLM调用次数

#### Week 6: Scheduling Agent + 简化Routing
- [ ] **Scheduling Agent** `src/agents/scheduling/`
  - Prompt: DAG → 调度序列
  - 策略: 基于List Scheduling + LLM优化优先级决策
- [ ] **简化Routing**（可能不需要单独Agent）
  - 使用A*路由作为后处理
  - LLM仅用于冲突消解决策（如果A*失败）

#### Week 7: Master Agent集成
- [ ] **Master Agent** `src/agents/master/agent.py`
  - 顺序执行: Placement → Scheduling → Routing
  - 收集各阶段结果
  - 端到端验证
  - 错误反馈与重试（最多2轮完整迭代）

#### Week 8: 优化与评估
- [ ] **RAG增强（轻量级）** `src/agents/rag/`
  - 使用FAISS检索相似问题
  - 动态添加few-shot示例
- [ ] **评估完整pipeline**
  - 与分层baseline对比
  - 分析各阶段贡献

**交付物**:
- `src/agents/` 完整代码
- `docs/agent_architecture.md` 架构文档
- `experiments/agent_eval/` 评估结果

---

### Phase 3: Prompt优化与对比实验 (Week 9-16) 【简化合并】

> 💡 **无需微调**: 专注于提示工程和API优化，大幅缩短周期

#### Week 9-10: Prompt工程优化
- [ ] **Prompt迭代优化** `src/agents/prompts/optimization.py`
  - 测试不同prompt模板效果
  - A/B测试Chain-of-Thought vs 直接生成
  - 测试few-shot示例数量 (1-shot, 3-shot, 5-shot)
  - 记录每种配置的成功率
- [ ] **自动示例选择** `src/agents/rag/retriever.py`
  - 使用FAISS检索相似问题
  - 动态选择最优few-shot示例
- [ ] **错误分析**
  - 收集常见失败模式
  - 针对性改进prompt

#### Week 11-14: 对比实验
- [ ] **设计对比实验**:
  - vs GA布局 + List调度（传统baseline）
  - vs 模拟退火布局
  - vs **分层流水线**（先布局再调度再路由，无迭代）
  - vs **纯LLM**（无后处理修复）
  - vs **LLM + 后处理**（完整方案）
- [ ] **消融实验**:
  - 有无Chain-of-Thought
  - 有无few-shot示例
  - 有无RAG增强
  - 后处理修复的作用
  - GPT-4 vs Claude效果对比
- [ ] **鲁棒性测试**:
  - 不同问题规模 (20/50/100/200 ops)
  - 不同芯片尺寸 (10x10, 15x15, 20x20)
  - 不同DAG模式 (linear, parallel, fork_join, random)
- [ ] **统计分析**: t-test, 成功率, 平均LLM调用次数

#### Week 15-16: 成本分析与优化
- [ ] **API成本分析**
  - 记录每个问题的token消耗
  - 计算平均成本 per problem
  - 对比不同策略的cost-effectiveness
- [ ] **效率优化**
  - 并行调用LLM（如果独立）
  - 缓存机制（相似问题复用结果）

**交付物**: `experiments/results/` 目录，包含所有结果、图表、成本分析

---

### Phase 4: 论文撰写与答辩 (Week 17-24) 【提前开始】

> 💡 **项目周期缩短**: 从40周压缩到24周，聚焦核心创新点

#### Week 17-18: 论文大纲与初稿
- [ ] 确定投稿目标 (DAC/ICCAD/TCAD，优先考虑TCAD或ICCAD)
- [ ] 制定论文大纲
- [ ] 撰写Introduction (背景、挑战、贡献3点)
- [ ] 撰写Related Work (DMFB综述、LLM for EDA)

**交付物**: `paper/outline.md`, `paper/intro_related.tex`

#### Week 19-20: Methodology
- [ ] 系统架构图 (简化版)
- [ ] Placement Agent详细设计 (核心创新)
- [ ] 验证器与后处理修复机制
- [ ] 复杂度分析

**交付物**: `paper/methodology.tex`

#### Week 21-22: 实验与结果
- [ ] 实验设置 (API配置、数据集、评估指标)
- [ ] 主要结果 (vs GA, vs 分层流水线)
- [ ] 消融研究 (prompt策略、后处理、RAG)
- [ ] 成本分析 (API token消耗)
- [ ] Case study (具体成功案例)

**交付物**: `paper/experiments.tex`, 所有图表

#### Week 23-24: 完善与投稿准备
- [ ] 整合所有章节
- [ ] 导师审阅与修改
- [ ] 图表优化
- [ ] 格式调整
- [ ] 代码开源准备 (README, notebook)
- [ ] 准备投稿材料

---

## 📝 当前优先任务 (本周 - 按新计划)

### 高优先级 (必须完成)
1. [ ] **运行 `python demo.py` 验证框架基础功能**
2. [ ] **实现Placement验证器** `src/agents/verifier/placement_verifier.py`
   - 检查模块重叠、越界
   - 返回结构化错误报告
3. [ ] **申请OpenAI/Anthropic API Key** (用于后续Agent开发)

### 中优先级 (尽量完成)
4. [ ] **实现Schedule验证器** `src/agents/verifier/schedule_verifier.py`
5. [ ] 生成第一批小规模数据集 (20 ops × 20个)
6. [ ] 运行baseline获取多样性标签 (GA + SA)

### 低优先级 (有时间再做)
7. [ ] 实现Routing验证器框架
8. [ ] 调研Claude API pricing和rate limits
9. [ ] 阅读LLM for EDA相关论文

**本周目标**: 验证器核心完成，API准备就绪，可开始Phase 2开发

---

## 📈 代码统计

| 类别 | 文件数 | 代码行数 | 状态 |
|-----|-------|---------|------|
| 核心数据结构 | 1 | ~600 | ✅ |
| 算法实现 | 3 | ~1,000 | ✅ |
| 适配器框架 | 5 | ~1,500 | ✅ |
| 问题生成 | 1 | ~350 | ✅ |
| 可视化 | 1 | ~300 | ✅ |
| 工具函数 | 2 | ~100 | ✅ |
| 命令行脚本 | 5 | ~500 | ✅ |
| 测试 | 1 | ~150 | ⚠️ 需扩充 |
| **总计** | **19+** | **~4,500** | |

---

## 🎯 关键检查点状态（优化后）

| 时间点 | 检查点 | 验收标准 | 状态 |
|-------|-------|---------|------|
| 第3周末 | Phase 1完成 | 验证器核心完成，100+样本，3D可视化 | 🚧 进行中 |
| 第8周末 | Agent框架完成 | Placement Agent可运行，API调用正常 | ⏳ 未开始 |
| 第16周末 | 实验完成 | 所有对比实验数据就绪，成本分析完成 | ⏳ 未开始 |
| 第24周末 | 论文初稿 | 完整论文，导师认可 | ⏳ 未开始 |
| **总周期** | **24周** | **从40周压缩到24周（6个月）** | 🎯 |

**优化亮点**:
- ✅ 跳过微调，使用API（节省8周）
- ✅ 聚焦Placement单点（减少复杂度）
- ✅ 单轮生成+后处理（减少迭代次数）
- ✅ 3D可视化优先（提高调试效率）

---

## 📋 优化决策说明

基于改进建议分析，以下是本次调整的核心理念：

### ✅ 采纳的优化

| 建议 | 决策 | 理由 |
|-----|------|------|
| **API优先** | 使用GPT-4/Claude API | 跳过耗时数月的微调，快速验证核心想法 |
| **Agent架构简化** | Master + 3个子Agent，不直接通信 | 降低状态管理复杂度，通过Master传递信息 |
| **单轮生成+后处理** | LLM生成方案 + 启发式修复 | 减少LLM调用次数，传统算法保证可行性 |
| **聚焦Placement** | 核心创新点 | 时间有限，单点突破比全流程更易出成果 |
| **验证器优先** | 作为核心模块 | 不仅检查，还生成详细报告供LLM修正 |
| **3D可视化** | 优先实现 | 对理解路由冲突至关重要 |
| **多baseline标签** | GA + SA + ILP | 提供更多样性的few-shot示例 |
| **对比分层流水线** | 必须包含 | 更能体现LLM端到端优化的优势 |

### ❌ 舍弃的内容

| 原计划 | 舍弃理由 |
|-------|---------|
| 微调7B/13B模型 | 耗时(数周)、资源要求高，API方式更快验证 |
| 完整的3个Agent独立开发 | 过于复杂，聚焦Placement单点 |
| 40周完整周期 | 压缩到24周，聚焦核心创新 |
| Splash-2适配器 | 优先级低，CS220和MFSim已足够 |
| Routing Agent单独实现 | 简化为A* + LLM冲突消解决策 |

### 🎯 新项目路线

**核心理念**: "快速验证 + 单点突破"

1. **Phase 1 (3周)**: 打好地基（验证器 + 多样数据）
2. **Phase 2 (5周)**: 核心创新（Placement Agent + API + 后处理）
3. **Phase 3 (8周)**: 充分对比（vs 传统方法 + 消融实验）
4. **Phase 4 (8周)**: 论文撰写（聚焦Placement创新点）

**预期优势**:
- 周期从40周缩短到24周（6个月）
- 无需GPU资源（省去申请和调试时间）
- 核心创新点清晰（LLM驱动的Placement优化）
- 失败风险低（API方式可快速调整）

**潜在风险与应对**:
- API成本高 → 使用缓存 + 限制测试集大小
- API效果不佳 → 快速转向微调（保留退路）
- 单点突破深度不够 → 充分的后处理修复机制保证质量

---

## 🔧 技术债务

1. **测试覆盖率不足** - 当前仅有基础测试，需要>80%覆盖率
2. **文档不完整** - 部分函数缺少详细docstring
3. **类型注解缺失** - 需要添加完整的类型提示
4. **错误处理** - 部分边界情况未处理
5. **性能优化** - 大规模问题(500+ ops)可能需要优化

---

**生成时间**: 2026-02-28
**生成工具**: Claude Code
**项目仓库**: https://github.com/ZZY-0813/dmfb-llm-synthesis
