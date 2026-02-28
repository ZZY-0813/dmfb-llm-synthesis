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

## 🚧 待实现功能

### Phase 1: Baseline完善与数据准备 (Week 1-4)

#### Week 1 遗留任务
- [ ] **Splash-2适配器** - 需要获取工具源码
- [ ] **CS220/MFSim编译验证** - 需要C++编译环境

#### Week 2 数据生成与验证
- [ ] 生成小规模测试集：20 ops × 100个，50 ops × 100个
- [ ] 生成中规模训练集：100 ops × 200个，200 ops × 100个
- [ ] 生成大规模挑战集：500 ops × 50个
- [ ] 运行baseline生成标签 (完整pipeline)
- [ ] 数据分析与统计 (makespan分布、CPL比值等)

#### Week 3 可视化与验证工具
- [ ] 改进placement可视化 (模块名称、依赖箭头)
- [ ] 实现schedule动画 (时间推进显示)
- [ ] 实现routing动画 (液滴移动轨迹)
- [ ] 添加3D可视化 (x, y, time)
- [ ] **关键缺失**: placement验证器 (检查重叠、越界)
- [ ] **关键缺失**: schedule验证器 (检查依赖、资源冲突)
- [ ] **关键缺失**: routing验证器 (检查碰撞、流体约束)

#### Week 4 Phase 1总结
- [ ] 添加完整docstring
- [ ] 运行代码格式化 (black)
- [ ] 添加类型注解
- [ ] 编写单元测试 (pytest, 覆盖率>80%)
- [ ] API文档编写

---

### Phase 2: Agent框架开发 (Week 5-12)

#### Week 5-6: Master Agent设计
- [ ] 设计Agent通信协议 (消息格式、状态机)
- [ ] 设计迭代优化流程图
- [ ] 确定LLM选型 (GPT-4 API vs 本地模型)
- [ ] 实现任务分解功能
- [ ] 实现子Agent调度器
- [ ] 实现结果汇总器
- [ ] 实现冲突检测器
- [ ] 实现反馈循环机制
- [ ] 实现重新规划触发器
- [ ] 实现收敛判断

**交付物**: `src/agents/master/master_agent.py`, `docs/agent_architecture.md`

#### Week 7-8: Placement Agent
- [ ] 设计placement任务的prompt模板
- [ ] 添加Chain-of-Thought提示
- [ ] 添加Few-shot示例
- [ ] 实现Python代码生成 (Code-as-Policy)
- [ ] 实现JSON直接输出
- [ ] 添加约束检查与后处理修复
- [ ] 实现从错误中学习
- [ ] 将baseline结果转换为指令格式
- [ ] 划分训练/验证集

**交付物**: `src/agents/placement/placement_agent.py`, `src/agents/placement/prompts.py`, `data/finetune/placement/train.jsonl`

#### Week 9-10: Scheduling Agent
- [ ] 设计scheduling任务的prompt模板
- [ ] 将DAG转换为文本描述
- [ ] 添加优先级策略说明
- [ ] 实现序列生成策略
- [ ] 或使用List Scheduling + LLM优化决策
- [ ] 添加约束满足保证
- [ ] 提取调度序列作为训练目标
- [ ] 准备instruction-response对

**交付物**: `src/agents/scheduling/scheduling_agent.py`, `src/agents/scheduling/prompts.py`, `data/finetune/scheduling/train.jsonl`

#### Week 11-12: Routing Agent + Verifier Agent
- [ ] 设计routing任务的prompt模板
- [ ] 描述时空约束
- [ ] 添加冲突消解策略
- [ ] 实现路径生成
- [ ] 或使用A* + LLM冲突消解
- [ ] 多液滴协同路由
- [ ] 集成验证工具
- [ ] 实现冲突报告生成
- [ ] 实现修复建议生成

**交付物**: `src/agents/routing/routing_agent.py`, `src/agents/verifier/verifier_agent.py`

---

### Phase 3: LLM集成与训练 (Week 13-24)

#### Week 13-16: 模型微调
- [ ] 申请GPU资源 (实验室服务器/云计算)
- [ ] 安装vLLM / TGI用于推理
- [ ] 安装PEFT用于微调
- [ ] 下载基础模型 (CodeLlama-7B/13B)
- [ ] **Placement Agent微调** - LoRA配置, 训练3-5 epoch
- [ ] **Scheduling Agent微调** - 类似训练流程
- [ ] **Routing Agent微调** - 路径生成模型
- [ ] **Master Agent微调 (可选)** - 迭代优化轨迹

**交付物**: `models/placement-agent/`, `models/scheduling-agent/`, `models/routing-agent/`

#### Week 17-20: RAG与增强
- [ ] 安装ChromaDB或FAISS
- [ ] 将baseline结果编码为向量
- [ ] 实现相似问题检索 (`src/agents/rag/retriever.py`)
- [ ] 基于问题相似度选择Few-shot示例
- [ ] 动态添加到prompt中
- [ ] 收集"错误->修复"的训练对
- [ ] 实现在线学习 (可选)
- [ ] 分析常见失败模式
- [ ] 设计针对性的修复策略
- [ ] 实现早期终止策略

#### Week 21-24: 对比实验
- [ ] 设计对比表格 (vs GA, vs SA, vs 分层方法)
- [ ] 设计消融实验 (各组件贡献)
- [ ] 选择测试集 (留出验证集)
- [ ] 在测试集上运行所有方法
- [ ] 记录makespan, runtime, success rate
- [ ] 消融实验: 无LLM、单vs多Agent、7B vs 13B、有无迭代优化、有无RAG
- [ ] 鲁棒性测试 (不同规模、约束严格程度)
- [ ] 统计分析 (t-test等)
- [ ] 生成对比图表
- [ ] 分析失败案例

**交付物**: `experiments/results/` 目录，包含所有结果和图表

---

### Phase 4: 论文撰写与答辩 (Week 25-40)

#### Week 25-28: 论文初稿
- [ ] 确定投稿目标 (DAC/ICCAD/TCAD)
- [ ] 制定论文大纲
- [ ] Introduction (背景、挑战、贡献)
- [ ] Related Work (DMFB综述、LLM for EDA、多Agent系统)
- [ ] Methodology (架构图、Agent设计、迭代优化、复杂度分析)

**交付物**: `paper/outline.md`, `paper/draft_v1.pdf`

#### Week 29-32: 实验与结果章节
- [ ] 实验设置 (硬件、软件、数据集、评估指标)
- [ ] 主要结果 (对比表格、扩展性图表、运行时间、成功率)
- [ ] 消融研究 (组件贡献、参数敏感性、Case study)
- [ ] 讨论 (结果解释、局限性、未来工作)

#### Week 33-36: 论文完善
- [ ] 整合所有章节
- [ ] 检查逻辑连贯性
- [ ] 补充引用文献
- [ ] 导师审阅与修改
- [ ] 图表优化 (tikz/illustrator)
- [ ] 格式调整 (页数限制、补充材料)

#### Week 37-40: 投稿与答辩
- [ ] 论文投稿
- [ ] 制作答辩PPT
- [ ] 准备演讲稿
- [ ] 模拟答辩
- [ ] 代码开源准备 (整理、README、notebook、脱敏)
- [ ] 最终答辩

---

## 📝 当前优先任务 (本周)

### 高优先级 (必须完成)
1. [ ] **运行 `python demo.py` 验证框架**
2. [ ] **生成第一批小规模数据集** (20 ops × 10个)
3. [ ] **询问导师关于MFSim/Splash-2获取**

### 中优先级 (尽量完成)
4. [ ] 运行baseline获取初始结果
5. [ ] 检查所有代码是否可以正常运行
6. [ ] 安装C++编译环境 (MinGW/Visual Studio)

### 低优先级 (有时间再做)
7. [ ] 完善可视化动画
8. [ ] 编写更多单元测试
9. [ ] 阅读相关论文

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

## 🎯 关键检查点状态

| 时间点 | 检查点 | 验收标准 | 状态 |
|-------|-------|---------|------|
| 第4周末 | Phase 1完成 | 有1000+训练样本，baseline可一键运行 | 🚧 进行中 |
| 第8周末 | Agent原型 | Master+3个子Agent可通信 | ⏳ 未开始 |
| 第12周末 | Agent框架完成 | 端到端pipeline可跑通 | ⏳ 未开始 |
| 第16周末 | 微调完成 | 有训练好的模型权重 | ⏳ 未开始 |
| 第24周末 | 实验完成 | 所有对比实验数据就绪 | ⏳ 未开始 |
| 第32周末 | 论文初稿 | 完整论文，导师认可 | ⏳ 未开始 |
| 第40周末 | 项目完成 | 论文投稿/答辩通过 | ⏳ 未开始 |

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
